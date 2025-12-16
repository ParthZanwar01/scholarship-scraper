#!/bin/bash
# quick_start.sh
# Sets up Tor-based social media scraping for Instagram and TikTok

echo "======================================"
echo "SCHOLARSHIP SCRAPER - TOR SETUP"
echo "======================================"

# Check if we're in the right directory
if [ ! -d "scholarship_scraper" ]; then
    echo "Error: Run this from the project root directory"
    exit 1
fi

cd scholarship_scraper

# Install requirements
echo "[1/5] Installing Python requirements..."
./venv/bin/pip install -q requests[socks] PySocks stem

# Check if Tor is installed
echo "[2/5] Checking Tor installation..."
if ! command -v tor &> /dev/null; then
    echo "Tor not found. Installing via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install tor
    else
        echo "Error: Homebrew not found. Install Tor manually:"
        echo "  brew install tor  # macOS"
        echo "  apt-get install tor  # Ubuntu"
        exit 1
    fi
else
    echo "✓ Tor is installed"
fi

# Setup directories
echo "[3/5] Creating directories..."
mkdir -p scraped_data sessions logs

# Generate accounts file
echo "[4/5] Setting up accounts..."
./venv/bin/python -c "
import json
import os

accounts = {
    'instagram': [
        {
            'username': os.getenv('INSTAGRAM_USERNAME', 'parthzanwar112@gmail.com'),
            'password': os.getenv('INSTAGRAM_PASSWORD', 'Parthtanish00!')
        }
    ],
    'tiktok': [
        {
            'username': os.getenv('TIKTOK_USERNAME', ''),
            'password': os.getenv('TIKTOK_PASSWORD', '')
        }
    ]
}

with open('accounts.json', 'w') as f:
    json.dump(accounts, f, indent=2)

print('✓ Accounts configured')
"

# Check if Tor is running
echo "[5/5] Starting Tor service..."
if pgrep -x "tor" > /dev/null; then
    echo "✓ Tor is already running"
else
    echo "Starting Tor..."
    tor &
    sleep 5
    if pgrep -x "tor" > /dev/null; then
        echo "✓ Tor started successfully"
    else
        echo "Warning: Tor may not have started. Check manually."
    fi
fi

echo ""
echo "======================================"
echo "SETUP COMPLETE!"
echo "======================================"
echo "Now run: ./venv/bin/python orchestrator.py"
echo ""
