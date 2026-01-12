# OnyxPoker - AI Poker Assistant

AI-powered poker assistant using GPT-5.2 vision to read tables and provide decisions.

## Quick Start

```bash
# 1. Set OpenAI API key
export OPENAI_API_KEY='sk-your-key'

# 2. Install dependencies
cd client
pip install -r requirements.txt

# 3. Run (default: GPT-5.2 vision + strategy engine)
python helper_bar.py

# OR run in AI-only mode (GPT-5.2 does everything)
python helper_bar.py --ai-only

# OR use different strategy
python helper_bar.py --strategy sonnet
```

## Usage

1. Open PokerStars and sit at a table
2. Run `python helper_bar.py` - a bar appears at bottom of screen
3. **Select your position** using radio buttons at top (UTG/MP/CO/BTN/SB/BB)
4. Click on poker window to make it active
5. Press **F9** - AI analyzes the table and shows decision

## Hotkeys

| Key | Action |
|-----|--------|
| F9 | Get AI advice (one-time) |
| F10 | Start/stop bot mode |
| F11 | Emergency stop |
| F12 | Hide/show bar |

## How It Works

- **No calibration needed** - F9 screenshots the active window
- **GPT-5.2 Vision** reads cards, pot, stacks, buttons (96.9% accuracy)
- **Strategy Engine** applies hardcoded poker logic from strategy files
- **Manual Position** - Select your position via UI buttons
- **6-9 seconds** per analysis

**AI-Only Mode**: Use `--ai-only` flag for GPT-5.2 to make all decisions (old behavior)

## Strategy Simulator

Test strategies against realistic player pools:

```bash
cd client
python3 poker_sim.py 50000  # Run 50k hands
```

Results show BB/100 win rate for each strategy.

## Cost

~$2 per 1000 hands (GPT-5.2 API)

## Files

```
client/
  helper_bar.py        # Main UI
  vision_detector.py   # GPT-5.2 API wrapper
  poker_logic.py       # Hand evaluation + decisions
  poker_sim.py         # Strategy simulator
  strategy_engine.py   # Lite mode strategy
  pokerstrategy_*      # Strategy definition files
  requirements.txt     # Dependencies
```

## Legal

For research and educational purposes only. Use on play money tables.
