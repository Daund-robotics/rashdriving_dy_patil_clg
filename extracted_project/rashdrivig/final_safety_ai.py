import smbus
import time
import joblib
import numpy as np
import RPi.GPIO as GPIO

# ---------------- PIN DEFINITIONS ----------------

# Motor direction pins
IN1 = 6
IN2 = 5
IN3 = 13
IN4 = 19

# Motor enable pins (PWM)
ENA = 12
ENB = 18

# Sensors & controls
MQ2_PIN = 27        # Alcohol sensor digital
BUZZER_PIN = 20    # Buzzer
KEY_PIN = 16       # Ignition key / switch

# ---------------- GPIO SETUP ----------------

GPIO.setmode(GPIO.BCM)

# Motor pins
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(ENB, GPIO.OUT)

# Sensor & key pins
GPIO.setup(MQ2_PIN, GPIO.IN)
GPIO.setup(KEY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# PWM setup
pwmA = GPIO.PWM(ENA, 100)
pwmB = GPIO.PWM(ENB, 100)
pwmA.start(0)
pwmB.start(0)

# ---------------- MOTOR FUNCTIONS ----------------

def motor_forward(speed=80):
    GPIO.output(IN1, 1)
    GPIO.output(IN2, 0)
    GPIO.output(IN3, 1)
    GPIO.output(IN4, 0)
    pwmA.ChangeDutyCycle(speed)
    pwmB.ChangeDutyCycle(speed)

def motor_stop():
    pwmA.ChangeDutyCycle(0)
    pwmB.ChangeDutyCycle(0)
    GPIO.output(IN1, 0)
    GPIO.output(IN2, 0)
    GPIO.output(IN3, 0)
    GPIO.output(IN4, 0)

def slow_stop():
    print("⚙️ Reducing speed slowly...")
    for speed in [70, 60, 50, 40, 30, 20, 10, 0]:
        pwmA.ChangeDutyCycle(speed)
        pwmB.ChangeDutyCycle(speed)
        time.sleep(0.4)
    motor_stop()

# ---------------- MPU6050 + ML SETUP ----------------

model = joblib.load("rash_driving_model.pkl")

PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

bus = smbus.SMBus(1)
Device_Address = 0x68
bus.write_byte_data(Device_Address, PWR_MGMT_1, 0)

def read_raw_data(addr):
    high = bus.read_byte_data(Device_Address, addr)
    low = bus.read_byte_data(Device_Address, addr + 1)
    value = ((high << 8) | low)
    if value > 32768:
        value = value - 65536
    return value

print("🚗 FINAL AI SAFETY SYSTEM WITH IGNITION KEY STARTED")
print("Press Ctrl+C to stop\n")

rash_start_time = None
prev_key_state = 0   # To detect sudden OFF

try:
    while True:

        # --------- READ INPUTS ---------
        alcohol = GPIO.input(MQ2_PIN)     # 0 = alcohol detected
        key = GPIO.input(KEY_PIN)         # 1 = key ON
       
        # --------- KEY OFF SUDDENLY LOGIC ---------
        if prev_key_state == 1 and key == 0:
            print("🔑 Key turned OFF suddenly - slowing vehicle safely")
            slow_stop()

        prev_key_state = key

        # --------- IF KEY IS OFF → VEHICLE STOP ---------
        if key == 0:
            motor_stop()
            GPIO.output(BUZZER_PIN, 1)
            print("🔑 Key OFF - Vehicle Stopped")
            time.sleep(0.2)
            continue

        # --------- IF DRUNK AND TRYING TO START ---------
        if alcohol == 0 and key == 1:
            print("🍺 DRUNK DRIVER - VEHICLE NOT ALLOWED TO START")
            GPIO.output(BUZZER_PIN, 0)
            motor_stop()
            time.sleep(0.5)
            continue

        # --------- READ MPU6050 DATA ---------
        acc_x = read_raw_data(ACCEL_XOUT_H)
        acc_y = read_raw_data(ACCEL_XOUT_H + 2)
        acc_z = read_raw_data(ACCEL_XOUT_H + 4)

        gyro_x = read_raw_data(GYRO_XOUT_H)
        gyro_y = read_raw_data(GYRO_XOUT_H + 2)
        gyro_z = read_raw_data(GYRO_XOUT_H + 4)

        Ax = acc_x / 16384.0
        Ay = acc_y / 16384.0
        Az = acc_z / 16384.0

        Gx = gyro_x / 131.0
        Gy = gyro_y / 131.0
        Gz = gyro_z / 131.0

        sample = np.array([[Ax, Ay, Az, Gx, Gy, Gz]])
        prediction = model.predict(sample)

        # --------- RASH DRIVING LOGIC ---------
        if prediction[0] == 1:
            print("⚠️ RASH DRIVING DETECTED")
            GPIO.output(BUZZER_PIN, 0)

            if rash_start_time is None:
                rash_start_time = time.time()

            elif time.time() - rash_start_time > 3:
                print("⛔ Rash continues - slowing & stopping motors")
                slow_stop()
                rash_start_time = None

        else:
            rash_start_time = None

        # --------- NORMAL CONDITION ---------
        if prediction[0] == 0 and alcohol == 1 and key == 1:
            GPIO.output(BUZZER_PIN, 1)
            motor_forward(80)
            print("✅ Normal Driving")

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nSystem Stopped")
    motor_stop()
    GPIO.output(BUZZER_PIN, 1)
    pwmA.stop()
    pwmB.stop()
    GPIO.cleanup()
