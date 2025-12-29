# OnyxPoker Architecture

## Project Structure

```
onyxpoker/
├── client/                          # Windows GUI application
│   ├── poker_gui.py                 # Main GUI (3 tabs + overlay + hotkeys)
│   ├── poker_bot.py                 # Bot orchestrator
│   ├── poker_reader.py              # OCR screen reading
│   ├── automation_client.py         # HTTP client to server
│   ├── window_detector.py           # Auto-calibration with CV
│   ├── mini_overlay.py              # Always-on-top mini panel
│   ├── hotkey_manager.py            # Global hotkeys (F6-F12)
│   ├── system_tray.py               # System tray icon
│   ├── card_matcher.py              # Card template matching
│   ├── kiro_validator.py            # Kiro CLI validation
│   └── config.py                    # Screen regions (generated)
├── server/                          # Linux Flask API
│   ├── app.py                       # Flask API server
│   └── poker_strategy.py            # Kiro CLI integration
└── docs/                            # Documentation
```

## Component Responsibilities

### poker_gui.py (Main GUI)
**Purpose**: Unified control interface with 4 tabs

**Tabs**:
1. **Control Panel**: Bot controls, game state, decision display, activity log
2. **Calibration**: Window capture, auto-detection, preview, save config
3. **Debug**: Screenshot capture, OCR analysis, Kiro validation, game state JSON
4. **Help**: Setup guide, hotkeys reference, tips

**Key Methods**:
- `scan_windows()`: Captures active window (3-second countdown)
- `auto_detect()`: Takes screenshot, runs CV detection, shows preview
- `save_calibration()`: Writes config.py with detected regions
- `capture_debug()`: Takes screenshot for OCR testing
- `validate_with_kiro()`: Sends state to Kiro CLI for validation

**State Variables**:
- `selected_window`: Window info captured by F7/scan_windows
- `detected_elements`: CV detection results (buttons, pot)
- `last_state`: Most recent OCR parsed state
- `last_screenshot`: Most recent screenshot PIL image

### window_detector.py (Auto-Calibration)
**Purpose**: Computer vision for detecting poker table elements

**Key Methods**:
- `find_poker_windows()`: Lists all windows (not filtered)
- `capture_window(window_info)`: Takes screenshot of specific window
- `detect_poker_elements(img)`: CV detection of buttons/pot
- `create_preview(img, elements)`: Draws colored boxes on preview

**Detection Logic**:
- Buttons: Looks for rectangles at bottom 20% of screen
- Pot: Looks for text with digits in center-top area
- Returns confidence score (0.0-1.0)

### hotkey_manager.py (Global Hotkeys)
**Purpose**: Background hotkey handling

**Hotkeys**:
- **F6**: Toggle mini overlay visibility
- **F7**: Capture active window (stores window info)
- **F8**: Context-aware (auto-detect if not calibrated, test OCR if calibrated)
- **F9**: Capture screenshot + analyze with Kiro
- **F10**: Start/stop bot
- **F11**: Emergency stop
- **F12**: Show/hide main window

**F7 Flow**:
1. Gets currently active window with `gw.getActiveWindow()`
2. Stores window info in `parent.selected_window`
3. Logs window title, size, position
4. Updates overlay to "scan_done" state

**F8 Flow**:
1. Checks if `selected_window` exists
2. Checks if config.py has real calibration (not placeholder)
3. If not calibrated: calls `auto_detect()`
4. If calibrated: calls `capture_debug()` for OCR test

### mini_overlay.py (Always-On-Top Panel)
**Purpose**: Minimal info display during gameplay

**States**:
- `calibrate`: Shows "Setup Needed - Press F7"
- `scan_done`: Shows "Press F8 to capture"
- `test`: Shows "Press F8 to test OCR"
- `ready`: Shows "Press F9 for advice"
- `playing`: Shows game state + decision

### poker_reader.py (OCR)
**Purpose**: Read poker table using Tesseract OCR

**Reads**:
- Pot amount (from POT_REGION)
- Stack amounts (from STACK_REGIONS)
- Available actions (from BUTTON_REGIONS)
- Cards (placeholder '??' - not implemented)

