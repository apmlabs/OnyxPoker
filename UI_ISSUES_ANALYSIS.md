# UI Display Issues - February 11, 2026

## User Feedback

**Problem:** Right panel doesn't show which cards/table it's analyzing. Can't verify if advice is correct. Updates are inconsistent.

**Left panel:** Practically useless except for F9 presses. Doesn't show what's happening, how we did, what we're reading, advice and why.

---

## Root Cause Analysis

### Issue #1: Right Panel Missing Context ❌

**What user sees:**
```
=> RAISE 0.30
J7o in BTN open range

TOP PAIR (good K)
```

**What's missing:**
- ❌ Which cards (7d Jc)
- ❌ Which board (empty or Jh 3s 5c)
- ❌ Which hand_id (259683402163)
- ❌ Pot size (€0.07)
- ❌ To call amount (€0.12)
- ❌ Position (BB)

**Why:** `_update_mem_display()` only shows action/reasoning, not the context.

---

### Issue #2: Left Panel Too Verbose ❌

**What user sees:**
```
[16:43:53] DEBUG: Window: Asterope #3 - No Limit Hold'em...
[16:43:53] DEBUG: Saved: 20260211_164353.png
[16:43:54] DEBUG: V2 API call (gpt-5.2)...
[16:43:59] INFO: [MEM] Cards override: GPT ['Jc', '7d'] -> MEM ['7d', 'Jc']
[16:43:59] DEBUG: [MEM] Position: BB
[16:43:59] INFO: [MEM] 7dJc hand=259683402163 (2.05s)
[16:43:59] DEBUG: API done: 5.1s
```

**What's missing:**
- ❌ Clear hand summary (cards + board + pot)
- ❌ What action was taken
- ❌ Why that action
- ❌ Result (win/lose/fold)

**Why:** Logs are DEBUG-level technical info, not user-friendly summaries.

---

### Issue #3: Memory Polls Don't Show in UI ❌

**What happens:**
- Memory polls every 200ms
- Updates logged to session file
- **But UI doesn't update!**

**Why:** `_update_mem_display()` is called, but user can't see the updates clearly.

---

### Issue #4: No Opponent Info Displayed ❌

**Data available:**
```json
"opponent_stats": []  // Always empty!
```

**Why:** `_lookup_opponent_stats()` returns empty list because player names don't match database.

---

## What Data Is Available

### F9 Entry (Initial Analysis)
```python
{
    'hero_cards': ['7d', 'Jc'],
    'memory_cards': '7dJc',
    'board': [],
    'memory_community': None,
    'hand_id': 259683402163,
    'pot': 0.07,
    'to_call': 0,
    'position': 'BB',
    'action': 'raise',
    'amount': 0.3,
    'reasoning': 'J7o in BTN open range',
    'opponents': [{'name': 'RiCorreia94', 'has_cards': True}, ...],
    'opponent_stats': []  // Empty!
}
```

### Memory Poll Entry (Live Update)
```python
{
    'memory_cards': '7dJc',
    'memory_community': [],
    'memory_actions': [
        ['RiCorreia94', 'POST_SB', 2],
        ['chininche', 'POST_BB', 5],
        ...
    ],
    'action': 'check',
    'bet_size': None,
    'reasoning': 'BB checks',
    'debug': {
        'pot': 0.07,
        'to_call': 0.0,
        'is_aggressor': False,
        'num_players': 1
    }
}
```

---

## Proposed Fixes

### Fix #1: Add Context Header to Right Panel ✅

**Show at top:**
```
[HAND 259683402163]
7d Jc | Board: -- | Pot: €0.07 | To call: €0.00
Position: BB | Players: 4

=> RAISE 0.30
J7o in BTN open range
```

**Implementation:**
```python
def _update_mem_display(self, hd, entry_count=0):
    # ... existing code ...
    
    # NEW: Context header
    mc = hd.get('hero_cards', '')
    if mc and len(mc) == 4:
        cards_str = f"{mc[0:2]} {mc[2:4]}"
    else:
        cards_str = "??"
    
    cc = hd.get('community_cards', [])
    board_str = ' '.join(cc) if cc else '--'
    
    # Get pot/to_call from debug or calculate
    debug = hd.get('_mem_debug', {})
    pot = debug.get('pot', 0)
    to_call = debug.get('to_call', 0)
    
    # Get position from last_result
    lr = self._last_result or {}
    position = lr.get('position', '?')
    num_players = debug.get('num_players', '?')
    hand_id = hd.get('hand_id', '?')
    
    # Display header
    self.stats_text.insert('end', f"[HAND {hand_id}]\n", 'MEMDATA')
    self.stats_text.insert('end', f"{cards_str} | Board: {board_str} | Pot: €{pot:.2f} | To call: €{to_call:.2f}\n", 'MEM')
    self.stats_text.insert('end', f"Position: {position} | Players: {num_players}\n\n", 'MEMDATA')
```

