# Live Play Issues Analysis - February 11, 2026

## Session Summary

**File:** `session_20260211_160941.jsonl`
- **Duration:** ~5 minutes (16:10 - 16:15)
- **F9 presses:** 9
- **Memory polls:** 37
- **Hands tracked:** 7 unique hand_ids
- **Hand changes detected:** 10 (buffer moved between hands)

---

## Critical Issues Found

### Issue #1: Cards Become NULL During Same Hand ❌

**Problem:** Memory cards become `null` mid-hand, even though hand_id hasn't changed.

**Evidence:**
```
Poll #2: hand 259683074477
  Previous: cards=KhJc
  Current:  cards=None, entry_count=13
  Actions: 5 entries
  NULL names: 5/5  ← ALL player names also NULL
```

**Root Cause:** When `extract_hand_data()` can't find hero's SEATED entry (type 0x02), it returns `None` for cards. This happens when:
1. Buffer is being reused/overwritten
2. String pointers become invalid (freed memory)
3. We're reading stale buffer data

**Impact:** UI shows old cards from F9, doesn't update with live data.

---

### Issue #2: UI Not Updating on Hand Change ❌

**Problem:** When `hand_id_changed: true`, the right panel doesn't show the NEW hand's cards.

**Evidence:**
```
Poll #3: NEW HAND 259683074477
  Cards: KhJc  ← This is the OLD hand's cards!
  Action: fold None
  Reasoning: KJo fold to 4-bet  ← OLD hand reasoning!
```

**Root Cause:** `_update_mem_display()` uses cards from `hand_data` (current poll), but `_reeval_with_memory()` falls back to `self._last_result` GPT cards when memory cards are None. The UI shows a mix of old and new data.

**Impact:** User sees wrong cards for the new hand until they press F9 again.

---

### Issue #3: Buffer Address Jumping ⚠️

**Observation:** Buffer address changes frequently, even within same hand_id:

```
Hand 259683074477:
  Poll #0: buf_addr=0x1a267f90
  Poll #3: buf_addr=0x1f293a10  ← Changed!
  Poll #5: buf_addr=0xf00f170   ← Changed again!
```

**This is NORMAL:** PokerStars allocates new buffers as the hand progresses. Our container-following logic works correctly.

**Not an issue**, but explains why we see multiple `hand_id_changed: true` for same hand_id.

---

## Root Cause Analysis

### Why Cards Become NULL

Looking at `memory_calibrator.py` `extract_hand_data()`:

```python
def extract_hand_data(entries):
    # Find hero's SEATED entry (type 0x02)
    for e in entries:
        if e['msg_type'] == 0x02 and e['name'] == HERO_NAME:
            hero_cards = e.get('extra')  # ASCII cards from extra_ptr
            break
    
    # If no SEATED entry found → hero_cards = None
    return {'hero_cards': hero_cards, ...}
```