### automation_client.py (HTTP Client)
**Purpose**: Communicate with Linux server

**Endpoints**:
- POST /analyze-poker: Send state, get decision
- POST /validate-state: Validate with Kiro CLI

## Data Flow

### Calibration Flow
```
User clicks poker window
  ↓
User presses F7 (or clicks "Capture Active Window")
  ↓
hotkey_manager.on_f7_capture_window()
  ↓
gw.getActiveWindow() → stores in parent.selected_window
  ↓
User presses F8
  ↓
hotkey_manager.on_f8_test_ocr()
  ↓
Checks: selected_window exists? config calibrated?
  ↓
Calls parent.auto_detect()
  ↓
poker_gui.auto_detect()
  ↓
detector.capture_window(selected_window) → PIL image
  ↓
detector.detect_poker_elements(img) → elements dict
  ↓
detector.create_preview(img, elements) → preview image
  ↓
Shows preview in Calibration tab canvas
  ↓
User clicks "Save Configuration"
  ↓
poker_gui.save_calibration()
  ↓
Writes config.py with TABLE_REGION, BUTTON_REGIONS, POT_REGION
```

### OCR Testing Flow
```
User presses F8 (after calibration)
  ↓
hotkey_manager.on_f8_test_ocr()
  ↓
Detects config is calibrated
  ↓
Calls parent.capture_debug()
  ↓
poker_gui.capture_debug()
  ↓
poker_reader.capture_screenshot() → base64 image
  ↓
poker_reader.parse_game_state() → state dict
  ↓
Updates Debug tab with OCR results
  ↓
Shows screenshot in Debug canvas
```

### Analysis Flow (F9)
```
User presses F9
  ↓
hotkey_manager.on_f9_capture()
  ↓
Calls parent.capture_debug()
  ↓
poker_reader.capture_screenshot() + parse_game_state()
  ↓
automation_client.analyze_poker(state, screenshot)
  ↓
HTTP POST to server /analyze-poker
  ↓
Server: poker_strategy.analyze_poker_state()
  ↓
Server: Kiro CLI subprocess
  ↓
Server: Returns decision JSON
  ↓
Client: Updates overlay with decision
```

## Configuration

### config.py (Generated)
**Created by**: `save_calibration()` after auto-detection

**Contains**:
- `TABLE_REGION`: (x, y, width, height) of poker window
- `BUTTON_REGIONS`: Dict with fold/call/raise coordinates
- `POT_REGION`: (x, y, w, h) where pot amount is displayed
- `HOLE_CARD_REGIONS`: Placeholder (not used yet)
- `STACK_REGIONS`: Placeholder (not used yet)

**Placeholder Detection**:
- `(0, 0, 0, 0)`: Empty/invalid
- `(100, 100, 800, 600)`: Default placeholder
- Any other values: Real calibration

## Current Issues

### Issue 1: Calibration Tab Instructions Outdated
**Problem**: Instructions say "Click 'Scan Windows'" but button says "Capture Active Window"

**Fix**: Update instructions to match actual workflow

### Issue 2: Screenshot Not Visible During Calibration
**Problem**: User can't see if screenshot was captured successfully

**Fix**: Show preview immediately after F8 capture, before detection

### Issue 3: Debug Tab vs Validation Confusion
**Problem**: Not clear what Debug tab is for vs validation

**Clarification**:
- **Debug Tab**: Manual testing - capture screenshot, see OCR results, validate with Kiro
- **Validation**: Automated check that OCR results make sense (via Kiro CLI)

### Issue 4: "Capture Active Window" Button Doesn't Work
**Problem**: Clicking button makes GUI active, not poker window

**Solution**: Use F7 hotkey instead (user focuses poker window first)

## Recommended Fixes

1. **Remove "Capture Active Window" button** - F7 only
2. **Update Calibration instructions** - Reflect F7/F8 workflow
3. **Show screenshot preview immediately** - Before CV detection
4. **Clarify Debug tab purpose** - Add description at top
5. **Add visual feedback** - Show when F7 captures window
6. **Simplify workflow** - Remove confusing 3-second countdown
