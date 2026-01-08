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

## Live Testing Workflow

### 1. Play Session (Windows)
```bash
# Start helper bar
python helper_bar.py

# Play poker, press F9 for each decision
# Screenshots auto-save to client/screenshots/
# Logs auto-save to client/logs/session_*.jsonl
```

### 2. Send Data to Server (Windows)
```bash
# Send screenshots
python send_to_kiro.py

# Send logs  
python send_logs.py
```

### 3. Analyze on Server (Linux)
```bash
# SSH to server
ssh ubuntu@54.80.204.92

# Analyze latest session
cd /home/ubuntu/mcpprojects/onyxpoker-server/server
python analyze_session.py

# Or test screenshots with GPT
cd /home/ubuntu/mcpprojects/onyxpoker/client
python test_screenshots.py /path/to/uploads/
```

### 4. Review & Iterate
- Check analysis output for mistakes
- Update `docs/ANALYSIS_NOTES.md` with findings
- Tune prompt in `vision_detector.py` if needed

## Log Format (JSONL)

Each line in session log:
```json
{
  "timestamp": "2026-01-08T13:30:00",
  "screenshot": "20260108_133000.png",
  "hero_cards": ["As", "Kh"],
  "board": ["Qd", "Jc", "Ts"],
  "pot": 0.15,
  "position": "BTN",
  "action": "raise",
  "amount": 0.45,
  "reasoning": "Strong hand in position...",
  "confidence": 0.95,
  "elapsed": 6.2
}
```

Screenshot filename matches log entry for easy correlation.

## Requirements

- Windows 10/11
- Python 3.8+
- OpenAI API key with GPT-5.2 access

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

Server runs on port 5001 at 54.80.204.92.

Endpoints:
- `POST /analyze` - Receive screenshot
- `POST /logs` - Receive session logs
- `GET /health` - Health check

## Troubleshooting

**"OPENAI_API_KEY not found"**
- Set environment variable: `set OPENAI_API_KEY=sk-...`

**"No module named 'openai'"**
- Run: `pip install -r requirements.txt`

**Server connection refused**
- Check server running: `curl http://54.80.204.92:5001/health`
