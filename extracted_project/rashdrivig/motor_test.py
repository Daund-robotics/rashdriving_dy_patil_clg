import RPi.GPIO as GPIO
import time

# L298N Pins (BCM numbering)
IN1 = 6
IN2 = 5
IN3 = 13
IN4 = 19

GPIO.setmode(GPIO.BCM)

GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)

print("🚗 Motors Moving Forward...")

# Forward direction
GPIO.output(IN1, 1)
GPIO.output(IN2, 0)
GPIO.output(IN3, 1)
GPIO.output(IN4, 0)

time.sleep(10)   # Run forward for 10 seconds

# Stop motors
GPIO.output(IN1, 0)
GPIO.output(IN2, 0)
GPIO.output(IN3, 0)
GPIO.output(IN4, 0)

GPIO.cleanup()
print("Motors Stopped")
