# OnyxPoker Deployment Guide

## Quick Start

### 1. Linux Server (Already Running)
```bash
Server: http://54.80.204.92:5000
Status: ✅ Running as systemd service
API Key: test_key_12345
```

### 2. Windows Client Setup
```bash
# 1. Get OpenAI API key
export OPENAI_API_KEY='sk-your-key-here'

# 2. Install dependencies
cd client
pip install -r requirements.txt

# 3. Configure .env
echo "ONYXPOKER_SERVER_URL=http://54.80.204.92:5000" > .env
echo "ONYXPOKER_API_KEY=test_key_12345" >> .env
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# 4. Test vision
python test_vision.py poker_table.png

# 5. Run GUI
python poker_gui.py
```

## Server Deployment (Already Complete)

### Current Setup
- **Location**: AWS EC2 (54.80.204.92)
- **Service**: systemd (onyxpoker.service)
- **Port**: 5000 (publicly accessible)
- **Logs**: /var/log/onyxpoker/
- **Auto-restart**: Enabled

### Server Management
```bash
# Check status
sudo systemctl status onyxpoker

# View logs
sudo journalctl -u onyxpoker -f

# Restart
sudo systemctl restart onyxpoker

# Stop
sudo systemctl stop onyxpoker
```

### Update Server Code
```bash
# SSH to server
ssh ubuntu@54.80.204.92

# Pull latest code
cd /home/ubuntu/mcpprojects/onyxpoker
git pull origin main

# Restart service
sudo systemctl restart onyxpoker
```

## Client Deployment

### Prerequisites
- Windows 10/11
- Python 3.8+
- OpenAI API key (for GPT-4o vision)
- Network access to server

### Installation
```bash
# Clone repository
git clone https://github.com/apmlabs/OnyxPoker.git
cd OnyxPoker/client

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy ..\.env.example .env
# Edit .env with your OpenAI API key
```

### Configuration

**Client .env file:**
```bash
# Server connection
ONYXPOKER_SERVER_URL=http://54.80.204.92:5000
ONYXPOKER_API_KEY=test_key_12345

# OpenAI GPT-4o Vision (REQUIRED)
OPENAI_API_KEY=sk-your-key-here

# Optional settings
SCREENSHOT_DELAY=1.0
MAX_RETRIES=3
```

**Get OpenAI API Key:**
1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy key (starts with `sk-`)

## Testing

### Test Vision Detection
```bash
# Take screenshot of poker table
# Save as poker_table.png

# Test GPT-4o vision
python test_vision.py poker_table.png
```

Expected output:
```
✅ Detection Results:
Hero Cards:       ['As', 'Kh']
Community Cards:  ['Qd', 'Jc', 'Ts']
Pot:              $150
Hero Stack:       $500
Confidence:       0.95
```

### Test Server Connection
```bash
# Test health endpoint
curl http://54.80.204.92:5000/health

# Test poker analysis
curl -X POST http://54.80.204.92:5000/analyze-poker \
  -H "Authorization: Bearer test_key_12345" \
  -H "Content-Type: application/json" \
  -d '{"hero_cards":["As","Kh"],"pot":150,"hero_stack":500,"to_call":20}'
```

## Security

### Current Setup
- API key authentication (test_key_12345)
- Rate limiting (60 req/min)
- CORS enabled
- Firewall: Port 5000 open

### Production Recommendations
1. **Change API key** - Generate secure key
2. **Enable HTTPS** - Use nginx + Let's Encrypt
3. **Restrict IPs** - Firewall rules for client IPs only
4. **Rotate keys** - Regular API key rotation

### Generate Secure API Key
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Monitoring

### Server Logs
```bash
# Application logs
tail -f /var/log/onyxpoker/server.log

# Error logs
tail -f /var/log/onyxpoker/error.log

# Systemd logs
sudo journalctl -u onyxpoker -f
```

### Health Check
```bash
# Check server health
curl http://54.80.204.92:5000/health

# Should return: {"status":"healthy"}
```

## Troubleshooting

### Client Issues

**"OPENAI_API_KEY not found"**
- Set environment variable or add to .env file
- Verify key starts with `sk-`

**"Connection refused"**
- Check server is running: `curl http://54.80.204.92:5000/health`
- Verify firewall allows port 5000
- Check API key is correct

**"Invalid API key"**
- Verify OpenAI API key is valid
- Check you have GPT-4o access
- Try regenerating key

### Server Issues

**"Service not running"**
```bash
sudo systemctl status onyxpoker
sudo systemctl start onyxpoker
```

**"Kiro CLI not found"**
```bash
which kiro-cli
# Should return: /home/ubuntu/.local/bin/kiro-cli
```

**"Port already in use"**
```bash
sudo lsof -i :5000
sudo systemctl restart onyxpoker
```

## Cost Analysis

### GPT-4o Vision API
- **Per hand**: ~$0.002
- **100 hands/day**: $6/month
- **1000 hands/day**: $60/month

### AWS Server
- **t3.medium**: ~$30/month
- **20GB storage**: ~$2/month
- **Total**: ~$32/month

### Total Cost
- Casual player: $38/month
- Serious grinder: $92/month

## Performance

### Expected Response Times
- Vision detection: 3-5 seconds
- Kiro CLI analysis: 2-5 seconds
- Total cycle: 5-10 seconds

### Optimization Tips
1. Keep Kiro CLI warm (persistent process)
2. Cache button positions
3. Batch API calls when possible
4. Use Gemini 2.0 Flash for 50% cost savings
