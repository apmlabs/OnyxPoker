# OnyxPoker - Pre-Flight Checklist

## Before Live Play

### 1. Memory System Status
- ✅ **Container scan**: 24-byte anchor at +0x6C (build-independent)
- ✅ **Buffer scan**: 0x88 signature fallback
- ✅ **Polling**: rescan_buffer() every 200ms (<1ms)
- ✅ **Auto-dump**: NO_BUFFER failures saved to memory_dumps/
- ✅ **Success rate**: 78% (7/9 in last session)

### 2. Memory Re-evaluation Logic (Fixed Session 88)
- ✅ **is_aggressor**: Tracks per-street (not just preflop)
- ✅ **is_facing_raise**: Checks if hero acted THEN villain raised
- ✅ **num_players**: Counts from memory actions
- ✅ **position**: Uses memory position
- ✅ **to_call**: Tracks per-street investment
- ✅ **pot**: Sums all actions (correct)
- ✅ **Error logging**: Shows traceback
- ✅ **Debug display**: Shows pot/call/agg/raise/players

### 3. Known Issues
- ⚠️ **Hero cards disappear**: SEATED entries pushed out after ~13 actions
  - **Mitigation**: Falls back to cached memory_cards from initial scan
- ⚠️ **NO_BUFFER failures**: 2/9 hands (22%)
  - **Mitigation**: Auto-saves dumps for offline analysis
  - **Action**: Review dumps to improve scan algorithm

### 4. Bot Mode Status
- ❓ **Button detection**: Not tested in Session 87
- ❓ **Click execution**: No bot_action entries in logs
- ❓ **Layout detection**: May need recalibration

### 5. Startup Validation
Run `python helper_bar.py` and check logs for:
```
[XX:XX:XX] INFO: OnyxPoker ready | F9=Advice F10=Bot F11=Stop F12=Hide
[XX:XX:XX] DEBUG: Memory: Windows detected, live scanning enabled
[XX:XX:XX] DEBUG: Strategy: the_lord
[XX:XX:XX] DEBUG: Vision: V2 (opponent detection)
```

### 6. Test Sequence
1. **F9 on first hand** → Check memory_status (CONFIRMED/OVERRIDE/NO_BUFFER)
2. **Wait for action** → Check right panel updates live
3. **Check left panel** → Should show `[MEM LIVE] (N) action → ADVICE`
4. **Check debug line** → Should show `Pot:X.XX Call:X.XX Agg:True/False ...`

### 7. If Memory Fails
- Check `memory_dumps/` for auto-saved dumps
- Run `python memory_calibrator.py list` to see tagged dumps
- Run `python memory_calibrator.py analyze` to verify structure
- Check logs for `[MEM] Error:` messages

### 8. Session Log Upload
After session, run:
```bash
python send_logs.py
```
Uploads to server: 54.80.204.92:5001

## Expected Behavior

### On F9 Press:
```
[04:08:27] INFO: F9: Analyzing...
[04:08:27] DEBUG: Window: Asterope - No Limit Hold'em €0.02/€0.05 ...
[04:08:27] DEBUG: Saved: 20260211_040827.png
[04:08:27] DEBUG: V2 API call (gpt-5.2)...
[04:08:36] DEBUG: [MEM] Position: SB
[04:08:36] INFO: [MEM] 9d7d hand=259678642588 (1.99s)
[04:08:36] DEBUG: API done: 5.0s
[04:08:36] INFO: Cards: 9d 7d | Board: 3s Ts 4d | Pot: $0.53 | To call: $0.10
[04:08:36] DECISION: => CALL
[04:08:36] DEBUG: high card - call high card flop (small) vs fish
[04:08:36] INFO: Win: 14% | Pot odds: 16%
[04:08:36] DEBUG: [MEM] Polling started
```

### During Polling:
```
[04:08:58] DEBUG: [MEM LIVE] (21) PutesyFabes: BET €0.10 → CALL
[04:09:00] DEBUG: [MEM LIVE] (22) idealistslp: FOLD → FOLD
[04:09:02] DEBUG: [MEM LIVE] (23) elrusogamer: FOLD → FOLD
```

### Right Panel Should Show:
```
=> CALL
high card - call high card flop (small) vs fish
HIGH CARD
Pot:0.55 Call:0.10 Agg:False Raise:False Players:4
---
PutesyFabes FISH - Isolate wide | Value bet | Calls too much | Never bluff
---
--- LIVE ---
--- FLOP 3s Ts 4d ---
idealistslp: CHECK
elrusogamer: CHECK
mochilo97: CHECK
PutesyFabes: BET €0.10
```

## Commit Status

**Last commit**: 3838f55 (Session 88)
- Fixed memory re-evaluation logic
- Added debug display
- Auto-save NO_BUFFER dumps

**Ready for live play**: YES (with monitoring)
**Bot mode ready**: NO (needs testing)
