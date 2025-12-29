# 🎯 Complete Hotkey-Driven Workflow

## ✅ What Changed

You now have a **complete hotkey-driven workflow** - no need to see the main window!

---

## 🚀 The New Flow

### Step 1: Launch (10 seconds)

```bash
cd /c/AWS/onyx-client
git pull origin main
cd client
python poker_gui.py
```

**What happens**:
1. GUI opens (maximized)
2. Mini overlay appears in corner
3. **After 2 seconds**: Main window auto-hides
4. Mini overlay shows: **"📋 Setup Needed - Press Ctrl+C to calibrate"**

---

### Step 2: Calibrate (2 minutes) - ONE TIME ONLY

**Mini overlay shows**: "📋 Setup Needed - Press Ctrl+C to calibrate"

**You press**: **Ctrl+C**

**What happens**:
1. Main window appears
2. Switches to Calibration tab automatically
3. You see: "Scan Windows" button

**Then you**:
1. Click "🔍 Scan Windows"
2. Select your PokerStars window from list
3. Click "✓ Select"
4. Click "🎯 Auto-Detect Elements"
5. Review preview (colored boxes on table)
6. Click "💾 Save Config"
7. **Press F12** to hide main window again

**Mini overlay now shows**: "📸 Test OCR - Press Ctrl+T"

---

### Step 3: Test OCR (30 seconds) - ONE TIME ONLY

**Mini overlay shows**: "📸 Test OCR - Press Ctrl+T"

**You press**: **Ctrl+T**

**What happens**:
1. Bot captures screenshot in background
2. Runs OCR on poker table
3. Main window appears
4. Switches to Debug tab automatically
5. Shows OCR results (pot, stacks, cards)

**Check**:
- Pot: Should show actual pot amount
- Stacks: Should show 6 stack values
- Cards: May show '??' (normal)

**If correct**:
- Press **F12** to hide main window
- **Mini overlay now shows**: "✅ Ready - Press F9 for advice"

**If wrong**:
- Press **Ctrl+C** to recalibrate
- Try again

---

### Step 4: Play Poker (Every Session)

**Mini overlay shows**: "✅ Ready - Press F9 for advice"

**You**:
1. Open PokerStars (fullscreen)
2. Join play money table
3. Play normally

**When you need advice**:
- Press **F9**
- Mini overlay updates with AI decision
- Shows: "💡 CALL $20" (or FOLD/RAISE)
- Shows reasoning: "Strong hand, pot odds good"

**That's it!** No need to see main window.

---

## ⌨️ All Hotkeys

| Key | Action | When to Use |
|-----|--------|-------------|
| **Ctrl+C** | Open Calibration | First time setup |
| **Ctrl+T** | Test OCR | After calibration |
| **F9** | Capture & Analyze | Get AI advice anytime |
| **F12** | Show/Hide Main Window | Check logs, debug |
| **Ctrl+H** | Show/Hide Mini Overlay | Toggle overlay |
| **F10** | Start/Stop Bot | Auto mode only |
| **F11** | Emergency Stop | Stop bot immediately |

---

## 📱 Mini Overlay Guidance

The overlay **tells you what to do next**:

### Before Calibration:
```
┌─────────────────────────────┐
│ 🎰 OnyxPoker                │
│ ─────────────────────────── │
│ 📋 Setup Needed             │
│ Press Ctrl+C to calibrate   │
│ Or F12 to open main window  │
│ ─────────────────────────── │
│ Ctrl+C:Calibrate  F12:Main  │
└─────────────────────────────┘
```

### After Calibration:
```
┌─────────────────────────────┐
│ 🎰 OnyxPoker                │
│ ─────────────────────────── │
│ 📸 Test OCR                 │
│ Press Ctrl+T to test OCR    │
│ Or F9 to capture & analyze  │
│ ─────────────────────────── │
│ Ctrl+T:Test  F9:Analyze     │
└─────────────────────────────┘
```

### Ready to Play:
```
┌─────────────────────────────┐
│ 🎰 OnyxPoker                │
│ ─────────────────────────── │
│ ✅ Ready!                   │
│ Press F9 to get AI advice   │
│ Bot is ready to help!       │
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

## 🎮 Complete Example Session

### First Time (Setup):

```
You: python poker_gui.py
GUI: *Opens, shows overlay, auto-hides after 2 seconds*

Overlay: "📋 Setup Needed - Press Ctrl+C"

You: *Press Ctrl+C*
GUI: *Shows calibration tab*

You: *Scan Windows → Select → Auto-Detect → Save*
You: *Press F12 to hide*

Overlay: "📸 Test OCR - Press Ctrl+T"

You: *Press Ctrl+T*
GUI: *Captures, shows debug tab with OCR results*

You: *Check results, press F12 to hide*

Overlay: "✅ Ready - Press F9 for advice"
```

### Every Session After:

```
You: python poker_gui.py
GUI: *Opens, auto-hides after 2 seconds*

Overlay: "✅ Ready - Press F9 for advice"

You: *Open PokerStars, play poker*

--- New Hand ---
You: *Get dealt A♠ K♥*
You: *Press F9*

Overlay:
  Table: $150 pot
  Cards: A♠ K♥
  Stack: $500
  💡 RAISE $75
  Strong hand, good position

You: *Raise $75 manually*

--- Next Hand ---
You: *Get dealt 7♣ 2♦*
You: *Press F9*

Overlay:
  Table: $150 pot
  Cards: 7♣ 2♦
  Stack: $425
  💡 FOLD
  Weak hand, not worth playing

You: *Fold*
```

---

## 🎯 Key Points

1. **Main window auto-hides** after 2 seconds
2. **Mini overlay guides you** through setup
3. **All actions via hotkeys** - no window switching needed
4. **Calibration is one-time** - then just use F9
5. **Overlay always visible** - shows next step or decisions

---

## 🔧 Troubleshooting

### "Overlay shows 'Setup Needed' but I already calibrated"
**Solution**: 
- Press Ctrl+T to test OCR
- This will update status to "Ready"

### "Hotkeys don't work"
**Solution**:
- Run as administrator (Windows)
- Check Activity Log (F12 → Control Panel)

### "OCR shows $0 for everything"
**Solution**:
- Press Ctrl+C to recalibrate
- Make sure PokerStars table is visible
- Try different PokerStars theme

### "Want to see main window"
**Solution**:
- Press F12 anytime
- Check Activity Log, OCR results, etc.
- Press F12 again to hide

---

## 📊 Workflow Summary

```
Launch → Auto-Hide → Overlay Guides You

First Time:
  Ctrl+C → Calibrate → F12 to hide
  Ctrl+T → Test OCR → F12 to hide
  ✅ Ready!

Every Session:
  F9 → Get AI advice
  (Repeat as needed)

That's it!
```

---

**No more window switching! Everything via hotkeys + overlay guidance.** 🚀
