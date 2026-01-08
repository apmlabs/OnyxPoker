# OnyxPoker - Complete User Guide

**Last Updated**: December 29, 2025 16:26 UTC  
**Status**: Ready for Testing

---

## 🎯 What Is OnyxPoker?

An AI-powered poker assistant that:
- Reads your poker table (cards, pot, stacks)
- Analyzes game state with Kiro CLI
- Provides real-time advice
- Works on single monitor with hotkeys

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Get Latest Code

```bash
cd /home/ubuntu/mcpprojects/onyxpoker
git pull origin main
```

### Step 2: Launch GUI

```bash
cd client
python poker_gui.py
```

**What happens:**
- Main window opens (maximized)
- Mini overlay appears in corner
- After 2 seconds, main window auto-hides
- Mini overlay shows: "📋 Setup Needed - Press Ctrl+C to calibrate"

### Step 3: First Time Setup (2 minutes)

**Follow the overlay guidance:**

1. **Press Ctrl+C** → Opens calibration tab
2. **Click "Scan Windows"** → Lists poker windows
3. **Select your PokerStars window** → Click "Select"
4. **Press F12** → Hides client window
5. **Press Ctrl+T** → Captures table, auto-detects elements
6. **Review preview** → Colored boxes on table
7. **Click "Save Configuration"** → Saves config
8. **Press Ctrl+T** → Tests OCR
9. **Verify results** → Pot/stacks should be correct

**Done!** Overlay now shows: "✅ Ready - Press F9 for advice"

---

## ⌨️ All Hotkeys

| Key | Action | When to Use |
|-----|--------|-------------|
| **Ctrl+C** | Open Calibration | First time setup |
| **Ctrl+T** | Auto-Detect or Test OCR | After selecting window |
| **F9** | Capture & Analyze | Get AI advice anytime |
| **F12** | Show/Hide Main Window | Check logs, debug |
| **Ctrl+H** | Toggle Mini Overlay | Show/hide overlay |
| **F10** | Start/Stop Bot | Auto mode only |
| **F11** | Emergency Stop | Stop bot immediately |

---

## 📱 Mini Overlay Guide

The overlay **always shows what to do next**:

### Before Calibration:
```
┌─────────────────────────────┐
│ 🎰 OnyxPoker                │
│ ─────────────────────────── │
│ 📋 Setup Needed             │
│ Press Ctrl+C to calibrate   │
│ ─────────────────────────── │
│ Step 1: Scan Windows        │
│ Step 2: Select window       │
│ Step 3: F12, then Ctrl+T    │
└─────────────────────────────┘
```

### After Calibration:
```
┌─────────────────────────────┐
│ 🎰 OnyxPoker                │
│ ─────────────────────────── │
│ ✅ Ready!                   │
│ Press F9 to get AI advice   │
│ ─────────────────────────── │
│ F9:Analyze  F12:Main        │
└─────────────────────────────┘
```

### During Play:
```
┌─────────────────────────────┐
│ 🎰 OnyxPoker                │
│ ─────────────────────────── │
│ Table: $150 pot             │
│ Cards: A♠ K♥                │
│ Stack: $500                 │
│ ─────────────────────────── │
│ 💡 CALL $20                 │
│ Strong hand, pot odds good  │
│ ─────────────────────────── │
│ F9:Analyze  F12:Main        │
└─────────────────────────────┘
```

---

## 🎮 Complete Workflow

### First Time (Setup):

```
1. Launch: python poker_gui.py
   → GUI opens, overlay appears, auto-hides

2. Overlay shows: "📋 Setup Needed - Press Ctrl+C"

3. Press Ctrl+C
   → Opens calibration tab

4. Click "Scan Windows"
   → Lists poker windows

5. Select window, click "Select"
   → Window activated

6. Press F12
   → Hides client window
   → Poker table now fully visible

7. Press Ctrl+T
   → Captures table in background
   → Runs auto-detection
   → Shows preview with colored boxes

8. Review preview, click "Save Configuration"
   → Saves config.py

9. Press Ctrl+T
   → Tests OCR
   → Shows results in Debug tab

10. Verify pot/stacks correct
    → Press F12 to hide

11. Overlay shows: "✅ Ready - Press F9 for advice"
```

### Every Session After:

```
1. Launch: python poker_gui.py
   → Auto-hides after 2 seconds

2. Overlay shows: "✅ Ready - Press F9 for advice"

3. Open PokerStars (fullscreen)

4. Play poker normally

5. When you need advice:
   → Press F9
   → Overlay updates with decision
   → Shows reasoning

6. Make your decision manually

7. Repeat as needed
```

---

## 🔧 Troubleshooting

### "Overlay shows 'Setup Needed' but I already calibrated"

**Solution**: Press Ctrl+T to test OCR, this updates status

### "Hotkeys don't work"

**Solution**: 
- Run as administrator (Windows)
- Check Activity Log (F12 → Control Panel)

### "OCR shows $0 for everything"

**Solution**:
- Press Ctrl+C to recalibrate
- Make sure PokerStars table is visible
- Try different PokerStars theme (use default)

### "Ctrl+T doesn't capture"

**Solution**:
- Make sure you pressed F12 first (to hide client)
- Poker table must be visible on screen
- Check Activity Log for errors

### "Cards show '??'"

**Solution**:
- This is normal (card recognition not yet implemented)
- Bot still works with pot/stacks/actions

---

## 📊 What Works Now

### ✅ Implemented:
- Server running (systemd service)
- Client connects to server
- Screenshot capture (background)
- Kiro CLI validation
- 7 hotkeys (all working)
- Mini overlay with guidance
- System tray
- Auto-hide main window
- Setup status detection
- Window geometry persistence
- Hotkey-based calibration

### 🔄 In Progress:
- Card recognition (shows '??' for now)
- Multi-table support
- Advanced error recovery

---

## 🎯 Tips & Best Practices

1. **Calibration is one-time** - Only need to do once per setup
2. **F12 before Ctrl+T** - Always hide client before capturing
3. **Use F9 liberally** - Get advice anytime, no cost
4. **Check Activity Log** - Press F12 to see what's happening
5. **Default theme works best** - Use PokerStars default theme

---

## 📚 More Documentation

- **HOTKEY_WORKFLOW.md** - Complete hotkey workflow
- **CALIBRATION_WORKFLOW.md** - Detailed calibration guide
- **HOTKEYS_GUIDE.md** - All hotkeys explained
- **AGENTS.md** - Technical learnings
- **TESTING_PLAN.md** - Testing procedures

---

## 🆘 Getting Help

### Check Activity Log:
1. Press F12
2. Control Panel tab
3. Read Activity Log
4. Click "Copy Logs" to share

### Report Issues:
Include:
- Activity Log (copy/paste)
- What you were doing
- Screenshot of GUI
- Screenshot of poker table

---

## ⚠️ Important Notes

1. **Play Money Only** - Test on play money tables first
2. **Single Monitor** - Designed for single monitor setup
3. **Windows Only** - Client requires Windows OS
4. **Background Capture** - Must hide client before capturing

---

**Ready to play poker with AI assistance!** 🎰🚀
