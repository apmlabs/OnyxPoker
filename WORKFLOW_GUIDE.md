# 🎯 Correct Workflow - Single Monitor Setup

## The Problem You Identified ✅

You're absolutely right! The current workflow is broken:
- Main window covers poker table
- Can't calibrate while window is open
- Can't take screenshots with window blocking table
- Need to constantly switch windows

## The Correct Workflow 🚀

### Phase 1: Initial Setup (One-Time, 5 minutes)

**Step 1: Position Everything**
```
1. Open PokerStars (play money table)
2. Position table on LEFT side of screen
3. Launch poker_gui.py
4. Main window opens on RIGHT side (or maximized)
5. Mini overlay appears (drag to corner)
```

**Step 2: Calibrate (With Main Window Visible)**
```
1. Keep BOTH windows visible side-by-side
2. Calibration tab → Scan Windows
3. Select PokerStars window
4. Click Auto-Detect Elements
5. Preview shows colored boxes on poker table
6. Click Save Config
7. Done! Now you can hide main window
```

**Step 3: Test OCR (With Main Window Visible)**
```
1. Still side-by-side
2. Debug tab → Capture Now
3. Check OCR results
4. If wrong, recalibrate
5. Once working, proceed to Phase 2
```

### Phase 2: Normal Play (Every Session)

**Step 1: Hide Main Window**
```
1. Press F12 to hide main window
2. PokerStars now has full screen
3. Mini overlay stays visible in corner
```

**Step 2: Play Poker**
```
1. Play normally
2. When you need advice: Press F9
3. Mini overlay updates with decision
4. You make the decision
```

**Step 3: Check Details (If Needed)**
```
1. Press F12 to show main window
2. Review Activity Log
3. Check OCR accuracy
4. Press F12 to hide again
```

---

## Current Hotkeys (Already Working!)

| Key | Action | Use Case |
|-----|--------|----------|
| **F9** | Capture & Analyze | Get AI advice (works with window hidden!) |
| **F10** | Start/Stop Bot | Toggle automation |
| **F11** | Emergency Stop | Stop + show main window |
| **F12** | Toggle Main Window | Show/hide for calibration/review |
| **Ctrl+H** | Toggle Mini Overlay | Show/hide mini panel |

---

## What's Already Solved ✅

1. **F9 works with window hidden** ✅
   - Takes screenshot in background
   - Analyzes game state
   - Updates mini overlay
   - No need to show main window!

2. **Mini overlay stays on top** ✅
   - Always visible
   - Shows decisions
   - Shows reasoning
   - Shows hotkey hints

3. **F12 toggles main window** ✅
   - Show for calibration/setup
   - Hide for playing
   - Window size persists

---

## What You Actually Need to Do

### First Time (Calibration):

```
┌─────────────────────────────────────────────────┐
│ 1. Open PokerStars (LEFT side)                 │
│ 2. Open poker_gui.py (RIGHT side)              │
│ 3. Keep BOTH visible side-by-side              │
│ 4. Calibrate (Calibration tab)                 │
│ 5. Test OCR (Debug tab)                        │
│ 6. Once working: Press F12 to hide main window │
└─────────────────────────────────────────────────┘
```

### Every Session After:

```
┌─────────────────────────────────────────────────┐
│ 1. Open PokerStars (fullscreen)                │
│ 2. Open poker_gui.py (auto-hides after launch) │
│ 3. Mini overlay visible in corner              │
│ 4. Press F9 when you need advice                │
│ 5. Press F12 if you need to see main window    │
└─────────────────────────────────────────────────┘
```

---

## Improved Workflow (What We Can Add)

### Option 1: Auto-Hide Main Window on Launch
```python
# After initialization, auto-hide main window
self.root.after(2000, self.root.withdraw)  # Hide after 2 seconds
```

### Option 2: Calibration Mode in Overlay
```
Mini overlay shows:
"📋 Next: Calibrate (F12 to open)"
"📸 Next: Test OCR (F9 to capture)"
"✅ Ready! Press F9 for advice"
```

### Option 3: Calibration Hotkey
```
Ctrl+C = Open calibration wizard
Ctrl+T = Test OCR
```

---

## What Do You Want?

**Option A: Keep Current (Simplest)** ✅
- Calibrate with windows side-by-side (one-time)
- Then use F9/F12 for everything
- Mini overlay shows decisions
- **Advantage**: Already works, no changes needed

**Option B: Add Auto-Hide** 
- Main window auto-hides after 2 seconds
- Mini overlay shows "Press F12 to calibrate"
- **Advantage**: Less manual hiding

**Option C: Add Calibration Hotkeys**
- Ctrl+C opens calibration wizard
- Ctrl+T tests OCR
- **Advantage**: Can calibrate without F12

**Option D: Add Next Step to Overlay**
- Mini overlay shows current status
- "📋 Not calibrated - Press F12"
- "📸 Calibrated - Press F9 to test"
- "✅ Ready - Press F9 for advice"
- **Advantage**: Always know what to do next

---

## My Recommendation

**For now**: Use Option A (current workflow)
- It already works
- Calibration is one-time
- F9 works perfectly with window hidden
- Mini overlay shows everything you need

**If you want improvements**: Option D (next step in overlay)
- Shows what to do next
- Guides you through setup
- Minimal code changes

---

## Tell Me:

1. **Does Option A work for you?** (side-by-side for calibration, then hide)
2. **Do you want Option D?** (next step guidance in overlay)
3. **Something else?**

The key insight: **You only need main window visible during initial calibration (one-time). After that, F9 + mini overlay is all you need!**