**Problem:** When buffer is reused or string pointers are freed, `e['name']` becomes `None` (can't read string), so we never find hero's entry.

### Why UI Doesn't Update

Looking at `helper_bar.py` `_reeval_with_memory()`:

```python
def _reeval_with_memory(self, hd):
    # Get hero cards from memory, fall back to cached F9 cards
    mc = hd.get('hero_cards', '')
    lr = self._last_result or {}
    if mc and len(mc) == 4:
        cards = [mc[0:2], mc[2:4]]
    elif lr.get('memory_cards'):  # Use cached memory cards from initial scan
        mc = lr['memory_cards']
        cards = [mc[0:2], mc[2:4]]
    elif lr.get('hero_cards'):  # Last resort: F9 GPT cards
        cards = lr['hero_cards']  # ← WRONG! This is OLD hand's cards!
    else:
        return None
```

**Problem:** When new hand starts, `hd.get('hero_cards')` is None (can't read buffer), so we fall back to `lr.get('hero_cards')` which is the PREVIOUS hand's cards from F9.

---

## Solutions

### Solution #1: Stop Polling When Cards Become NULL

**Approach:** If we can't read cards, the buffer is invalid. Stop polling and wait for next F9.

```python
def _mem_poll_loop(self):
    while self._mem_polling:
        hd = rescan_buffer(self._mem_buf_addr, self._mem_hand_id)
        if hd is None:
            self._mem_polling = False
            break
        
        # NEW: Stop if cards become unreadable
        if not hd.get('hero_cards'):
            self._mem_polling = False
            self.root.after(0, lambda: self.log("[MEM] Cards unreadable, polling stopped", "DEBUG"))
            break
        
        # ... rest of polling logic
```

**Pros:** Simple, prevents showing wrong data
**Cons:** Polling stops mid-hand, user loses live updates

---

### Solution #2: Clear UI When Hand Changes

**Approach:** When `hand_id_changed: true`, clear the right panel and show "New hand - press F9".

```python
def _update_mem_display(self, hd, entry_count=0):
    # Check if this is a new hand
    if hd.get('hand_id_changed'):
        # Clear panel and prompt for F9
        self.stats_text.delete('1.0', 'end')
        self.stats_text.insert('end', "[NEW HAND DETECTED]\n", 'MEM')
        self.stats_text.insert('end', "Press F9 for analysis\n", 'DRAW')
        self.time_label.config(text="NEW HAND")
        # Stop polling - wait for F9
        self._mem_polling = False
        return
    
    # ... rest of display logic
```

**Pros:** Clear indication to user, no wrong data shown
**Cons:** User must press F9 for every new hand

---

### Solution #3: Re-scan on Hand Change (BEST)

**Approach:** When `hand_id_changed: true`, call `scan_live()` to get fresh data for the new hand.

```python
def _mem_poll_loop(self):
    from memory_calibrator import scan_live
    
    while self._mem_polling:
        hd = rescan_buffer(self._mem_buf_addr, self._mem_hand_id)
        if hd is None:
            self._mem_polling = False
            break
        
        # NEW: Re-scan when hand changes
        if hd.get('hand_id_changed'):
            new_hand_id = hd.get('hand_id')
            self.root.after(0, lambda h=new_hand_id: 
                self.log(f"[MEM] New hand {h}, re-scanning...", "INFO"))
            
            # Full scan to get fresh cards
            fresh_data = scan_live()
            if fresh_data and fresh_data.get('hero_cards'):
                # Update tracking
                self._mem_hand_id = fresh_data['hand_id']
                self._mem_buf_addr = fresh_data['buf_addr']
                self._mem_last_entries = 0
                # Update display with fresh data
                self.root.after(0, lambda d=fresh_data: self._update_mem_display(d, d.get('entry_count', 0)))
                time.sleep(0.2)
                continue
            else:
                # Scan failed - stop polling
                self._mem_polling = False
                self.root.after(0, lambda: self.log("[MEM] Re-scan failed, polling stopped", "ERROR"))
                break
        
        # ... rest of polling logic
```

**Pros:** 
- Automatic updates for new hands
- No user action required
- Always shows correct cards

**Cons:**
- Re-scan takes 2-4s (but only once per hand)
- More CPU/memory usage

---

### Solution #4: Hybrid Approach (RECOMMENDED)

**Combine #1 and #3:**

1. When `hand_id_changed: true` → re-scan
2. If re-scan fails OR cards become NULL → stop polling and show "Press F9"
3. User presses F9 → fresh scan + polling restarts

```python
def _mem_poll_loop(self):
    from memory_calibrator import scan_live
    
    while self._mem_polling:
        hd = rescan_buffer(self._mem_buf_addr, self._mem_hand_id)
        
        # Buffer lost
        if hd is None:
            self._mem_polling = False
            self.root.after(0, lambda: self.log("[MEM] Buffer lost", "DEBUG"))
            break
        
        # Cards unreadable (buffer corrupted)
        if not hd.get('hero_cards'):
            self._mem_polling = False
            self.root.after(0, lambda: self.log("[MEM] Cards unreadable, press F9", "INFO"))
            # Show prompt in UI
            self.root.after(0, lambda: self._show_f9_prompt())
            break
        
        # New hand detected
        if hd.get('hand_id_changed'):
            new_hand_id = hd.get('hand_id')
            self.root.after(0, lambda h=new_hand_id: 
                self.log(f"[MEM] New hand {h}, re-scanning...", "INFO"))
            
            # Try full scan
            fresh_data = scan_live()
            if fresh_data and fresh_data.get('hero_cards'):
                # Success - update tracking and continue
                self._mem_hand_id = fresh_data['hand_id']
                self._mem_buf_addr = fresh_data['buf_addr']
                self._mem_last_entries = 0
                self.root.after(0, lambda d=fresh_data: 
                    self._update_mem_display(d, d.get('entry_count', 0)))
                time.sleep(0.2)
                continue
            else:
                # Re-scan failed - stop and prompt
                self._mem_polling = False
                self.root.after(0, lambda: self.log("[MEM] Re-scan failed, press F9", "INFO"))
                self.root.after(0, lambda: self._show_f9_prompt())
                break
        
        # Normal update
        n = hd.get('entry_count', 0)
        if n != self._mem_last_entries:
            self._mem_last_entries = n
            self.root.after(0, lambda d=hd, cnt=n: self._update_mem_display(d, cnt))
        
        time.sleep(0.2)

def _show_f9_prompt(self):
    """Show 'Press F9' prompt in right panel."""
    self.stats_text.delete('1.0', 'end')
    self.stats_text.insert('end', "[NEW HAND]\n", 'MEM')
    self.stats_text.insert('end', "Press F9 for analysis\n", 'ACTION')
    self.time_label.config(text="READY")
```

**Pros:**
- Automatic for most hands (re-scan works)
- Graceful fallback when re-scan fails
- Clear user feedback
- No wrong data shown

**Cons:**
- Slightly more complex
- Re-scan adds 2-4s delay per hand

---

## Additional Improvements

### 1. Cache Last Known Good Cards

Store the last successfully read cards per hand_id:

```python
self._mem_card_cache = {}  # hand_id → cards

# In _mem_poll_loop:
if hd.get('hero_cards'):
    self._mem_card_cache[hd['hand_id']] = hd['hero_cards']
elif hd['hand_id'] in self._mem_card_cache:
    hd['hero_cards'] = self._mem_card_cache[hd['hand_id']]
```

### 2. Better Error Messages

Show specific errors in UI:
- "Buffer moved - re-scanning..."
- "Cards unreadable - press F9"
- "New hand detected - updating..."

### 3. Visual Indicator for Stale Data

Add timestamp to right panel:
```
[MEM] 8h 5d (2s ago)
```

If data is >5s old, show warning.

---

## Recommended Implementation Plan

1. **Implement Solution #4 (Hybrid)** - Best balance of automation and reliability
2. **Add card caching** - Reduce NULL card issues
3. **Improve error messages** - Better user feedback
4. **Add data freshness indicator** - Show when data is stale

**Estimated effort:** 2-3 hours
**Risk:** Low - fallback to F9 always works

---

## Questions for User

1. **How often do you want to press F9?**
   - Every hand (current behavior)
   - Only when polling fails (Solution #4)
   - Never (full automation, but may show wrong data briefly)

2. **Is 2-4s delay acceptable for automatic hand updates?**
   - Yes → Use Solution #3 or #4
   - No → Use Solution #2 (manual F9 every hand)

3. **What should UI show when cards are unreadable?**
   - Blank panel with "Press F9"
   - Last known cards with "STALE" warning
   - Error message only

---

## Next Steps

1. User answers questions above
2. Implement chosen solution
3. Test on live play
4. Iterate based on feedback
