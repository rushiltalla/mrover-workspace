import Adafruit_BBIO.UART as UART
import serial
import asyncio
import math
import time
from rover_common.aiohelper import run_coroutines
from rover_common import aiolcm
from rover_msgs import IMUData


class IMU_Manager():

    def __init__(self):
        UART.setup("UART4")

        # Mapping NMEA messages to their handlers
        self.NMEA_TAGS_MAPPER = {
            "PCHRS": self.pchrs_handler,
            "PCHRA": self.pchra_handler
        }
        self.sleep = .01

    def __enter__(self):

        self.ser = serial.Serial(
            port='/dev/ttyS4',
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=0
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        '''
        Closes serial connection to UM-7
        '''
        self.ser.close()

    def pchrs_handler(self, msg, imu_struct):
        arr = msg.split(",")

        # packet type can be either 0: gyro, 1: accel, 2: magnetometer
        # mag data is unit-nrom (unitless)
        try:
            arr = msg.split(",")
            print(arr)
            packetType = arr[1]
            if (packetType == '0'):
                imu_struct.gyro_x_dps = float(arr[3])
                imu_struct.gyro_y_dps = float(arr[4])
                imu_struct.gyro_z_dps = float(arr[5])
            elif (packetType == '1'):
                imu_struct.accel_x_g = float(arr[3])
                imu_struct.accel_y_g = float(arr[4])
                imu_struct.accel_z_g = float(arr[5])
            elif (packetType == '2'):
                imu_struct.mag_x_uT = float(arr[3])
                imu_struct.mag_y_uT = float(arr[4])
                imu_struct.mag_z_uT = float(arr[5])
                bearing = -(math.atan2(float(arr[4]), float(arr[3])) * (180.0 / math.pi))
                if(bearing < 0):
                    bearing += 360
                imu_struct.bearing_deg = bearing
            else:
                # this shouldnt happen
                print("Passed")
                pass
        # fill with zeroes if something goes wrong.
        except:
            print("somthing went wrong")
            imu_struct.gyro_x_dps = 0
            imu_struct.gyro_y_dps = 0
            imu_struct.gyro_z_dps = 0
            imu_struct.accel_x_g = 0
            imu_struct.accel_y_g = 0
            imu_struct.accel_z_g = 0
            imu_struct.mag_x_uT = 0
            imu_struct.mag_y_uT = 0
            imu_struct.mag_z_uT = 0

    def pchra_handler(self, msg, imu_struct):
        pi = 3.14159265359
        try:
            arr = msg.split(",")
            # raw values are in degrees, need to convert to radians
            imu_struct.roll_rad = float(arr[2]) * pi / 180
            imu_struct.pitch_rad = float(arr[3]) * pi / 180
            imu_struct.yaw_rad = float(arr[4]) * pi / 180
            # fill with zeroes if something goes wrong
        except:
            print("somthing went wrong the other one")
            imu_struct.roll_rad = 0
            imu_struct.pitch_rad = 0
            imu_struct.yaw_rad = 0

    async def recieve(self, lcm):
            '''
            Reads from the rover IMU over serial connection.
            Attempts to read and proccess all supported NMEA tags
            at least once before publishing a new LCM message.
            Sleeps after publishing to
            allow time for handling incoming LCM messages
            '''
            imu = IMUData()
            error_counter = 0
            # Mark TXT as always seen because they are not necessary
            while True:
                try:
                    msg = str(self.ser.readline())
                    error_counter = 0
                except Exception as e:
                    if error_counter < self.max_error_count:
                        error_counter += 1
                        print(e)
                        await asyncio.sleep(self.sleep)
                        continue
                    else:
                        raise e

                match_found = False
                for tag, func in self.NMEA_TAGS_MAPPER.items():
                    if tag in msg:
                        match_found = True
                        try:
                            if(tag == "PCHRS"):
                                print(msg)
                                func(msg, imu)
                                lcm.publish('/imu_data', imu.encode())
                            if(tag == "PCHRA"):
                                print(msg)
                                func(msg, imu)
                                lcm.publish('/imu_data', imu.encode())
                        except Exception as e:
                            print(e)
                            break

                    if not match_found:
                        if not msg:
                            print('Error decoding message stream: {}'.format(msg))

                await asyncio.sleep(self.sleep)

    # turns off registers that are outputting non-NMEA data
    def turnOffRegister(self, register):
        checksum = ord('s') + ord('n') + ord('p') + register + 0x80

        cmd_buffer = [ord('s'), ord('n'), ord('p'), 0x80, register,
                      0x00, 0x00, 0x00, 0x00, checksum >> 8, checksum & 0xff]

        self.ser.write(cmd_buffer)

    # turns on the attidude and sensor nmea sentences to 1Hz
    def enable_nmea(self, register):
        checksum = ord('s') + ord('n') + ord('p') + register + 0x80 + 0x11

        cmd_buffer = [ord('s'), ord('n'), ord('p'), 0x80, register,
                      0, 0x11, 0, 0, checksum >> 8, checksum & 0xff]

        self.ser.write(cmd_buffer)

    def get_calibrated(self, register):
        checksum = ord('s') + ord('n') + ord('p') + register
        cmd_buffer = [ord('s'), ord('n'), ord('p'), 0x00, register,
                      checksum >> 8, checksum & 0xff]

        # sends reques for data
        self.ser.write(cmd_buffer)
        time.sleep(.5)

        # um7 sends back same message as request for data but with payload
        # containing IEEE 754 32bit number (= to python float)
        received = self.ser.readline()
        print("reveived\n")
        print(received)
        if(received[0:8] == "b'snp\x80"):
            print(received[0:8])
            print(received)
            print("\n")
        # b'/0x74/0x72
        # data = float(received[5:9])
        # print("data")
        # print(data)


# end of class


def main():
    # Uses a context manager to ensure serial port released
    NMEA_RATE_REG = 0x07
    GYRO_PROC = [0x61, 0x62, 0x63]
    MAG_PROC = [0x69, 0x6A, 0x6B]
    ACCEL_PROC = [0x65, 0x66, 0x67]

    with IMU_Manager() as manager:
        # turns off registers that are outputting non-NMEA data
        l = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07]
        for reg in l:
            manager.turnOffRegister(reg)

        # hopefully spits out calibrated values from registers
        for r in GYRO_PROC:
            print("GYRO_PROC\n")
            manager.get_calibrated(r)
        for r in MAG_PROC:
            print("MAG_PROC\n")
            manager.get_calibrated(r)
        for r in ACCEL_PROC:
            print("ACCEL_PROC\n")
            manager.get_calibrated(r)

        manager.enable_nmea(NMEA_RATE_REG)

        lcm = aiolcm.AsyncLCM()

        run_coroutines(lcm.loop(), manager.recieve(lcm))


if __name__ == "__main__":
    main()
