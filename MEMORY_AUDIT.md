# Memory Polling Logic Audit
**Date:** 2026-02-12  
**Status:** Complete review after Session 89 bugs

---

## ARCHITECTURE OVERVIEW

### Components
1. **memory_calibrator.py** - Memory reading (Windows process)
2. **helper_bar.py** - UI + polling loop (Tkinter main thread)

### Data Flow
```
F9 pressed
  ├─ Screenshot + scan_live() (2-4s) → {hero_cards, hand_id, buf_addr, container_addr}
  ├─ GPT V2 (5.5s) → {board, pot, opponents}
  ├─ Merge results → display
  └─ Start polling: _mem_poll_loop(buf_addr, hand_id)
       └─ Every 200ms: rescan_buffer(buf_addr, hand_id)
            ├─ Check container FIRST for new hand
            ├─ If hand changed: return {hand_id_changed=True, new_buf_addr}
            └─ Else: return current hand data
```

---

## CRITICAL VARIABLES

### helper_bar.py State
| Variable | Purpose | Updated When |
|----------|---------|--------------|
| `_mem_polling` | Boolean flag | F9 sets False, then True after display |
| `_mem_poll_generation` | Counter to invalidate old polls | Incremented on each F9 |
| `_mem_hand_id` | Expected hand_id | F9 initial scan, poll detects change |
| `_mem_buf_addr` | Buffer address | F9 initial scan, poll detects change |
| `_mem_last_entries` | Entry count | Poll updates when actions added |
| `_last_result` | Cached F9 data | F9 stores full GPT result |
| `_last_mem_display` | Cached poll data | Poll stores for display |

### memory_calibrator.py State
| Variable | Purpose | Lifetime |
|----------|---------|----------|
| `_reader` | ProcessReader instance | Entire session |
| `_cached_container_addr` | Container address | Entire session (stable) |

---

## FUNCTION ANALYSIS

### 1. rescan_buffer(buf_addr, expected_hand_id)

**Purpose:** Re-read buffer in <1ms, detect hand changes

**Logic Flow:**
```python
1. Check if container moved to new hand (FIRST)
   - Read container's current hand_id
   - If container_hand_id != expected_hand_id:
     → Follow container to new buffer
     → Return {hand_id_changed=True, new_buf_addr, new_hand_data}

2. Container says same hand OR no container
   - Read buffer at buf_addr
   - Decode entries
   - Validate (check for corrupted names)
   - Return hand_data
```

**Edge Cases:**
- ✅ No container (dumps): Falls through to step 2
- ✅ Container not updated yet: Returns current hand data
- ✅ Buffer corrupted: Returns None → triggers full rescan
- ✅ Hand changed: Sets hand_id_changed=True

**Potential Issues:**
- ⚠️ What if container points to WRONG hand? (stale container)
  - **Mitigation:** Container is stable per table session (verified 25 dumps)
- ⚠️ What if decode_buffer fails?
  - **Mitigation:** Returns None → triggers full rescan after 10 retries

---

### 2. _mem_poll_loop(generation)

**Purpose:** Background thread polling every 200ms

**Logic Flow:**
```python
while _mem_polling and _mem_poll_generation == generation:
    1. hd = rescan_buffer(_mem_buf_addr, _mem_hand_id)
    
    2. If hd is None:
       - Retry 10 times (50ms each = 500ms total)
       - After 500ms: full rescan via scan_live()
       - Update _mem_hand_id, _mem_buf_addr
    
    3. If hd.get('hand_id_changed'):
       - Update _mem_hand_id = new_hand_id
       - Update _mem_buf_addr = new_buf_addr
       - Reset _mem_last_entries = 0
       - Log new hand
       - Update display immediately
    
    4. If entry_count changed OR hand changed:
       - Log new actions
       - Update _mem_last_entries
       - Update display
    
    5. Sleep 200ms
```

**Edge Cases:**
- ✅ F9 pressed during poll: generation mismatch → old poll exits
- ✅ Buffer lost: Retries then full rescan
- ✅ Hand changed: Updates tracking immediately
- ✅ No changes: Skips display update (no spam)

**Potential Issues:**
- ⚠️ What if hand changes DURING the 10 retries?
  - **Current:** After 500ms, does full rescan → finds new hand
  - **Better:** Check container during retries (already done in rescan_buffer)
- ⚠️ What if _update_mem_display queued before generation check?
  - **Fixed Session 89k:** Check generation BEFORE queuing

---

### 3. _update_mem_display(hd, entry_count, generation)

**Purpose:** Update right panel with poll data

**Logic Flow:**
```python
1. Check generation - if mismatch, return (stale update)

2. Extract data from hd (poll data, NOT cached F9 data):
   - Cards: hd.get('hero_cards')
   - Board: hd.get('community_cards')
   - Actions: hd.get('actions')
   - Players: hd.get('players')

3. Calculate pot/to_call from actions (via _reeval_with_memory)

4. Calculate position from players dict + actions

5. Display:
   - Header: cards | board | pot | to_call | position | num_players
   - Advice: action + reasoning + hand strength
   - Opponents: from cached F9 data (_last_result)
   - Actions: last 8 from poll data
```

