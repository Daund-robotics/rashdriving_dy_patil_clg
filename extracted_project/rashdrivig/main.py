import smbus, time, joblib, numpy as np, socket
import RPi.GPIO as GPIO
import pandas as pd
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading

# ---------------- GET IP ADDRESS ----------------
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# ---------------- GPIO CLEAN SETUP ----------------
GPIO.setwarnings(False)
GPIO.cleanup()
GPIO.setmode(GPIO.BCM)

# ---------------- PIN DEFINITIONS ----------------
IN1, IN2, IN3, IN4 = 6, 5, 13, 19
ENA, ENB = 12, 18

MQ2_PIN = 27
BUZZER_PIN = 20
KEY_PIN = 16

# ---------------- GPIO SETUP ----------------
for pin in [IN1, IN2, IN3, IN4, ENA, ENB, BUZZER_PIN]:
    GPIO.setup(pin, GPIO.OUT)

GPIO.setup(MQ2_PIN, GPIO.IN)
GPIO.setup(KEY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# PWM
pwmA = GPIO.PWM(ENA, 100)
pwmB = GPIO.PWM(ENB, 100)
pwmA.start(0)
pwmB.start(0)

# ---------------- MOTOR VARIABLES ----------------
current_speed = 0
target_speed = 0   # accelerator target speed

# ---------------- MOTOR FUNCTIONS ----------------
def motor_forward(speed):
    global current_speed
    current_speed = speed
    GPIO.output(IN1, 1); GPIO.output(IN2, 0)
    GPIO.output(IN3, 1); GPIO.output(IN4, 0)
    pwmA.ChangeDutyCycle(speed)
    pwmB.ChangeDutyCycle(speed)

def motor_stop():
    global current_speed
    current_speed = 0
    pwmA.ChangeDutyCycle(0)
    pwmB.ChangeDutyCycle(0)
    GPIO.output(IN1, 0); GPIO.output(IN2, 0)
    GPIO.output(IN3, 0); GPIO.output(IN4, 0)

def slow_stop():
    global current_speed, target_speed
    print("⚙️ Reducing speed slowly...")
    for s in range(current_speed, -1, -10):
        pwmA.ChangeDutyCycle(s)
        pwmB.ChangeDutyCycle(s)
        time.sleep(0.3)
    target_speed = 0
    motor_stop()

# ---------------- ML + MPU6050 ----------------
model = joblib.load("rash_driving_model.pkl")

PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

bus = smbus.SMBus(1)
bus.write_byte_data(0x68, PWR_MGMT_1, 0)

def read_raw(addr):
    high = bus.read_byte_data(0x68, addr)
    low = bus.read_byte_data(0x68, addr+1)
    val = (high << 8) | low
    if val > 32768: val -= 65536
    return val

# ---------------- FLASK WEB SERVER ----------------
app = Flask(__name__)
socketio = SocketIO(app)

last_slider_time = time.time()
last_slider_value = 0

@app.route("/")
def index():
    return render_template("dashboard.html")

# -------- ACCELERATOR SLIDER HANDLER --------
@socketio.on("set_speed")
def set_speed(data):
    global last_slider_time, last_slider_value, target_speed

    speed = int(data["speed"])
    now = time.time()

    # Rash acceleration detection
    if abs(speed - last_slider_value) > 30 and (now - last_slider_time) < 1:
        emit("alert", {"msg": "⚠️ RASH ACCELERATION DETECTED"})
        GPIO.output(BUZZER_PIN, 1)
        slow_stop()
        return

    last_slider_time = now
    last_slider_value = speed

    # Only update target speed
    target_speed = speed
    emit("status", {"speed": speed})

# ---------------- TELEGRAM BOT SETUP ----------------
import requests

BOT_TOKEN = "8366269997:AAG517j7wB5Dsm9XG1BwlPAQOrCnXYLVrFI"
CHAT_ID = "5866641097"

def send_telegram_msg(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg}
        # Use a timeout to prevent blocking the safety loop for too long
        requests.post(url, data=data, timeout=3)
        print(f"📩 Telegram Sent: {msg}")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

# ---------------- BACKGROUND SAFETY LOOP ----------------
def safety_loop():
    global target_speed

    rash_start = None
    prev_key = 0
    
    # Flags to prevent spamming Telegram
    alcohol_alert_sent = False
    rash_alert_sent = False

    while True:
        alcohol = GPIO.input(MQ2_PIN)   # 0 = alcohol detected
        key = GPIO.input(KEY_PIN)       # 1 = key ON

        # -------- KEY START (0 -> 1) --------
        if prev_key == 0 and key == 1:
            send_telegram_msg("Car is started 🚗")

        # -------- KEY TURNED OFF SUDDENLY --------
        if prev_key == 1 and key == 0:
            socketio.emit("alert", {"msg": "🔑 KEY TURNED OFF – SAFE STOP"})
            slow_stop()

        prev_key = key

        # -------- KEY OFF --------
        if key == 0:
            motor_stop()
            target_speed = 0
            socketio.emit("status", {
                "key": "OFF",
                "speed": 0,
                "alcohol": "NO",
                "rash": "NO"
            })
            alcohol_alert_sent = False # Reset flag
            rash_alert_sent = False # Reset flag
            time.sleep(0.3)
            continue

        socketio.emit("status", {"key": "ON"})

        # -------- ALCOHOL CHECK --------
        if alcohol == 0:
            if not alcohol_alert_sent:
                send_telegram_msg("Driver is drunked 🍺")
                alcohol_alert_sent = True
            
            GPIO.output(BUZZER_PIN, 1)
            motor_stop()
            target_speed = 0
            socketio.emit("alert", {"msg": "🍺 ALCOHOL DETECTED – VEHICLE LOCKED"})
            socketio.emit("status", {"alcohol": "YES", "speed": 0})
            time.sleep(1)
            continue
        else:
            alcohol_alert_sent = False # Reset when alcohol is clear
            socketio.emit("status", {"alcohol": "NO"})

        # -------- READ MPU6050 --------
        Ax = read_raw(ACCEL_XOUT_H) / 16384.0
        Ay = read_raw(ACCEL_XOUT_H+2) / 16384.0
        Az = read_raw(ACCEL_XOUT_H+4) / 16384.0
        Gx = read_raw(GYRO_XOUT_H) / 131.0
        Gy = read_raw(GYRO_XOUT_H+2) / 131.0
        Gz = read_raw(GYRO_XOUT_H+4) / 131.0

        sample = pd.DataFrame([[Ax, Ay, Az, Gx, Gy, Gz]],
                               columns=["AccX", "AccY", "AccZ", "GyroX", "GyroY", "GyroZ"])

        pred = model.predict(sample)

        # -------- RASH DRIVING (AI) --------
        if pred[0] == 1:
            GPIO.output(BUZZER_PIN, 1)
            socketio.emit("alert", {"msg": "⚠️ RASH DRIVING DETECTED (AI)"})
            socketio.emit("status", {"rash": "YES"})

            if not rash_alert_sent:
                send_telegram_msg("Rash driving detected ⚠️")
                rash_alert_sent = True

            if rash_start is None:
                rash_start = time.time()
            elif time.time() - rash_start > 3:
                slow_stop()
                socketio.emit("alert", {"msg": "⛔ VEHICLE STOPPED DUE TO RASH DRIVING"})
                rash_start = None
        else:
            rash_start = None
            rash_alert_sent = False # Reset when driving is normal
            GPIO.output(BUZZER_PIN, 0)
            socketio.emit("status", {"rash": "NO"})

        # -------- CONTINUOUS MOTOR RUN --------
        if target_speed > 0 and alcohol == 1 and key == 1 and pred[0] == 0:
            motor_forward(target_speed)

        # Sync real speed always
        socketio.emit("status", {"speed": current_speed})

        time.sleep(0.4)

# Start safety thread
threading.Thread(target=safety_loop, daemon=True).start()

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    ip = get_ip()
    print("\n🚗 SMART VEHICLE DASHBOARD STARTED")
    print("🌐 Open Dashboard at: http://" + ip + ":5000\n")
    socketio.run(app, host="0.0.0.0", port=5000)
