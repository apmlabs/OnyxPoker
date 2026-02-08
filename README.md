# OnyxPoker - AI Poker Assistant

AI-powered poker assistant using GPT-5.2 vision to read tables and provide decisions.

## Live Results (Session 40)

**141 hands played** with value_maniac strategy:
- Overbets with pairs getting paid consistently
- Big wins: JJ (~$10), Set 4s (~$8), Quads (~$7), Trip Aces (~$4)
- Correct folds: KJ vs $14.55 all-in, AK vs $7.46 all-in

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
3. Click on poker window to make it active
4. Press **F9** - AI analyzes the table and shows:
   - **Line 1**: Action for all 6 positions (UTG:FOLD | MP:FOLD | CO:RAISE | BTN:RAISE | SB:RAISE | BB:CHECK)
   - **Line 2**: What to do vs a raise (CALL any, CALL up to 15bb, CALL up to 4bb, or FOLD)
   - **Stats panel**: All hand analysis flags for research

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
- **Memory reading** (Windows) runs in parallel — finds buffer in 2-4s, then polls every 200ms (<1ms) for live action updates in the right panel. Falls back to GPT cards when memory unavailable. Time label shows `LIVE (N)` during polling. Catches GPT card errors with ground truth from process memory
- **Strategy Engine** applies hardcoded poker logic from strategy files
- **Preflop**: Shows advice for ALL 6 positions automatically
- **~5.5 seconds** per analysis (memory finishes in 2-4s, GPT in 5.5s)

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
  poker_logic.py       # Hand analysis + decisions (analyze_hand is single source of truth)
  poker_sim.py         # Strategy simulator
  strategy_engine.py   # Lite mode strategy
  pokerstrategy_*      # Strategy definition files
  requirements.txt     # Dependencies
```

## Architecture

All hand analysis uses `analyze_hand()` - single source of truth that returns:
- `strength`: 1-9 (high card to straight flush)
- `desc`: Human readable description
- `is_overpair`, `has_top_pair`, `two_pair_type`, etc.

## Legal

For research and educational purposes only. Use on play money tables.