**Edge Cases:**
- ✅ No cards: Shows "??"
- ✅ No board: Shows "--"
- ✅ Stale data: Shows "STALE" tag
- ✅ Generation mismatch: Returns early (no update)

**Potential Issues:**
- ⚠️ What if _reeval_with_memory returns None?
  - **Current:** Shows "[Calculating...]"
  - **Better:** Fall back to cached F9 advice? (NO - poll data might be different)

---

### 4. _reeval_with_memory(hd)

**Purpose:** Re-run strategy engine with poll data

**Logic Flow:**
```python
1. Get cards:
   - First: hd.get('hero_cards') (current poll)
   - Fallback: _last_result['memory_cards'] (cached from F9)
   - Last resort: _last_result['hero_cards'] (GPT cards)

2. Parse actions to calculate:
   - pot (sum all amounts)
   - to_call (last_villain_bet - hero_street_total)
   - is_aggressor (who raised last on current street)
   - is_facing_raise (villain raised after hero acted)
   - hero_last_action (for check-raise detection)

3. Build table_data dict

4. Call strategy_engine.get_action(table_data)

5. Return decision dict with _mem_debug
```

**Edge Cases:**
- ✅ No cards: Returns None
- ✅ Preflop: board=[], pot from blinds
- ✅ Postflop: board from community_cards
- ✅ Check-raise: Detects via hero_acted + to_call > 0

**Potential Issues:**
- ⚠️ What if actions list is corrupted?
  - **Current:** Calculates pot=0.07 (default)
  - **Better:** Validate actions before parsing? (rescan_buffer already validates names)
- ⚠️ What if DEAL marker missing?
  - **Current:** current_street_start = 0 (treats all as current street)
  - **Impact:** Pot calculation includes previous streets → WRONG
  - **Fix needed:** Handle missing DEAL marker

---

## IDENTIFIED BUGS

### BUG 1: Missing DEAL marker handling ⚠️
**Location:** `_reeval_with_memory()` line 1015  
**Issue:** If DEAL marker missing, treats all actions as current street  
**Impact:** Pot calculation includes previous streets  
**Fix:** Default to last N actions if no DEAL found

### BUG 2: Container validation missing ⚠️
**Location:** `rescan_buffer()` line 1121  
**Issue:** Doesn't validate container hand_id is reasonable (200B-300B range)  
**Impact:** Could follow corrupted container to garbage  
**Fix:** Add hand_id range check

### BUG 3: No timeout on polling loop ⚠️
**Location:** `_mem_poll_loop()` line 697  
**Issue:** If hand never ends, polls forever  
**Impact:** Memory leak, CPU usage  
**Fix:** Add max_iterations or timeout

---

## RACE CONDITIONS

### RACE 1: F9 during poll ✅ FIXED
**Scenario:** User presses F9 while poll is running  
**Fix:** Generation counter + check before queuing UI updates

### RACE 2: Hand changes during retry ✅ HANDLED
**Scenario:** Hand changes during 10-retry loop  
**Fix:** rescan_buffer checks container first → detects new hand immediately

### RACE 3: Display update after F9 ✅ FIXED
**Scenario:** Poll queues display update, then F9 clears panel  
**Fix:** Poll starts AFTER _display_result completes

---

## RECOMMENDATIONS

### HIGH PRIORITY
1. ✅ **Check container FIRST** - Already implemented
2. ⚠️ **Handle missing DEAL marker** - Add fallback logic
3. ⚠️ **Validate container hand_id** - Add range check

### MEDIUM PRIORITY
4. ⚠️ **Add polling timeout** - Max 5 minutes per hand
5. ⚠️ **Better error recovery** - Log corrupted data for debugging
6. ⚠️ **Validate actions list** - Check for impossible sequences

### LOW PRIORITY
7. ✅ **Reduce logging spam** - Already minimal
8. ✅ **Cache position calculation** - Not needed (fast enough)

---

## TESTING CHECKLIST

### Scenario 1: Normal hand progression ✅
- [x] Poll detects new actions
- [x] Display updates live
- [x] Hand changes detected
- [x] New hand tracked correctly

### Scenario 2: F9 during poll ✅
- [x] Old poll exits cleanly
- [x] New poll starts
- [x] No stale updates

### Scenario 3: Buffer lost ⚠️ NEEDS TESTING
- [ ] Retries work
- [ ] Full rescan after 500ms
- [ ] Recovers correctly

### Scenario 4: Hand changes during retry ⚠️ NEEDS TESTING
- [ ] Container redirect works
- [ ] New hand detected immediately
- [ ] No stuck on old hand

### Scenario 5: Corrupted buffer ⚠️ NEEDS TESTING
- [ ] Validation catches it
- [ ] Returns None
- [ ] Full rescan triggered

---

## CONCLUSION

**Overall Assessment:** Logic is mostly sound, but has 3 bugs and needs testing on edge cases.

**Critical Path:** rescan_buffer → _mem_poll_loop → _update_mem_display → _reeval_with_memory

**Weakest Link:** Missing DEAL marker handling in _reeval_with_memory

**Next Steps:**
1. Fix missing DEAL marker bug
2. Add container hand_id validation
3. Test buffer lost scenario
4. Test hand change during retry
