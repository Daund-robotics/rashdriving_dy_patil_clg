#!/bin/bash

echo "🚗 Rash Driving Detection System - Setup Script"
echo "-----------------------------------------------"

# 1. Update System
echo "🔄 Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install System Dependencies & Thonny
echo "🛠️ Installing system libraries and Thonny..."
# Installing system dependencies for libraries and Thonny IDE
sudo apt-get install -y python3-dev python3-pip python3-venv i2c-tools python3-smbus libgpiod-dev thonny

# 3. Create Virtual Environment (Recommended for Python 3.13+)
# We will create a generic venv, but also install globally if needed for Thonny to see them easily without config
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

# 4. Activate Virtual Environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# 5. Install Python Dependencies
echo "📦 Installing Python libraries from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# Note: Thonny on RPi usually uses the system python. 
# To make libraries available to Thonny (without venv config), we can try installing with --break-system-packages
# ONLY if the user explicitly wants to run from Thonny easily.
# However, the safest way is inside venv. We will stick to venv and tell user how to point Thonny to it if needed, 
# or just install specific system packages that Thonny uses.

# Let's try to install key libraries via apt for system-wide access (Thonny default)
echo "🌍 Installing libraries globally for Thonny (System-wide)..."
sudo apt-get install -y python3-flask python3-socketio python3-numpy python3-pandas python3-sklearn python3-joblib python3-rpi.gpio python3-smbus

# 6. Enable I2C Interface (if not already enabled)
echo "⚙️ Checking I2C status..."
if sudo grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "✅ I2C is already enabled."
else
    echo "⚠️ Enabling I2C interface..."
    sudo echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
    echo "❗ REQUIRED: Please reboot your Raspberry Pi to enable I2C."
fi

# 7. Permissions
echo "🔐 Setting permissions..."
sudo usermod -aG i2c,gpio $USER

echo "-----------------------------------------------"
echo "✅ Setup Complete!"
echo "-----------------------------------------------"
echo "📝 HOW TO RUN:"
echo ""
echo "OPTION 1: Terminal (Recommended for Performance)"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "OPTION 2: Thonny IDE"
echo "   Open Thonny, then go to: Tools > Options > Interpreter"
echo "   Select 'Alternative Python 3 interpreter...'"
echo "   Browse to: $(pwd)/venv/bin/python3"
echo "   Then open main.py and click Run."
echo "-----------------------------------------------"
