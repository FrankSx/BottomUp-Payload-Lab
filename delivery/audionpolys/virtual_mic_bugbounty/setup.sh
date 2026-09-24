#!/bin/bash
# Virtual Mic Bug Bounty Platform - Setup Script

set -e

echo "🎤 Setting up Virtual Microphone Bug Bounty Platform..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p tests/payloads
mkdir -p reports
mkdir -p evidence

# Download ChromeDriver (adjust version as needed)
echo "📥 Downloading ChromeDriver..."
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1)
wget -q "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROME_VERSION.0.6778.87/linux64/chromedriver-linux64.zip" -O chromedriver.zip || echo "⚠️  Manual ChromeDriver download may be needed"
unzip -o chromedriver.zip 2>/dev/null || true
rm -f chromedriver.zip

# Set permissions
chmod +x src/core/virtual_mic_controller.py

echo "✅ Setup complete!"
echo "🚀 Run: python dashboard/app.py"