---

### Fix #2: Simplify Left Panel Logs ✅

**Show only:**
- F9 press with hand summary
- Memory updates with action
- Results (win/lose/fold)

**Remove:**
- DEBUG window/screenshot messages
- API timing details
- Technical memory details

**Implementation:**
```python
# In _analyze_thread, replace verbose logs with:
self.log(f"F9: {cards_str} | {board_str} | Pot €{pot}", "INFO")

# In _mem_poll_loop, add:
if n != self._mem_last_entries:
    self.log(f"[MEM] {cards_str} | {action_str}", "INFO")
```

---

### Fix #3: Show Memory Updates Clearly ✅

**Current:** Time label shows "LIVE (15)"
**Problem:** User doesn't know what changed

**Solution:** Log each significant update
```python
# When action count changes
if len(actions) > self._last_action_count:
    new_actions = actions[self._last_action_count:]
    for name, act, amt in new_actions:
        if act not in ('POST_SB', 'POST_BB'):
            self.log(f"[MEM] {name}: {act} €{amt/100:.2f}", "INFO")
```

---

### Fix #4: Fix Opponent Stats Lookup ✅

**Problem:** `opponent_stats` always empty

**Debug:**
```python
# Check why lookup fails
opponents = [{'name': 'RiCorreia94', ...}, ...]
stats = self._lookup_opponent_stats(opponents)
# Returns: []
```

**Likely cause:** Player names not in database or case mismatch

**Solution:** Add logging to see what's happening
```python
def _lookup_opponent_stats(self, opponents):
    stats = []
    for opp in opponents:
        name = opp.get('name')
        if name and name in self.player_stats:
            stats.append(self.player_stats[name])
        else:
            self.log(f"[DEBUG] Player {name} not in DB", "DEBUG")
    return stats
```

---

## Mockup: Improved UI

### Right Panel (After Fixes)
```
[HAND 259683402163]
7d Jc | Board: -- | Pot: €0.07 | To call: €0.00
Position: BB | Players: 4

=> RAISE 0.30
J7o in BTN open range

---
RiCorreia94 (UNKNOWN)
chininche (UNKNOWN)
Keesil (UNKNOWN)

---
RiCorreia94: POST_SB €0.02
chininche: POST_BB €0.05
Keesil: FOLD
idealistslp: RAISE €0.10

LIVE (13)
```

### Left Panel (After Fixes)
```
[16:43:53] F9: 7d Jc | -- | Pot €0.07
[16:43:59] => RAISE €0.30 (J7o in BTN open range)
[16:44:01] [MEM] New hand 259683404550
[16:44:01] [MEM] 2d Qc | -- | Pot €0.07
[16:44:03] [MEM] RiCorreia94: RAISE €0.10
[16:44:05] [MEM] chininche: CALL €0.10
[16:44:12] F9: 2d Qc | -- | Pot €0.19
[16:44:18] => FOLD (Q2o fold vs open)
```

---

## Implementation Plan

### Phase 1: Right Panel Context (HIGH PRIORITY)
1. Add context header with cards/board/pot/position
2. Show hand_id for verification
3. Keep existing action/reasoning display
4. Test on live play

### Phase 2: Left Panel Cleanup (MEDIUM PRIORITY)
1. Remove DEBUG logs from user view
2. Add hand summary on F9
3. Add action summary on memory updates
4. Keep technical logs in session file only

### Phase 3: Opponent Stats Fix (LOW PRIORITY)
1. Debug why lookup fails
2. Add case-insensitive matching
3. Add "not in DB" indicator
4. Update player database if needed

### Phase 4: Memory Update Visibility (MEDIUM PRIORITY)
1. Log each new action to left panel
2. Highlight significant events (raises, all-ins)
3. Show street changes clearly
4. Add result logging (win/lose/fold)

---

## Questions for User

1. **Right panel priority:** Which info is most important?
   - Cards + board + pot? (context)
   - Action + reasoning? (advice)
   - Opponent info? (stats)
   - Live actions? (history)

2. **Left panel:** What do you want to see?
   - Every memory update? (verbose)
   - Only significant actions? (filtered)
   - Just F9 summaries? (minimal)

3. **Verification:** How do you verify advice is correct?
   - Check cards match your hand?
   - Check pot matches table?
   - Check reasoning makes sense?
   - All of the above?

---

## Next Steps

1. User answers questions above
2. Implement Phase 1 (context header)
3. Test on live play
4. Iterate based on feedback
5. Implement remaining phases
