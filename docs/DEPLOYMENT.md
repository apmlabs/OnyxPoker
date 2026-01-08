# OnyxPoker Deployment Guide

## Quick Start (Windows Client)

```bash
# 1. Set OpenAI API key
set OPENAI_API_KEY=sk-your-key-here

# 2. Install dependencies
cd client
pip install -r requirements.txt

# 3. Run
python helper_bar.py
```

Then: Focus poker window → Press F9 → See advice

## Requirements

- Windows 10/11
- Python 3.8+
- OpenAI API key with GPT-5.2 access

## Get OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy key (starts with `sk-`)

## Hotkeys

| Key | Action |
|-----|--------|
| F9 | Get AI advice |
| F10 | Start bot loop |
| F11 | Stop bot |
| F12 | Hide/show bar |

## Cost

- ~$0.002 per hand
- ~$2 per 1000 hands

## Optional: Kiro Analysis Server

For remote screenshot analysis (send from Windows to Linux):

### Server Setup (Linux)
```bash
# On AWS EC2 (54.80.204.92)
cd /home/ubuntu/mcpprojects/onyxpoker-server/server
source venv/bin/activate
python kiro_analyze.py
```

Server runs on port 5001. Endpoints:
- `POST /analyze` - Send screenshot for analysis
- `POST /logs` - Send session logs
- `GET /health` - Health check

### Client Scripts
```bash
# Send screenshots to server
python send_to_kiro.py

# Send session logs
python send_logs.py
```

### AWS Security Group

Ensure port 5001 is open:
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 5001 \
  --cidr 0.0.0.0/0
```

## Troubleshooting

**"OPENAI_API_KEY not found"**
- Set environment variable: `set OPENAI_API_KEY=sk-...`

**"No module named 'openai'"**
- Run: `pip install -r requirements.txt`

**Server connection refused**
- Check server running: `curl http://54.80.204.92:5001/health`
- Check port 5001 open in security group

## File Structure

```
client/
  helper_bar.py      # Main UI
  vision_detector.py # GPT-5.2 API
  send_to_kiro.py    # Send screenshots to server
  send_logs.py       # Send logs to server
  screenshots/       # Auto-saved screenshots
  logs/              # Session logs (JSONL)
```
