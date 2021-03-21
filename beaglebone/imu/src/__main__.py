import Adafruit_BBIO.UART as UART
import serial
# import struct
# import time
import asyncio
# from os import getenv
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
            packetType = arr[1]
            if (packetType == 0):
                imu_struct.gyro_x_dps = float(arr[3])
                imu_struct.gyro_y_dps = float(arr[4])
                imu_struct.gyro_z_dps = float(arr[5])
            elif (packetType == 1):
                imu_struct.accel_x_g = float(arr[3])
                imu_struct.accel_y_g = float(arr[4])
                imu_struct.accel_z_g = float(arr[5])
            elif (packetType == 2):
                imu_struct.mag_x_uT = float(arr[3])
                imu_struct.mag_y_uT = float(arr[3])
                imu_struct.mag_z_uT = float(arr[3])
            else:
                # this shouldnt happen
                pass
        # fill with zeroes if something goes wrong.
        except:
            imu_struct.gyro_x_dps = 0
            imu_struct.gyro_y_dps = 0
            imu_struct.gyro_z_dps = 0
            imu_struct.accel_x_dps = 0
            imu_struct.accel_y_dps = 0
            imu_struct.accel_z_dps = 0
            imu_struct.mag_x_dps = 0
            imu_struct.mag_y_dps = 0
            imu_struct.mag_z_dps = 0

    def pchra_handler(self, msg, imu_struct):
        pi = 3.14159265359
        try:
            arr = msg.split(",")
            # raw values are in degrees, need to convert to radians
            imu_struct.roll_rad = float(arr[2]) * pi / 180
            imu_struct.pitch_rad = float(arr[3]) * pi / 180
            imu_struct.yaw_rad = float(arr[4]) * pi / 180
            # heading not bearing
            imu_struct.bearing_deg = float(arr[5])
        # fill with zeroes if something goes wrong
        except:
            imu_struct.roll_rad = 0
            imu_struct.pitch_rad = 0
            imu_struct.yaw_rad = 0
            imu_struct.bearing_deg = 0

    async def recieve(self, lcm):
            '''
            Reads from the rover IMU over serial connection.
            Attempts to read and proccess all supported NMEA tags
            at least once before publishing a new LCM message.
            Sleeps after publishing to
            allow time for handling incoming LCM messages
            '''
            imu_struct = IMUData()
            error_counter = 0
            # Mark TXT as always seen because they are not necessary
            seen_tags = {tag: False if not tag == 'TXT' else True
                         for tag in self.NMEA_TAGS_MAPPER.keys()}
            while True:
                # Wait for all tags to be seen
                while (not all(seen_tags.values())):
                    try:
                        msg = str(self.ser.readline())
                        print(msg)
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
                                func(msg, imu_struct)
                                seen_tags[tag] = True
                            except Exception as e:
                                print(e)
                            break

                    if not match_found:
                        print('Error decoding message stream: {}'.format(msg))

                lcm.publish('/imu_data', imu_struct.encode())
                seen_tags = {tag: False if not tag == 'TXT' else True
                             for tag in self.NMEA_TAGS_MAPPER.keys()}
                await asyncio.sleep(self.sleep)

    # turns off registers that are outputting non-NMEA data
    def turnOffRegister(self, register):
        checksum = ord('s') + ord('n') + ord('p') + register + 0x80

        cmd_buffer = {ord('s'), ord('n'), ord('p'), 0x80, register,
                      0x00, 0x00, 0x00, 0x00, checksum >> 8, checksum & 0xff}

        self.ser.write(bytes(cmd_buffer))

    # turns on the attidude and sensor nmea sentences to 1Hz
    def enable_nmea(self, register):
        checksum = ord('s') + ord('n') + ord('p') + register + 0x80 + 0x01

        cmd_buffer = {ord('s'), ord('n'), ord('p'), 0x80, register,
                      0, 0x11, 0, 0, checksum >> 8, checksum & 0xff}

        self.ser.write(bytes(cmd_buffer))

# end of class


def main():

    # Uses a context manager to ensure serial port released
    NMEA_RATE_REG = 0x07

    with IMU_Manager() as manager:
        # turns off registers that are outputting non-NMEA data
        l = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07}
        for reg in l:
            manager.turnOffRegister(reg)

        manager.enable_nmea(NMEA_RATE_REG)

        lcm = aiolcm.AsyncLCM()

        run_coroutines(lcm.loop(), manager.recieve(lcm))


if __name__ == "__main__":
    main()
