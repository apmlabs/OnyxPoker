# Debug Log Export - Quick Guide

## What Was Added

**Activity Log (Control Panel Tab):**
- 📋 Copy Logs - Copy all logs to clipboard
- 💾 Save Logs - Save logs to timestamped .txt file
- Clear Log - Clear all logs

**Debug Tab:**
- 📋 Copy OCR - Copy OCR analysis to clipboard
- 📋 Copy State - Copy game state JSON to clipboard

## How to Use

### 1. When You See an Error

**In GUI:**
1. Go to Control Panel tab
2. Click "📋 Copy Logs"
3. Paste into chat/email/notepad

**Or:**
1. Click "💾 Save Logs"
2. Choose location
3. Share the .txt file

### 2. For Debug Tab Info

**OCR Analysis:**
1. Debug Tab → Click "📸 Capture Now"
2. Click "📋 Copy OCR"
3. Paste to share

**Game State:**
1. Debug Tab → Click "📸 Capture Now"
2. Click "📋 Copy State"
3. Paste to share

## What to Share When Reporting Issues

**Minimum:**
- Activity Log (Copy Logs button)
- What you were doing when error occurred

**Ideal:**
- Activity Log
- OCR Analysis (if OCR-related)
- Game State (if detection-related)
- Screenshot of GUI

## Example Issue Report

```
ISSUE: Kiro validation shows "invalid"

ACTIVITY LOG:
[14:54:12] INFO: Testing Kiro CLI validation...
[14:54:15] ERROR: Kiro validation failed: timeout
[14:54:15] INFO: Validation result: Invalid

OCR ANALYSIS:
Pot: $0
Stacks: [0, 0, 0, 0, 0, 0]
Cards: ['??', '??']

GAME STATE:
{
  "pot": 0,
  "stacks": [0, 0, 0, 0, 0, 0],
  "hero_cards": ["??", "??"]
}

WHAT I WAS DOING:
Clicked "Validate State" in Debug tab with no poker table open
```

## Next Steps

1. **Pull latest code:**
   ```bash
   git pull origin main
   ```

2. **Restart GUI:**
   ```bash
   python poker_gui.py
   ```

3. **Test validation again:**
   - Debug Tab → "✓ Validate State"
   - If error, click "📋 Copy Logs"
   - Paste logs to share

---

**Now you can easily capture and share debug info!**
