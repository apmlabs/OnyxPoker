# OnyxPoker Auto-Calibration

## Quick Start

Run the calibration wizard:
```cmd
python calibration_ui.py
```

## How It Works

### Step 1: Window Detection
- Automatically scans for PokerStars windows
- Shows all detected poker tables
- Select the one you want to use

### Step 2: Auto-Detection
- Captures window screenshot
- Uses computer vision to find:
  - Action buttons (Fold, Call, Raise)
  - Pot region
  - Table layout
- Shows confidence score

### Step 3: Verification
- Preview shows detected regions highlighted
- Red boxes = Action buttons
- Green box = Pot region
- Confidence score indicates detection quality

### Step 4: Save
- Saves configuration to `config.py`
- Ready to use with poker bot

## Important Notes

⚠️ **Window Visibility**: On Windows, the poker table window MUST be visible (not minimized) for screenshot capture. This is a Windows limitation.

✅ **What's Detected Automatically**:
- Table window position and size
- Action buttons (Fold, Call, Raise)
- Pot region

📝 **What Needs Manual Adjustment** (if needed):
- Card positions (hole cards, community cards)
- Stack positions for each seat

## Troubleshooting

**"No poker windows found"**
- Make sure PokerStars is open
- Join a table
- Window must be visible (not minimized)

**"Low confidence in detection"**
- Make sure you're at an active table
- Window should be fully visible
- Try different table theme (default works best)

**"No action buttons detected"**
- Ensure it's your turn (buttons visible)
- Or wait until buttons appear
- Table must not be in lobby/waiting state

## Next Steps

After calibration:
1. Test OCR: `python poker_bot.py --execution analysis --hands 1`
2. Verify readings are accurate
3. Adjust card/stack regions manually if needed in `config.py`
