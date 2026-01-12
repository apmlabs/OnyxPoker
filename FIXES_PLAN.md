# OnyxPoker Fixes Plan
**Date**: January 12, 2026  
**Status**: In Progress

## Critical Issues

### ✅ Issue 1: vision_detector_lite.py Wrong API
**Priority**: CRITICAL  
**File**: `client/vision_detector_lite.py`  
**Problem**: Using `responses.create()` for gpt-4o-mini (should be chat completions)  
**Impact**: Lite mode completely broken  
**Fix**: Switch to `chat.completions.create()` with proper response parsing  
**Status**: ✅ FIXED - Switched to chat completions API

### ✅ Issue 2: Opener Position Detection
**Priority**: HIGH  
**File**: `client/strategy_engine.py`  
**Problem**: Always assumes BTN opened, affects 3-bet ranges  
**Impact**: Wrong ranges vs UTG/MP opens  
**Fix**: Use conservative ranges when opener position unknown  
**Status**: ✅ FIXED - Now assumes MP (conservative)

### ✅ Issue 3: Multiway Pot Logic Missing
**Priority**: HIGH  
**File**: `client/poker_logic.py`  
**Problem**: No multiway adjustments (strategy files require them)  
**Impact**: Overbluffing multiway, not tightening enough  
**Fix**: Add `num_opponents` param, tighten c-betting multiway  
**Status**: ✅ FIXED - Added multiway logic to both postflop functions

### ⬜ Issue 4: Position Detection Simplified
**Priority**: MEDIUM  
**File**: `client/strategy_engine.py`  
**Problem**: `is_ip = position in ['BTN', 'CO']` ignores relative position  
**Impact**: MP plays same vs BB and vs BTN  
**Fix**: Need relative position or use conservative default  
**Status**: DEFERRED - Requires opponent position from vision detector

### ⬜ Issue 5: Stack Depth Adjustments Missing
**Priority**: MEDIUM  
**File**: `client/poker_logic.py`  
**Problem**: No stack depth logic (<50bb, >100bb adjustments)  
**Impact**: Suboptimal at non-standard stacks  
**Fix**: Add stack depth parameter and adjustments  
**Status**: DEFERRED - Requires stack size from vision detector

### ✅ Issue 6: test_raw_gpt.py Unused
**Priority**: LOW  
**File**: `client/test_raw_gpt.py`  
**Problem**: Orphaned test file  
**Fix**: Delete or move to tests/  
**Status**: ✅ FIXED - Deleted

## Implementation Order

1. ✅ **Issue 1** - Fix lite mode API (CRITICAL, breaks feature)
2. ✅ **Issue 3** - Add multiway pot logic (HIGH, strategy files require it)
3. ✅ **Issue 2** - Fix opener position (HIGH, affects ranges)
4. ⬜ **Issue 4** - Improve position detection (MEDIUM, deferred - needs vision data)
5. ⬜ **Issue 5** - Add stack depth (MEDIUM, deferred - needs vision data)
6. ✅ **Issue 6** - Clean up test file (LOW)

## Summary

**Completed**: 4/6 issues fixed  
**Deferred**: 2/6 issues (require additional data from vision detector)

### Changes Made

1. **vision_detector_lite.py**: Switched from `responses.create()` to `chat.completions.create()` for gpt-4o-mini
2. **poker_logic.py**: Added `num_opponents` parameter and multiway pot logic to both postflop functions
3. **strategy_engine.py**: Changed opener position assumption from BTN to MP (conservative)
4. **poker_sim.py**: Updated to pass `num_opponents` to postflop_action
5. **test_raw_gpt.py**: Deleted unused file

### Deferred Issues

**Issue 4 & 5** require additional data from vision detector:
- Opponent position (for relative position calculation)
- Stack sizes (for stack depth adjustments)

These can be added when vision detector provides this data.
