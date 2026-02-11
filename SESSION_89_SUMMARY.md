# Session 89 Summary

## Root Cause Found

**The card cache was being populated with WRONG cards for NEW hands!**

### The Bug

When polling detected a hand change:
1. Old hand 259688152753 ends (cards=7s4c)
2. New hand 259688621248 starts
3. Polling: `rescan_buffer` sees hand_id changed
4. Follows container to get new buffer
5. **BUG**: Container briefly still points to OLD buffer!
6. Reads OLD buffer: hand_id=259688152753, cards=7s4c
7. **CATASTROPHIC**: Code saves `_card_cache[259688621248] = '7s4c'` (WRONG!)
8. F9 pressed: reads cache, gets wrong cards for new hand!

### The Fix (Session 89j)

When `rescan_buffer` follows the container to a "new" hand, **verify the hand_id actually changed:**

```python
if new_hid == expected_hand_id:
    # Container still points to old buffer - hand hasn't changed yet!
    return None  # Retry later
```

This prevents caching wrong cards with wrong hand_id.

## All Bugs Fixed in Session 89

1. ✅ Display using cached F9 data instead of live poll data (89c)
2. ✅ Polling stops when rescan fails (89b - added retry logic)
3. ✅ Action names null (89d - use players dict instead of freed pointers)
4. ✅ Street markers cluttering display (89e - removed)
5. ✅ Display not updating when hand changes (89f - added auto-update)
6. ✅ Polling not switching to new hand when F9 pressed (89h - always update tracking)
7. ✅ Race condition preventing new polling thread from starting (89i - set flag after starting thread)
8. ✅ **Card cache returning wrong hand's cards (89j - verify hand_id changed)**

## Test Instructions

```bash
git pull origin main
python helper_bar.py
```

**What should happen:**
1. Press F9 on first hand → shows correct cards
2. Play the hand (actions update live in right panel)
3. **New hand starts → cards automatically change to new hand's cards!**
4. No need to press F9 again (but you can)
5. **Cards should ALWAYS be correct for the current hand**

If cards are still wrong, upload new session log + dumps and I'll trace through exactly what's happening.
