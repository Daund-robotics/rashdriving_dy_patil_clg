#!/bin/bash

echo "🚗 Rash Driving Detection System - Setup Script"
echo "-----------------------------------------------"

# 1. Update System
echo "🔄 Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install System Dependencies (I2C, GPIO, Build Tools)
echo "🛠️ Installing system libraries..."
sudo apt-get install -y python3-dev python3-pip python3-venv i2c-tools python3-smbus libgpiod-dev

# 3. Create Virtual Environment (Recommended for Python 3.13+)
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
echo "🚀 To run the project:"
echo "   1. source venv/bin/activate"
echo "   2. python main.py"
echo "-----------------------------------------------"
