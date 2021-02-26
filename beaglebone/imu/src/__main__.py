import Adafruit_BBIO.UART as UART
import serial
import struct

baud = 115200

#https://learn.adafruit.com/setting-up-io-python-library-on-beaglebone-black/uart
#UART1 RX:P9_26 TX:P9_24 CTS:P9_20 RTS:P9_19
#UART2 RX:P9_22 TX:P9_21
UART.setup("UART2")


#Binary packets Pg. 31
#https://www.pololu.com/file/0J1556/UM7%20Datasheet_v1-8_30.07.2018.pdf

#All SPI operations begin when the master writes two control bytes to the bus. The first byte
#indicates whether the operation is a register read (0x00) or a write (0x01). The second byte is
#the address of the register being accessed. 
#first byte read or write, second is address


#pg 15 for talking about packets    This is spi though, Not UART?
#ser.write(0x00)

#pip install

#Wants Gyroscopic accelerometer and magnetometer data
#Data Registers
XGyro = 0x61  # Processed x-axis rate gyro data
YGyro = 0x62  # Processed y-axis rate gyro data
ZGyro = 0x63  # Processed z-axis rate gyro data 
XAccel = 0x65  # Processed x-axis accel data
YAccel = 0x66  # Processed y-axis accel data
ZAccel = 0x67  # Processed z-axis accel data 
XMag = 0x69  # Processed x-axis magnetometer data
YMag = 0x6A  # Processed y-axis magnetometer data
ZMag = 0x6B  # Processed z-axis magnetometer data 

#https://stackoverflow.com/questions/57982782/type-codes-in-python-for-array this is int
type = "<b"

ser = serial.Serial(port="/dev/ttyS4", baudrate=baud)
ser.close()
ser.open()

cmd_buffer = [0,0,0,0,0,0,0,0,0,0,0]

#Sets desired transmission rates for CHR NMEA-style packets (31 bits) Pg. 55
#CREG_COM_RATES7 = 0x07
#packetRates = 0xf0000


def checkfirmware():
    cmd_buffer[0] = ord('s')
    cmd_buffer[1] = ord('n')
    cmd_buffer[2] = ord('p')
    cmd_buffer[3] = 0x40 #1000000 or just 0?
    cmd_buffer[4] = 0xAD

    checksum = ord('s') + ord('n') + ord('p') + 0xAD
    
    cmd_buffer[5] = 0
    cmd_buffer[6] = 0
    cmd_buffer[7] = 0
    cmd_buffer[8] = 0

    cmd_buffer[9] = checksum >> 8
    cmd_buffer[10] = checksum & 0xFF

    #ser.write(bytes([ord('s')]))
    #ser.write(bytes([ord('n')]))
    #ser.write(bytes([ord('p')]))
    #ser.write(0x00)
    #ser.write(0xAA)
    #ser.write(0x01)
    #ser.write(0xFB)

    ser.write(cmd_buffer)


def resetEKF():
    cmd_buffer[0] = ord('s')
    cmd_buffer[1] = ord('n')
    cmd_buffer[2] = ord('p')
    cmd_buffer[3] = 0x40
    cmd_buffer[4] = 0xB0

    checksum = ord('s') + ord('n') + ord('p') + 0xB0

    cmd_buffer[5] = 0
    cmd_buffer[6] = 0
    cmd_buffer[7] = 0
    cmd_buffer[8] = 0

    cmd_buffer[9] = checksum >> 8
    cmd_buffer[10] = checksum & 0xB0

    ser.write(cmd_buffer)
    


def setRate():
    cmd_buffer[0] = ord('s')
    cmd_buffer[1] = ord('n')
    cmd_buffer[2] = ord('p')
    cmd_buffer[3] = 0x40
    cmd_buffer[4] = 0x04 #Processed Data

    checksum = ord('s') + ord('n') + ord('p') + 0x04

    #Data that is non zero
    cmd_buffer[5] = 0
    cmd_buffer[6] = 0
    cmd_buffer[7] = 0
    cmd_buffer[8] = 0x08

    cmd_buffer[9] = checksum >> 8
    cmd_buffer[10] = checksum & 0xB0

    ser.write(cmd_buffer)

    


def read_data(register):
    # with serial.Serial(port="/dev/ttyS4", baudrate=baud) as ser:
        #Page 31 Data Sheet
    #PT = 00000000
    #packet = struct.pack('s','n','p', PT, register)
    
    #value = ser.read(register)

    cmd_buffer[0] = ord('s')
    cmd_buffer[1] = ord('n')
    cmd_buffer[2] = ord('p')
    cmd_buffer[3] = 0x00
    cmd_buffer[4] = register

    checksum = ord('s') + ord('n') + ord('p') + register
    
    #these four are for the four bytes that make up the data section
    cmd_buffer[5] = 0
    cmd_buffer[6] = 0
    cmd_buffer[7] = 0
    cmd_buffer[8] = 0

    cmd_buffer[9] = checksum >> 8
    cmd_buffer[10] = checksum & 0xFF

    #Attempting to get a reading from the UM7
    print(cmd_buffer)
    value = ser.write(cmd_buffer)     
    print(value)
    print(cmd_buffer)

    #print("pt1")
    #value = ser.read(register)
    #print("pt2")
    #print(value)

    return value


checkfirmware()
resetEKF()
setRate()
while ser.isOpen():
    
    GyroX = read_data(XGyro)
    GyroY = read_data(YGyro)
    GyroZ = read_data(ZGyro)
    AccelX = read_data(XAccel)
    AccelY = read_data(YAccel)
    AccelZ = read_data(ZAccel)
    MagX = read_data(XMag)
    MagY = read_data(YMag)
    MagZ = read_data(ZMag)
    

    

    #print("Gyro:      X: " + GyroX + "Y: " + GyroY + "Z: " + GyroZ + "\n         Accel:     X: " + AccelX + "Y: " + AccelY + "Z: " + AccelZ + "\n         Mag:       X: " + MagX + "Y: " + MagY + "Z: " + MagZ)


#I think Rushils code wasnt working since he reserved one space in his buffer for the packet type and data bytes payloads, which are more than one byte
#packet type is one byte though right?
