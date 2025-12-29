# Calibration Flow - Complete Guide

## Overview

Calibration is the process of teaching the bot where poker table elements are located on your screen. This is a **one-time setup** that must be done before the bot can read your poker table.

## Why Calibration is Needed

The bot needs to know:
- Where is the poker table window?
- Where are the action buttons (Fold, Call, Raise)?
- Where is the pot amount displayed?
- Where are your cards?
- Where are the stack amounts?

Every poker client (PokerStars, 888poker, etc.) has different layouts, so calibration is required.

## Current Workflow (F7 → F8 → Save)

### Step 1: Focus Poker Window
- Open PokerStars
- Sit at a table
- Click on the poker window to make it active

### Step 2: Capture Window Info (F7)
- Press **F7** hotkey
- Bot captures currently focused window
- Stores window title, size, position
- Activity Log shows: "✓ Window captured: [title]"

**What F7 Does**:
- Gets active window with `pygetwindow.getActiveWindow()`
- Stores window metadata (NOT a screenshot yet)
- Updates overlay: "Press F8 to capture"

### Step 3: Take Screenshot & Detect (F8)
- Press **F8** hotkey
- Bot takes screenshot of window from Step 2
- Runs computer vision to detect buttons/pot
- Shows preview with colored rectangles
- Activity Log shows: "✓ Screenshot captured", "✓ Preview updated"

**What F8 Does**:
- Calls `window_detector.capture_window()` → PIL image
- Calls `window_detector.detect_poker_elements()` → finds buttons/pot
- Calls `window_detector.create_preview()` → draws colored boxes
- Updates Calibration tab canvas with preview

### Step 4: Review Preview
- Look at Calibration tab
- See colored rectangles on poker table:
  - **Red boxes**: Action buttons (Fold, Call, Raise)
  - **Green box**: Pot region
- Check confidence score (should be >50%)

### Step 5: Save Configuration
- Click "Save Configuration" button
- Bot writes `config.py` with detected regions
- Activity Log shows: "✅ Calibration saved"

**What Save Does**:
- Writes `TABLE_REGION = (x, y, width, height)`
- Writes `BUTTON_REGIONS = {'fold': (x,y,w,h), ...}`
- Writes `POT_REGION = (x, y, w, h)`
- Updates overlay: "Press F8 to test OCR"

### Step 6: Test OCR (Optional)
- Press **F8** again
- Bot reads pot/stacks from poker table
- Shows results in Debug tab
- Verify values are correct

## Alternative: Button-Based Workflow

### Using GUI Buttons (Not Recommended)

**Problem**: Clicking "Capture Active Window" button makes GUI active, not poker window

**Why It Doesn't Work**:
1. User clicks poker window (poker window is active)
2. User clicks "Capture Active Window" button
3. GUI becomes active (poker window loses focus)
4. Bot captures GUI window, not poker window

**Solution**: Use F7 hotkey instead

## Troubleshooting

### "No active window detected"
- Make sure you clicked on poker window before pressing F7
- Try clicking poker window again, then immediately press F7

### "Screenshot shows wrong window"
- You pressed F8 before F7
- Start over: F7 (capture window) → F8 (take screenshot)

### "No buttons detected" (confidence <50%)
- Poker table might be too small
- Try resizing poker window to be larger
- Make sure table is fully visible (not covered by other windows)

### "Preview doesn't show up"
- Check Calibration tab (not Control or Debug tab)
- Look for canvas with colored rectangles
- If blank, F8 might have failed - check Activity Log

## Technical Details

### What Gets Stored in config.py

```python
# Window region
TABLE_REGION = (100, 50, 1200, 800)  # x, y, width, height

# Button positions
BUTTON_REGIONS = {
    "fold": (300, 700, 80, 40),   # x, y, width, height
    "call": (400, 700, 80, 40),
    "raise": (500, 700, 80, 40),
}

# Pot display area
POT_REGION = (550, 300, 100, 30)  # x, y, width, height
```

### Computer Vision Detection

**How It Works**:
1. Convert screenshot to grayscale
2. Find edges with Canny edge detection
3. Find contours (potential buttons)
4. Filter by size (buttons are 60-150px wide, 30-60px tall)
5. Sort left to right (fold, call, raise)
6. Look for text with digits in center-top (pot)

**Confidence Score**:
- 0.7 if 3+ buttons detected
- +0.2 if pot region has digits
- Total: 0.0 to 0.9

### Placeholder Detection

**How Bot Knows If Calibrated**:
```python
# Placeholder values (not calibrated)
TABLE_REGION = (0, 0, 0, 0)           # Empty
TABLE_REGION = (100, 100, 800, 600)   # Default

# Real calibration (calibrated)
TABLE_REGION = (150, 75, 1280, 720)   # Actual values
```

## Future Improvements

1. **Manual coordinate entry** - For when auto-detection fails
2. **Visual calibration tool** - Click on buttons to mark them
3. **Multiple profiles** - Save different configs for different tables
4. **Validation step** - Test OCR before saving
5. **Recalibration detection** - Warn if window size changes
