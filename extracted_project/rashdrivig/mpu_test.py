import smbus
import time
import math

# MPU6050 Registers
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

bus = smbus.SMBus(1)
Device_Address = 0x68

# Wake up MPU6050
bus.write_byte_data(Device_Address, PWR_MGMT_1, 0)

def read_raw_data(addr):
    high = bus.read_byte_data(Device_Address, addr)
    low = bus.read_byte_data(Device_Address, addr+1)

    value = ((high << 8) | low)

    if value > 32768:
        value = value - 65536
    return value

while True:
    # Read Accelerometer raw values
    acc_x = read_raw_data(ACCEL_XOUT_H)
    acc_y = read_raw_data(ACCEL_XOUT_H + 2)
    acc_z = read_raw_data(ACCEL_XOUT_H + 4)

    # Read Gyroscope raw values
    gyro_x = read_raw_data(GYRO_XOUT_H)
    gyro_y = read_raw_data(GYRO_XOUT_H + 2)
    gyro_z = read_raw_data(GYRO_XOUT_H + 4)

    # Convert to proper units
    Ax = acc_x / 16384.0
    Ay = acc_y / 16384.0
    Az = acc_z / 16384.0

    Gx = gyro_x / 131.0
    Gy = gyro_y / 131.0
    Gz = gyro_z / 131.0

    print("Acc  X={:.2f} Y={:.2f} Z={:.2f}".format(Ax, Ay, Az))
    print("Gyro X={:.2f} Y={:.2f} Z={:.2f}".format(Gx, Gy, Gz))
    print("------------------------------------")

    time.sleep(0.5)

