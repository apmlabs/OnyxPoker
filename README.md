# OnyxPoker - AI Poker Assistant

AI-powered poker assistant using GPT-5.2 vision to read tables and provide decisions.

## Quick Start

```bash
# 1. Set OpenAI API key
export OPENAI_API_KEY='sk-your-key'

# 2. Install dependencies
cd client
pip install -r requirements.txt

# 3. Run
python helper_bar.py
```

## Usage

1. Open PokerStars and sit at a table
2. Run `python helper_bar.py` - a bar appears at bottom of screen
3. Click on poker window to make it active
4. Press **F9** - AI analyzes the table and shows decision

## Hotkeys

| Key | Action |
|-----|--------|
| F9 | Get AI advice (one-time) |
| F10 | Start/stop bot mode |
| F11 | Emergency stop |
| F12 | Hide/show bar |

## How It Works

- **No calibration needed** - F9 screenshots the active window
- **GPT-5.2 Vision** reads cards, pot, stacks, buttons
- **AI Decision** with reasoning (fold/call/raise)
- **6-9 seconds** per analysis

## Cost

~$2 per 1000 hands (GPT-5.2 API)

## Files

```
client/
  helper_bar.py      # Main UI
  vision_detector.py # GPT-5.2 API wrapper
  poker_reader.py    # Screenshot + parse
  requirements.txt   # Dependencies
```

## Legal

For research and educational purposes only. Use on play money tables.
