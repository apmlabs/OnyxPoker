# Live Play Logic Audit

**Date:** 2026-02-12  
**Status:** Ready for live play

---

## What Runs During Live Play

### helper_bar.py (1712 lines)
**Purpose:** Main UI + live play orchestration

**Used in live play:**
- F9 hotkey → screenshot + GPT vision + memory scan + strategy
- F10 hotkey → bot mode (auto-play)
- F11 hotkey → emergency stop
- Memory polling (rescan_buffer every 200ms)
- UI display (left panel logs, right panel stats)
- Session logging to JSONL

**Key methods (live):**
- `_analyze_thread()` - F9 handler (385-676, 291 lines)
- `_mem_poll_loop()` - Memory polling (692-795, 103 lines)
- `_update_mem_display()` - Right panel updates (796-955, 159 lines)
- `_display_result()` - Show advice (1142-1371, 229 lines)
- `_bot_loop()` - Bot mode (1501-1593, 92 lines)

**Total live logic:** ~874 lines (51% of file)

**Dead code (not used in live play):**
- `_bot_get_window()` - unused (1486-1495, 9 lines)
- `_bot_take_screenshot()` - unused (1496-1500, 4 lines)
- Drag/resize handlers (1609-1681, 72 lines) - UI only
- `create_ui()` - UI setup (137-218, 81 lines)

**Why it's 1712 lines:**
- 874 lines live logic (51%)
- 166 lines UI/drag/resize (10%)
- 672 lines support (logging, formatting, helpers) (39%)

---

## What Runs During Memory Operations

### memory_calibrator.py (1226 lines)
**Purpose:** Memory reading + offline analysis

**Used in live play (Windows only):**
1. `scan_live()` - Initial buffer scan (1019-1112, 93 lines)
2. `rescan_buffer()` - Fast re-read (1113-1158, 45 lines)
3. `save_dump()` - Optional dump save (315-353, 38 lines)
4. `tag_dump()` - Optional dump tagging (354-376, 22 lines)

**Total live logic:** ~198 lines (16% of file)

**NOT used in live play (offline analysis only):**
- `cmd_analyze()` - Verify dumps offline (875-995, 120 lines)
- `cmd_scan_pointers()` - Deep pointer analysis (793-874, 81 lines)
- `find_buffer_in_dump()` - Dump file analysis (514-585, 71 lines)
- `_analyze_container_structure()` - Research (623-650, 27 lines)
- `_deep_pointer_scan()` - Research (651-730, 79 lines)
- `_compare_pre_container_bytes()` - Research (731-792, 61 lines)
- Helper functions for dump analysis (409-513, 104 lines)

**Why it's 1226 lines:**
- 198 lines live logic (16%)
- 543 lines offline analysis (44%)
- 485 lines support/research (40%)

---

## What's NOT Used in Live Play

### cmd_pointer_scan.py (247 lines)
**Purpose:** Cheat Engine-style pointer chain scanner

**Status:** Research tool only, NEVER runs during live play

**Why it exists:**
- Session 84: Attempted to find static pointer chain (module → container)
- Session 88: Proved NO pointer chain exists
- Kept for documentation/research purposes

**Conclusion:** Can be deleted or moved to `/research` folder

---

## Memory Logic Flow (Live Play)

```
F9 pressed
  ├─ Screenshot (pyautogui)
  │
  ├─ [Windows] Start mem_thread:
  │     scan_live() (2-4s initial)
  │       ├─ Find PokerStars.exe process
  │       ├─ Scan for container (magic 0x0B0207EA, 150ms)
  │       ├─ Read buffer pointer from container+0xE4
  │       ├─ Decode 30 entries (hero cards, actions)
  │       └─ Return {cards, hand_id, players, actions, buf_addr}
  │
  ├─ GPT V2 vision (5.5s)
  │
  ├─ Merge: memory cards override GPT (ground truth)
  │
  ├─ Strategy engine → advice
  │
  └─ _display_result() → show advice
        └─ _start_mem_poll(buf_addr, hand_id)
              └─ rescan_buffer() every 200ms (<1ms)
                    ├─ Read 30 entries from known address
                    ├─ Check if hand_id changed (new hand)
                    ├─ If changed: follow container redirect
                    └─ Update right panel live
```

**Key insight:** Only 4 functions from memory_calibrator.py run during live play:
1. `scan_live()` - once per F9
2. `rescan_buffer()` - every 200ms during polling
3. `save_dump()` - optional (--calibrate flag)
4. `tag_dump()` - optional (--calibrate flag)

---

## Is There Double Logic?

**NO.** Checked all imports:

```bash
$ grep "from memory_calibrator import" helper_bar.py
430:    from memory_calibrator import scan_live
440:    from memory_calibrator import save_dump
564:    from memory_calibrator import tag_dump
622:    from memory_calibrator import tag_dump
694:    from memory_calibrator import rescan_buffer, scan_live
```

**Only 4 functions imported, all used correctly:**
- `scan_live()` - called once on F9 (Windows only)
- `rescan_buffer()` - called in polling loop (Windows only)
- `save_dump()` - called if --calibrate flag (optional)
- `tag_dump()` - called after GPT returns (optional)

**No duplicate memory reading logic in helper_bar.py.**

---

## Recommendations

### 1. Move Research Code (Optional)
Create `/research` folder and move:
- `cmd_pointer_scan.py` (247 lines) - never used in live play
- Memory analysis functions from `memory_calibrator.py`:
  - `cmd_analyze()`, `cmd_scan_pointers()`
  - `_deep_pointer_scan()`, `_compare_pre_container_bytes()`
  - `_analyze_container_structure()`

**Benefit:** Clearer separation of live vs research code  
**Risk:** None (these never run during live play)

### 2. Split helper_bar.py (Optional)
Extract into separate files:
- `bot_clicker.py` - bot mode logic (already exists but unused)
- `memory_poller.py` - memory polling loop
- `ui_components.py` - drag/resize handlers

**Benefit:** Smaller main file  
**Risk:** More imports, harder to trace flow

### 3. Keep As-Is (Recommended)
**Why:**
- No duplicate logic found
- Clear separation: live (16-51%) vs support/research (40-49%)
- All research code is in separate functions (easy to identify)
- File sizes reasonable for Python (1200-1700 lines)

---

## Summary

✅ **Live play logic is clean:**
- helper_bar.py: 874 lines live logic (51%)
- memory_calibrator.py: 198 lines live logic (16%)
- cmd_pointer_scan.py: 0 lines live logic (research only)

✅ **No double logic:**
- Only 4 memory functions imported
- All used correctly (scan once, poll repeatedly)

✅ **File sizes justified:**
- helper_bar.py: UI + orchestration + logging
- memory_calibrator.py: live reading + offline analysis
- cmd_pointer_scan.py: research tool (can be moved/deleted)

**Conclusion:** Code is ready for live play. File sizes are due to comprehensive logging, error handling, and offline analysis tools — not duplicate logic.
