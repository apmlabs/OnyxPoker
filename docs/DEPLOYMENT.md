# OnyxPoker Deployment Guide

## Quick Start

### 1. Linux Server Setup (AWS/Linux)
```bash
cd /home/ubuntu/mcpprojects/onyxpoker/server
./setup.sh
source venv/bin/activate
python app.py
```

### 2. Windows Client Setup
```cmd
cd client
setup.bat
venv\Scripts\activate.bat
python automation_client.py
```

## Detailed Deployment

### Linux Server (AI Analysis)

**Prerequisites:**
- Ubuntu 22.04 or later
- Python 3.8+
- Kiro CLI installed and accessible

**Installation:**
```bash
# Clone or copy project files
cd /path/to/onyxpoker/server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example .env
# Edit .env with your settings

# Create directories
mkdir -p /tmp/onyxpoker_screenshots
mkdir -p logs

# Start server
python app.py
```

**Production Deployment:**
```bash
# Using gunicorn for production
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or with systemd service
sudo cp onyxpoker.service /etc/systemd/system/
sudo systemctl enable onyxpoker
sudo systemctl start onyxpoker
```

### Windows Client (GUI Automation)

**Prerequisites:**
- Windows 10/11
- Python 3.8+
- Network access to Linux server

**Installation:**
```cmd
# Navigate to client directory
cd client

# Create virtual environment
python -m venv venv
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy ..\env.example .env
# Edit .env with server URL and API key

# Test connection
python automation_client.py
```

## Configuration

### Server Configuration (.env)
```bash
API_KEY=your_secure_api_key_here
FLASK_PORT=5000
FLASK_HOST=0.0.0.0
DEBUG=False
SECRET_KEY=your_secret_key_here

KIRO_CLI_PATH=/usr/local/bin/kiro-cli
TEMP_SCREENSHOT_DIR=/tmp/onyxpoker_screenshots
MAX_SCREENSHOT_SIZE=5242880

RATE_LIMIT_PER_MINUTE=60
AUTH_TOKEN_EXPIRY=3600
ALLOWED_ORIGINS=*

LOG_LEVEL=INFO
LOG_FILE=/var/log/onyxpoker.log
```

### Client Configuration (.env)
```bash
ONYXPOKER_SERVER_URL=http://your-server-ip:5000
ONYXPOKER_API_KEY=your_secure_api_key_here
SCREENSHOT_DELAY=1.0
MAX_RETRIES=3
```

## Security Setup

### Firewall Configuration
```bash
# Allow API port
sudo ufw allow 5000/tcp

# Restrict to specific IPs (recommended)
sudo ufw allow from YOUR_WINDOWS_IP to any port 5000
```

### SSL/HTTPS Setup
```bash
# Install nginx for SSL termination
sudo apt install nginx certbot python3-certbot-nginx

# Configure SSL certificate
sudo certbot --nginx -d your-domain.com

# Update nginx configuration for proxy
sudo nano /etc/nginx/sites-available/onyxpoker
```

### API Key Management
```bash
# Generate secure API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Store in environment variables
echo "API_KEY=your_generated_key" >> .env
```

## Monitoring & Logging

### Log Files
- Server logs: `/var/log/onyxpoker.log`
- Application logs: `logs/app.log`
- Error logs: `logs/error.log`

### Health Monitoring
```bash
# Check server health
curl -H "Authorization: Bearer your_api_key" http://localhost:5000/health

# Monitor logs
tail -f /var/log/onyxpoker.log
```

## Troubleshooting

### Common Issues

**Connection Refused:**
- Check firewall settings
- Verify server is running on correct port
- Confirm API key is correct

**Screenshot Analysis Fails:**
- Verify Kiro CLI is installed and accessible
- Check temp directory permissions
- Monitor server logs for errors

**PyAutoGUI Errors:**
- Ensure display is available (not headless)
- Check screen resolution and coordinates
- Verify PyAutoGUI permissions on Windows

### Debug Mode
```bash
# Enable debug logging
export DEBUG=True
export LOG_LEVEL=DEBUG

# Run with verbose output
python app.py --debug
```

## Performance Optimization

### Server Optimization
- Use gunicorn with multiple workers
- Implement Redis for caching
- Optimize image processing pipeline
- Monitor memory usage

### Client Optimization
- Adjust screenshot delay based on application response time
- Implement smart retry logic
- Cache common UI patterns
- Use image compression for faster uploads
