# OnyxPoker - Comprehensive Project Audit

**Date**: December 30, 2025 02:17 UTC  
**Auditor**: Kiro AI Agent  
**Status**: CRITICAL ISSUES FOUND

---

## Executive Summary

**User Report**: "Project does not really work. Overlay not providing enough info, not being updated. Workflow doesn't work or works super slowly. Not enough debug info. Calibration screenshot looks small, weird, incomplete."

**Audit Findings**: Multiple critical issues identified across architecture, UX, and implementation.

---

## Critical Issues Found

### 🔴 ISSUE #1: Calibration Screenshot Shows Wrong Region

**Problem**: User says "calibration screenshot always looks small weird and incomplete"

**Root Cause**: `auto_detect()` method in poker_gui.py captures FULL SCREEN instead of just the poker window region.

**Code Location**: poker_gui.py line ~750
```python
def auto_detect(self):
    # WRONG: Captures full screen
    screenshot = pyautogui.screenshot()
    
    # Should be: Capture only the selected window region
    # screenshot = pyautogui.screenshot(region=(x, y, w, h))
```

**Impact**: 
- Preview shows entire screen (small, hard to see)
- Detection runs on wrong region
- User can't verify calibration quality
- Confidence scores meaningless

**Fix Required**: Capture only the selected window region, not full screen.

---

### 🔴 ISSUE #2: Overlay Not Showing Enough Info

**Problem**: Overlay shows minimal info, not updating properly

**Current Overlay Display**:
```
🎰 OnyxPoker
─────────────
Table: -- 
Cards: --
Stack: --
─────────────
💡 --
Waiting for action...
```

**Missing Critical Info**:
- No pot amount shown
- No board cards shown
- No opponent count
- No to_call amount
- No available actions
- No confidence score
- No timestamp

**Fix Required**: Add comprehensive game state display to overlay.

---

### 🔴 ISSUE #3: Workflow Too Slow

**Problem**: F9 takes 5-10 seconds with no progress feedback

**Current Flow**:
1. User presses F9
2. **NOTHING VISIBLE HAPPENS** (5-10 seconds)
3. Overlay updates with decision

**User Experience**: Feels broken, no feedback, unclear if working

**Fix Required**: 
- Show immediate "Analyzing..." message
- Show progress updates during GPT-4o call
- Show elapsed time
- Show what step is happening

---

### 🔴 ISSUE #4: Not Enough Debug Info

**Problem**: Logs don't show enough detail to diagnose issues

**Current Logs**:
```
💡 Getting advice...
🃏 Current Hand
Cards: ['As', 'Kh'], Pot: $150
💡 Recommended: RAISE $60
```

**Missing Debug Info**:
- No GPT-4o API call timing
- No screenshot capture confirmation
- No JSON response from GPT-4o
- No error details if API fails
- No confidence scores
- No button position detection
- No validation of detected values

**Fix Required**: Add comprehensive debug logging at every step.

---

### 🟡 ISSUE #5: Overlay Update Chain Fragile

**Problem**: Multiple places try to update overlay, inconsistent

**Current Code**:
- poker_gui.py calls `overlay.update_game_state()`
- hotkey_manager.py calls `overlay.update_status()`
- Different methods, different parameters
- Easy to miss updates

**Fix Required**: Single unified update method, called from one place.

---

### 🟡 ISSUE #6: No Error Recovery

**Problem**: If GPT-4o fails, user sees nothing

**Current Behavior**:
- API timeout → silent failure
- Invalid JSON → crash
- No API key → crash on startup
- Rate limit → no feedback

**Fix Required**: Graceful error handling with user-friendly messages.

---

### 🟡 ISSUE #7: Calibration Workflow Confusing

**Problem**: User must remember F12 → F8 sequence

**Current Workflow**:
1. Click "Scan Windows" (3 second countdown)
2. Select window
3. Press F12 (hide main window)
4. Press F8 (capture & detect)
5. Review preview
6. Save

