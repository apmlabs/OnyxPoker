# Hotkeys & Mini Overlay - Quick Guide

**Date**: December 29, 2025 15:30 UTC  
**Status**: ✅ Implemented

---

## 🎮 What's New

### 1. Mini Overlay Panel
- **Always-on-top** window (stays above PokerStars)
- **320×240 pixels** (small, non-intrusive)
- **Semi-transparent** background
- **Draggable** - position anywhere on screen

**Shows:**
- Table info (pot size)
- Your cards
- Your stack
- AI decision (FOLD/CALL/RAISE)
- Brief reasoning
- Hotkey hints

### 2. Global Hotkeys
Work even when PokerStars is focused!

- **F9** - Capture screenshot and analyze
- **F10** - Start/Stop bot
- **F11** - Emergency stop (shows main window)
- **F12** - Show/Hide main window

### 3. System Tray Icon
- Bot runs in background
- Right-click for menu
- Quick access to all functions

---

## 🚀 How to Use

### First Time Setup

1. **Install new dependencies:**
   ```bash
   cd client
   pip install keyboard pystray
   ```

2. **Pull latest code:**
   ```bash
   git pull origin main
   ```

3. **Launch GUI:**
   ```bash
   python poker_gui.py
   ```

**What happens:**
- Main window opens (maximized)
- Mini overlay appears (top-right corner)
- System tray icon appears (taskbar)
- Hotkeys registered (F9-F12)

---

## 🎯 Single Monitor Workflow

### Setup Phase

1. **Launch OnyxPoker GUI**
   - Calibrate screen regions
   - Test connection
   - Configure bot settings

2. **Position Mini Overlay**
   - Drag to corner of screen
   - Make sure it doesn't block poker table

3. **Open PokerStars**
   - Can use fullscreen or windowed
   - Mini overlay stays on top

### Playing Phase

1. **Hide Main Window**
   - Press **F12** or minimize
   - Mini overlay stays visible

2. **Play Poker**
   - PokerStars takes full screen
   - Mini overlay shows in corner

3. **When You Need Analysis**
   - Press **F9** - Bot captures and analyzes
   - Mini overlay updates with decision
   - No need to switch windows!

4. **Start/Stop Bot**
   - Press **F10** to toggle
   - Mini overlay shows status

5. **Emergency Stop**
   - Press **F11** - Stops bot immediately
   - Shows main window for review

6. **Check Full GUI**
   - Press **F12** - Shows main window
   - Review logs, OCR, validation
   - Press **F12** again to hide

---

## 📱 Mini Overlay Layout

```
┌─────────────────────────────┐
│ 🎰 OnyxPoker                │ ← Header
│ ─────────────────────────── │
│ Table: $150 pot             │ ← Pot size
│ Cards: A♠ K♥                │ ← Your cards
│ Stack: $500                 │ ← Your stack
│ ─────────────────────────── │
│ 💡 CALL $20                 │ ← AI Decision
│ Strong hand, pot odds good  │ ← Brief reasoning
│ ─────────────────────────── │
│ [F9] Analyze [F12] Main     │ ← Hotkey hints
└─────────────────────────────┘
```

**Features:**
- **Draggable** - Click and drag anywhere
- **Always on top** - Never hidden by other windows
- **Real-time updates** - Changes as game progresses
- **Color-coded** - Green for good, yellow for caution

---

## 🎛️ System Tray Menu

**Right-click tray icon:**
- Show Main Window
- Show Mini Overlay
- Hide Mini Overlay
- ─────────────────
- Start Bot
- Stop Bot
- ─────────────────
- Exit

---

## ⌨️ Hotkey Reference

| Key | Action | When to Use |
|-----|--------|-------------|
| **F9** | Capture & Analyze | When you want bot's opinion |
| **F10** | Start/Stop Bot | Toggle automation |
| **F11** | Emergency Stop | Something wrong, stop now! |
| **F12** | Show/Hide Main | Check logs, settings, debug |

**Note**: Hotkeys work globally (even when PokerStars is focused)

---

## 🎮 Example Workflow

### Scenario: Playing Fullscreen Poker

1. **Start:**
   ```
   - Launch poker_gui.py
   - Calibrate once
   - Press F12 to hide main window
   - Open PokerStars fullscreen
   ```

2. **During Play:**
   ```
   - Mini overlay visible in corner
   - Shows: "Waiting for action..."
   - You get dealt cards
   - Press F9 to analyze
   - Mini overlay updates: "💡 CALL $20"
   - Shows reasoning: "Strong hand..."
   - You make decision
   ```

3. **Need More Info:**
   ```
   - Press F12 to show main window
   - Check Activity Log
   - Review full reasoning
   - Check OCR accuracy
   - Press F12 to hide again
   ```

4. **Start Automation:**
   ```
   - Press F10 to start bot
   - Mini overlay shows: "Playing"
   - Bot makes decisions automatically
   - Mini overlay updates in real-time
   ```

5. **Emergency:**
   ```
   - Something wrong?
   - Press F11 - Immediate stop
   - Main window appears
   - Review what happened
   ```

---

## 🔧 Troubleshooting

### "Hotkeys don't work"
**Solution**: Run as administrator
```bash
Right-click Python → Run as administrator
```

### "Mini overlay not showing"
**Solution**: Check if it's hidden
- Press F12 to show main window
- System Tray → Right-click → Show Mini Overlay

### "Can't install keyboard/pystray"
**Solution**: Install manually
```bash
pip install keyboard==0.13.5
pip install pystray==0.19.5
```

### "Mini overlay blocks poker table"
**Solution**: Drag it to corner
- Click and drag to reposition
- Place in corner where it doesn't block

---

## 💡 Tips & Tricks

**Best Practices:**
1. Position mini overlay in top-right corner
2. Use F9 for quick analysis (no window switching)
3. Keep main window hidden during play (F12)
4. Use F11 for emergency stops
5. Check Activity Log periodically (F12)

**Performance:**
- Mini overlay uses minimal resources
- Hotkeys have no performance impact
- System tray runs in background

**Customization:**
- Mini overlay is draggable
- Can be hidden if not needed
- Hotkeys can be disabled in code

---

## 🎯 Next Steps

1. **Pull latest code**
2. **Install dependencies** (keyboard, pystray)
3. **Launch GUI**
4. **Position mini overlay**
5. **Test hotkeys** (F9-F12)
6. **Play poker with overlay visible!**

---

**Now you can play fullscreen poker with AI assistance!** 🎰🚀
