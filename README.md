# OnyxPoker - AI-Powered Poker Assistant

**Status**: ✅ GPT-5.2 Vision | Testing in Progress

## Quick Start (Windows)

```bash
# 1. Set OpenAI API key
set OPENAI_API_KEY=sk-your-key-here

# 2. Install dependencies
cd client
pip install -r requirements.txt

# 3. Run helper bar
python helper_bar.py
```

## Hotkeys
- **F9** - Get AI advice (analyzes active window)
- **F10** - Toggle bot mode (not implemented)
- **F11** - Emergency stop
- **F12** - Hide/show helper bar

## How It Works
1. Press F9 with poker table as active window
2. GPT-5.2 Vision analyzes the screenshot
3. Returns: cards, board, pot, recommended action
4. Results shown in helper bar (6-9 seconds)

## Architecture
```
Windows Client (helper_bar.py)
    ↓ Screenshot active window
    ↓ GPT-5.2 Vision API
    ↓ JSON response with game state + decision
    ↓ Display in helper bar UI
```

## Files
```
client/
  helper_bar.py      # Main UI - wide bar docked to bottom
  vision_detector.py # GPT-5.2 API calls
  poker_reader.py    # Screenshot + state parsing
  config.py          # TABLE_REGION config
  requirements.txt   # Dependencies
```

## Cost
- GPT-5.2 Vision: ~$2 per 1000 hands
- Casual (100 hands/day): ~$6/month

## Legal
⚠️ Research/educational only. Use on play money tables.
