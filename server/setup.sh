#!/bin/bash
# OnyxPoker Server Setup Script

echo "Setting up OnyxPoker AI Analysis Server..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p /tmp/onyxpoker_screenshots
mkdir -p logs

# Copy environment configuration
if [ ! -f .env ]; then
    cp ../.env.example .env
    echo "Please edit .env file with your configuration"
fi

# Make app executable
chmod +x app.py

echo "Server setup complete!"
echo "To start the server:"
echo "  source venv/bin/activate"
echo "  python app.py"