**Issues**:
- Too many steps
- Easy to forget F12
- Countdown is annoying
- Preview shows wrong region (Issue #1)

**Fix Required**: Simplify to 2 steps: Click window → F8 → Save.

---

## Architecture Issues

### Issue A: GPT-4o Called Twice for Same Screenshot

**Problem**: Inefficient API usage

**Current Flow**:
1. F9 pressed
2. `parse_game_state(include_decision=True)` → GPT-4o call #1
3. Result displayed
4. (If bot mode) `get_decision()` → GPT-4o call #2

**Cost**: 2x API calls = 2x cost = 2x latency

**Fix**: Use `include_decision=True` always, cache result.

---

### Issue B: Config.py Has Unused Fields

**Problem**: Generated config has button regions GPT-4o doesn't need

**Current config.py**:
```python
TABLE_REGION = (150, 75, 1280, 720)  # NEEDED
BUTTON_REGIONS = {...}  # NOT NEEDED (GPT-4o detects)
POT_REGION = (...)  # NOT NEEDED
STACK_REGIONS = [...]  # NOT NEEDED
```

**Impact**: Confusing, looks like OCR is still used

**Fix**: Only save TABLE_REGION, remove rest.

---

### Issue C: No Validation of GPT-4o Results

**Problem**: Blindly trust GPT-4o output

**Current Code**:
```python
result = self.vision.detect_poker_elements(temp_path)
# No validation!
state = {
    'pot': result.get('pot', 0),  # Could be None, negative, huge
    'hero_cards': result.get('hero_cards', ['??', '??']),  # Could be invalid
}
```

**Risks**:
- Pot could be None → crash
- Cards could be invalid format
- Button positions could be off-screen
- Confidence could be low but still used

**Fix**: Validate all GPT-4o outputs before using.

---

## UX Issues

### UX Issue 1: No Visual Feedback on Hotkeys

**Problem**: Press F9, nothing happens for 5-10 seconds

**User Thinks**: "Did it work? Is it frozen? Should I press again?"

**Fix**: Immediate visual feedback on ALL hotkeys.

---

### UX Issue 2: Overlay Too Small

**Problem**: 320x260 overlay is tiny, hard to read

**Current Size**: 320x260 pixels  
**Font Sizes**: 7-14pt  
**Readability**: Poor on high-DPI screens

**Fix**: Larger overlay (400x350), bigger fonts.

---

### UX Issue 3: No Confidence Indicator

**Problem**: User doesn't know if detection is reliable

**Current**: No confidence shown anywhere  
**GPT-4o**: Returns confidence ~0.95  
**User**: Blind trust

**Fix**: Show confidence score in overlay and GUI.

---

### UX Issue 4: No Timestamp

**Problem**: Can't tell if overlay is stale

**Current**: No timestamp on decisions  
**User**: "Is this from 5 minutes ago?"

**Fix**: Show timestamp on every decision.

---

## Performance Issues

### Perf Issue 1: Full Screen Screenshot

**Problem**: Capturing full screen is slow and wasteful

**Current**: `pyautogui.screenshot()` → 1920x1080 or larger  
**Needed**: Only poker window region → 1280x720

**Impact**: 
- Slower capture (2-3x)
- Larger file to encode
- Slower GPT-4o processing
- Higher API cost

**Fix**: Always capture only TABLE_REGION.

---

### Perf Issue 2: No Caching

**Problem**: Same screenshot analyzed multiple times

**Scenario**: User presses F9 twice on same hand  
**Current**: 2 GPT-4o calls  
**Should**: Cache result for 5 seconds

**Fix**: Cache GPT-4o results with timestamp.

---

### Perf Issue 3: Synchronous API Calls

**Problem**: GUI freezes during GPT-4o call

**Current**: Main thread blocks for 5-10 seconds  
**User**: Can't click anything, looks frozen

**Fix**: Use threading for all API calls.

---

## Code Quality Issues

### Code Issue 1: Inconsistent Error Handling

**Problem**: Some methods have try/catch, some don't

**Examples**:
- `auto_detect()`: Has try/catch
- `get_advice()`: Has try/catch
- `parse_game_state()`: No try/catch
- `detect_poker_elements()`: No try/catch

**Fix**: Consistent error handling everywhere.

---

### Code Issue 2: Magic Numbers

**Problem**: Hardcoded values everywhere

**Examples**:
```python
self.window.geometry("320x260")  # Why 320x260?
self.window.attributes('-alpha', 0.85)  # Why 0.85?
time.sleep(1)  # Why 1 second?
max_tokens=500  # Why 500?
```

**Fix**: Use named constants.

---

### Code Issue 3: No Type Hints

**Problem**: Hard to understand what functions expect/return

**Current**:
```python
def update_game_state(self, state, decision):
    # What is state? What is decision?
```

**Fix**: Add type hints everywhere.

---

## Recommended Fixes (Priority Order)

### Priority 1: CRITICAL (Must Fix Now)

**1. Fix Calibration Screenshot** (30 minutes)
- Capture only selected window region
- Show proper preview
- Verify detection quality

**2. Add Progress Feedback** (30 minutes)
- Immediate "Analyzing..." on F9
- Show elapsed time
- Show current step

**3. Enhance Overlay Display** (1 hour)
- Show pot, board, opponents
- Show confidence score
- Show timestamp
- Larger size, bigger fonts

**4. Add Comprehensive Debug Logging** (1 hour)
- Log every step with timing
- Log GPT-4o request/response
- Log validation results
- Log errors with full traceback

### Priority 2: HIGH (Fix This Week)

**5. Simplify Calibration Workflow** (2 hours)
- Remove countdown
- Auto-capture on window selection
- Single-step process

**6. Add Result Validation** (2 hours)
- Validate GPT-4o outputs
- Check ranges (pot > 0, cards valid)
- Warn on low confidence

**7. Add Error Recovery** (2 hours)
- Graceful API failure handling
- Retry logic
- User-friendly error messages

**8. Threading for API Calls** (2 hours)
- Non-blocking GPT-4o calls
- Progress updates during call
- Cancellable operations

### Priority 3: MEDIUM (Fix Next Week)

**9. Result Caching** (1 hour)
- Cache GPT-4o results
- 5-second TTL
- Avoid duplicate calls

**10. Code Quality** (3 hours)
- Add type hints
- Extract constants
- Consistent error handling

**11. UX Polish** (2 hours)
- Larger overlay
- Better fonts
- Confidence indicators
- Timestamps

---

## Testing Plan

### Test 1: Calibration
1. Open PokerStars
2. Press F8
3. Verify preview shows ONLY poker window
4. Verify detection boxes are accurate
5. Save and verify config.py

### Test 2: Advice Mode
1. Sit at table
2. Press F9
3. Verify immediate "Analyzing..." feedback
4. Verify overlay updates within 10 seconds
5. Verify decision makes sense
6. Verify reasoning is shown
7. Verify confidence score shown

### Test 3: Error Handling
1. Disconnect internet
2. Press F9
3. Verify graceful error message
4. Reconnect
5. Press F9
6. Verify recovery

### Test 4: Performance
1. Press F9
2. Measure time to first feedback (<1 second)
3. Measure time to decision (<10 seconds)
4. Verify GUI doesn't freeze

---

## Conclusion

**Current State**: Project has good architecture (GPT-4o vision) but poor UX and implementation issues.

**Main Problems**:
1. Calibration captures wrong region
2. No progress feedback
3. Overlay shows minimal info
4. Not enough debug logging
5. Workflow too slow/confusing

**Estimated Fix Time**: 
- Priority 1 (Critical): 3 hours
- Priority 2 (High): 8 hours
- Priority 3 (Medium): 6 hours
- **Total**: 17 hours to fully working bot

**Next Steps**:
1. Fix calibration screenshot (30 min)
2. Add progress feedback (30 min)
3. Enhance overlay (1 hour)
4. Add debug logging (1 hour)
5. Test on real table

---

**Audit Complete**: December 30, 2025 02:17 UTC
