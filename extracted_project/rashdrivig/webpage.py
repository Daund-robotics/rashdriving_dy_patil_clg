# Vehicle Safety Dashboard + Accelerator Control (Flask)
# Run with:  python3 vehicle_dashboard.py
# Open browser: http://<raspberry_pi_ip>:5000

from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# ---------------- SYSTEM STATE ----------------
current_speed = 0          # 0 – 100 (PWM %)
vehicle_status = "STOPPED"
alert_message = "NONE"
buzzer_on = False

# Rash accelerator detection
last_speed = 0
last_change_time = time.time()

# ---------------- HARDWARE HOOKS (CONNECT WITH YOUR MAIN CODE) ----------------
# Replace these print statements with your real motor / buzzer functions

def motor_set_speed(speed):
    global vehicle_status
    if speed == 0:
        vehicle_status = "STOPPED"
    else:
        vehicle_status = "RUNNING"
    print(f"[MOTOR] Speed set to {speed}%")


def buzzer_on_func():
    global buzzer_on
    buzzer_on = True
    print("[BUZZER] ON")


def buzzer_off_func():
    global buzzer_on
    buzzer_on = False
    print("[BUZZER] OFF")

# ---------------- RASH ACCELERATOR LOGIC ----------------

def check_rash_accelerator(new_speed):
    global last_speed, last_change_time, alert_message

    now = time.time()
    speed_change = abs(new_speed - last_speed)
    time_diff = now - last_change_time

    # Rash condition: big speed change in very short time
    if speed_change > 30 and time_diff < 1.0:
        alert_message = "RASH ACCELERATION DETECTED!"
        buzzer_on_func()
        print("⚠️ RASH ACCELERATOR MOVEMENT")
    else:
        alert_message = "NONE"
        buzzer_off_func()

    last_speed = new_speed
    last_change_time = now

# ---------------- FLASK ROUTES ----------------

@app.route("/")
def index():
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Vehicle Safety Dashboard</title>
    <style>
        body {{ font-family: Arial; background: #111; color: white; text-align: center; }}
        .card {{ background: #222; padding: 20px; margin: 15px; border-radius: 10px; }}
        .alert {{ color: red; font-size: 22px; font-weight: bold; }}
        .normal {{ color: lightgreen; }}
        input[type=range] {{ width: 80%; }}
    </style>
</head>
<body>
    <h1>🚗 Intelligent Vehicle Safety Dashboard</h1>

    <div class="card">
        <h2>Vehicle Status</h2>
        <p id="status">Loading...</p>
        <p>Speed: <span id="speed">0</span> %</p>
    </div>

    <div class="card">
        <h2>Accelerator</h2>
        <input type="range" min="0" max="100" value="0" id="slider" oninput="setSpeed(this.value)">
    </div>

    <div class="card">
        <h2>Alert</h2>
        <p id="alert" class="normal">NONE</p>
    </div>

<script>
function setSpeed(val) {{
    fetch('/set_speed', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{speed: val}})
    }});
}}

function updateStatus() {{
    fetch('/status')
    .then(res => res.json())
    .then(data => {{
        document.getElementById('status').innerText = data.vehicle_status;
        document.getElementById('speed').innerText = data.speed;

        let alertBox = document.getElementById('alert');
        alertBox.innerText = data.alert;

        if (data.alert !== "NONE") {{
            alertBox.className = "alert";
        }} else {{
            alertBox.className = "normal";
        }}
    }});
}}

setInterval(updateStatus, 500);
</script>
</body>
</html>
"""


@app.route("/set_speed", methods=["POST"])
def set_speed():
    global current_speed

    data = request.get_json()
    new_speed = int(data.get("speed", 0))

    check_rash_accelerator(new_speed)

    current_speed = new_speed
    motor_set_speed(current_speed)

    return jsonify({"status": "ok"})


@app.route("/status")
def status():
    return jsonify({
        "speed": current_speed,
        "vehicle_status": vehicle_status,
        "alert": alert_message,
        "buzzer": buzzer_on
    })


# ---------------- MAIN ----------------

if __name__ == "__main__":
    print("🚗 Vehicle Dashboard Started")
    print("Open browser at: http://<raspberry_pi_ip>:5000")
    app.run(host="0.0.0.0", port=5000)
