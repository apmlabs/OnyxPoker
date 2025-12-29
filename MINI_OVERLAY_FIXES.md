# Mini Overlay & Hotkeys - Fixes Applied

**Date**: December 29, 2025 15:45 UTC  
**Status**: ✅ All Issues Fixed

---

## 🐛 Issues Reported

1. **Mini overlay can't reopen after closing**
2. **No hotkey info in UI**
3. **No hotkey info in tray menu**
4. **Overlay needs to be more transparent**
5. **Overlay has window decorations (title bar, buttons)**
6. **Need hotkey to toggle overlay**

---

## ✅ Fixes Applied

### 1. Mini Overlay Window Decorations
**Before**: Had title bar with close/minimize buttons  
**After**: Borderless window (no decorations)

**Change**: `self.window.overrideredirect(True)`

### 2. Transparency
**Before**: 95% opacity (barely transparent)  
**After**: 85% opacity (more transparent)

**Change**: `self.window.attributes('-alpha', 0.85)`

### 3. Close Behavior
**Before**: Closing destroyed the window, couldn't reopen  
**After**: Closing toggles visibility (hide/show)

**Changes**:
- Added `visible` state tracking
- Added `toggle_visibility()` method
- Intercept close event: `self.window.protocol("WM_DELETE_WINDOW", self.toggle_visibility)`

### 4. Toggle Hotkey
**Before**: No hotkey to toggle overlay  
**After**: Ctrl+H toggles overlay visibility

**Changes**:
- Added `keyboard.add_hotkey('ctrl+h', self.on_ctrl_h_toggle_overlay)`
- Added handler in `hotkey_manager.py`

### 5. Hotkey Info in GUI
**Before**: No hotkey info visible in main window  
**After**: Hotkeys panel in Control tab

**Changes**:
- Added "⌨️ Global Hotkeys" panel
- Shows all 5 hotkeys with descriptions
- Visible immediately when GUI opens

### 6. Hotkey Info in Tray Menu
**Before**: Menu items had no hotkey labels  
**After**: All menu items show hotkeys

**Changes**:
- "Show Main Window (F12)"
- "Toggle Mini Overlay (Ctrl+H)"
- "Start Bot (F10)"
- "Stop Bot (F10)"
- "Capture & Analyze (F9)"
- "Emergency Stop (F11)"
- Added "Hotkeys Help" option with full dialog

### 7. Improved Hotkey Logging
**Before**: Single line log message  
**After**: Multi-line, clear format

**Output**:
```
✅ Hotkeys registered:
   F9 = Capture & Analyze
   F10 = Start/Stop Bot
   F11 = Emergency Stop
   F12 = Toggle Main Window
   Ctrl+H = Toggle Mini Overlay
```

---

## 📊 Summary of Changes

### Files Modified (4)
1. **client/mini_overlay.py**
   - Remove window decorations
   - Increase transparency
   - Add toggle visibility
   - Add more hotkey hints

2. **client/hotkey_manager.py**
   - Add Ctrl+H hotkey
   - Improve logging format
   - Add toggle overlay handler

3. **client/poker_gui.py**
   - Add hotkeys info panel in Control tab

4. **client/system_tray.py**
   - Add hotkey labels to menu items
   - Add toggle overlay option
   - Add capture, emergency stop options
   - Add hotkeys help dialog

### Documentation Updated (1)
1. **HOTKEYS_GUIDE.md**
   - Update features list
   - Add Ctrl+H to reference table
   - Update tray menu section
   - Update troubleshooting

---

## 🎯 How to Use

### Pull Latest Code
```bash
cd /c/AWS/onyx-client
git pull origin main
```

### Launch GUI
```bash
cd client
python poker_gui.py
```

### Test Features
1. **Mini Overlay**: Should appear with no title bar, more transparent
2. **Ctrl+H**: Press to hide/show overlay
3. **Control Tab**: See hotkeys info panel
4. **System Tray**: Right-click to see hotkey labels
5. **Hotkeys Help**: Tray menu → Hotkeys Help

---

## ✅ All Issues Resolved

- [x] Mini overlay can reopen after closing (Ctrl+H)
- [x] Hotkey info visible in GUI (Control tab)
- [x] Hotkey info visible in tray menu (labels + help)
- [x] Overlay more transparent (85% opacity)
- [x] No window decorations (borderless)
- [x] Hotkey to toggle overlay (Ctrl+H)

---

**Status**: Ready to test! 🚀
