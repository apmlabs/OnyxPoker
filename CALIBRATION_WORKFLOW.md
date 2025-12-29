# 🎯 Hotkey-Based Calibration - How It Works

## ✅ Solution Implemented: Hotkey Workflow (No Window Focus Issues)

---

## The Problem We Solved

**Issue**: Windows cannot capture background windows
- If client window covers poker table → Screenshot captures client, not poker!
- Side-by-side windows not possible on single monitor

**Solution**: Hotkey-based workflow
- User hides client with F12
- User presses Ctrl+T to capture in background
- No window focus issues!

---

## 🚀 Complete Calibration Flow

### Step 1: Open Calibration
```
You: Press Ctrl+C
Bot: Opens calibration tab
Overlay: Shows "Step 1: Scan Windows"
```

### Step 2: Scan & Select Window
```
You: Click "Scan Windows"
Bot: Lists all poker windows
You: Select your PokerStars window
You: Click "Select"
Overlay: Shows "Step 3: Press F12, then Ctrl+T"
```

### Step 3: Capture Table (Hotkey!)
```
You: Press F12 (hide client)
Poker table now visible, not covered
You: Press Ctrl+T (capture in background)
Bot: Takes screenshot of poker table
Bot: Runs auto-detection
Bot: Shows client with preview
Overlay: Shows "Review preview and save"
```

### Step 4: Review & Save
```
You: Look at preview (colored boxes on table)
You: Click "Save Configuration"
Bot: Saves config.py
Overlay: Shows "Test: Ctrl+T or F9"
```

### Step 5: Test
```
You: Press Ctrl+T (test OCR)
Bot: Captures table, shows OCR results
You: Verify pot/stacks are correct
Overlay: Shows "✅ Ready - Press F9 for advice"
```

---

## 📱 Overlay Guidance (Step-by-Step)

### State 1: Not Calibrated
```
┌─────────────────────────────┐
│ 🎰 OnyxPoker                │
│ ─────────────────────────── │
│ 📋 Setup Needed             │
│ Press Ctrl+C to calibrate   │
│ Or F12 to open main window  │
│ ─────────────────────────── │
│ Step 1: Scan Windows        │
│ Step 2: Select poker window │
│ Step 3: Press F12, then Ctrl+T │
└─────────────────────────────┘
```

### State 2: Window Selected
```
┌─────────────────────────────┐
│ 🎰 OnyxPoker                │
│ ─────────────────────────── │
│ 📸 Capture Table            │
│ Press F12 to hide this window │
│ Then press Ctrl+T to capture │
│ ─────────────────────────── │
│ ✓ Window selected           │
│ Next: F12 (hide)            │
│ Then: Ctrl+T (capture)      │
└─────────────────────────────┘
```

### State 3: Calibrated, Ready to Test
```
┌─────────────────────────────┐
│ 🎰 OnyxPoker                │
│ ─────────────────────────── │
│ 📸 Test OCR                 │
│ Press Ctrl+T to test OCR    │
│ Or F9 to capture & analyze  │
│ ─────────────────────────── │
│ Calibration saved!          │
│ Test: Ctrl+T                │
│ Or: F9 to analyze           │
└─────────────────────────────┘
```

### State 4: Ready to Play
```
┌─────────────────────────────┐
│ 🎰 OnyxPoker                │
│ ─────────────────────────── │
│ ✅ Ready!                   │
│ Press F9 to get AI advice   │
│ Bot is ready to help!       │
│ ─────────────────────────── │
│ All set!                    │
│ F9: Get advice              │
│ F10: Start bot              │
└─────────────────────────────┘
```

---

## ⌨️ Ctrl+T is Context-Aware!

**Smart Hotkey**: Ctrl+T does different things based on context

### If Window Selected But Not Calibrated:
```
Ctrl+T → Auto-Detect Elements
- Captures poker table
- Runs computer vision
- Shows preview with boxes
```

### If Already Calibrated:
```
Ctrl+T → Test OCR
- Captures poker table
- Runs OCR (pot, stacks, cards)
- Shows results in Debug tab
```

---

## 🎮 Complete Example Session

### First Time (Calibration):

```
You: python poker_gui.py
Bot: *Opens, auto-hides after 2 seconds*

Overlay: "📋 Setup Needed - Press Ctrl+C"
         "Step 1: Scan Windows"
         "Step 2: Select poker window"
         "Step 3: Press F12, then Ctrl+T"

You: *Press Ctrl+C*
Bot: *Shows calibration tab*

You: *Click "Scan Windows"*
Bot: *Lists poker windows*

You: *Select window, click "Select"*
Bot: *Activates window*

Overlay: "📸 Capture Table"
         "Press F12 to hide this window"
         "Then press Ctrl+T to capture"

You: *Press F12*
Bot: *Hides client window*
Poker table now fully visible!

You: *Press Ctrl+T*
Bot: *Captures poker table in background*
Bot: *Runs auto-detection*
Bot: *Shows client with preview*

You: *Review colored boxes on preview*
You: *Click "Save Configuration"*

Overlay: "📸 Test OCR"
         "Press Ctrl+T to test OCR"

You: *Press Ctrl+T*
Bot: *Tests OCR, shows results*

You: *Verify pot/stacks correct*

Overlay: "✅ Ready - Press F9 for advice"
```

### Every Session After:

```
You: python poker_gui.py
Bot: *Opens, auto-hides*

Overlay: "✅ Ready - Press F9 for advice"

You: *Play poker, press F9 when needed*
```

---

## 🎯 Key Points

1. **No window focus issues** - Ctrl+T captures in background
2. **Overlay guides you** - Always shows next step
3. **Context-aware hotkey** - Ctrl+T does the right thing
4. **Single monitor friendly** - F12 hides client, Ctrl+T captures
5. **Clear instructions** - Overlay shows exactly what to do

---

## 🔧 Technical Details

### How Ctrl+T Works:

```python
def on_ctrl_t_test_ocr(self):
    # Check if window selected but not calibrated
    if has_selected_window and not_calibrated:
        # Do auto-detection
        auto_detect()
    else:
        # Do OCR test
        capture_debug()
```

### How Background Capture Works:

```python
# User presses F12 → Client hides
# Poker table now visible
# User presses Ctrl+T → Captures poker table
# No window focus needed!
```

---

## ✅ Advantages

1. **Works on single monitor** - No side-by-side needed
2. **No window focus issues** - Captures in background
3. **Clear guidance** - Overlay shows every step
4. **Context-aware** - Ctrl+T does the right thing
5. **Fast** - Just 2 hotkeys (F12, Ctrl+T)

---

**Calibration is now simple and works perfectly on single monitor!** 🚀
