# OnyxPoker - Agent Context

## 🎉 MILESTONE: SESSION 40 - First Winning Live Session 🎉

**141 hands played** at 2NL with value_maniac strategy. Overbets with pairs getting paid consistently. This validates the entire approach.

### ⚠️ GOLD MODEL - DO NOT MODIFY ⚠️
```
Git Tag:    v1.0-gold
Commit:     9349026
Date:       January 14, 2026
Strategy:   value_maniac
Results:    141 hands, profitable session
```
**To revert**: `git checkout v1.0-gold`
**To compare**: Always benchmark new strategies against this version.

---

## 🎯 PROJECT GOAL

**AI-powered poker analysis tool for research purposes** - NOT for automated botting.

The system analyzes poker tables using GPT vision API and provides strategic advice. The human makes all decisions and clicks. This is a research tool for studying AI decision-making in poker.

---

## 📚 DOCUMENTATION STRUCTURE

### Core Files (NEVER DELETE)
- **AGENTS.md** (this file) - Permanent knowledge, architecture, lessons learned
- **AmazonQ.md** - Current status, session history, progress tracking
- **README.md** - User-facing quick start guide

### Technical Documentation
- **docs/DEPLOYMENT.md** - Setup and deployment guide

---

## 🏗️ ARCHITECTURE

### Full Call Chain (verified Session 83)
```
F9 pressed (helper_bar.py)
  │
  ├─ Stop previous memory polling (_mem_polling = False)
  ├─ Screenshot active window (pyautogui)
  │
  ├─ [Windows] Start mem_thread: scan_live() → hero_cards, hand_id, players, actions, buf_addr (2-4s)
  │
  ├─ VisionDetectorV2.detect_table()        → GPT-5.2 reads cards/pot/opponents (~5.5s)
  │
  ├─ [Windows] Merge memory results: cards override GPT, fill hand_id, player names
  ├─ [Windows] Save _pending_mem_poll = (buf_addr, hand_id)
  │
  ├─ _merge_opponents()                     → Tracks real names across screenshots
  ├─ _lookup_opponent_stats()               → Looks up archetypes from player_stats.json
  │                                           Returns: [{name, archetype, advice}, ...]
  │
  ├─ StrategyEngine('the_lord').get_action(table_data)
  │     │
  │     ├─ PREFLOP (no community cards):
  │     │     loop all 6 positions with to_call=0
  │     │     └─ preflop_action()            ← poker_logic/preflop.py
  │     │          Uses STRATEGIES dict + THE_LORD_VS_RAISE for opponent-aware ranges
  │     │
  │     └─ POSTFLOP (community cards present):
  │           ├─ _get_villain_archetype()     → picks tightest active opponent
  │           └─ postflop_action()            ← poker_logic/_monolith.py (dispatcher)
  │                 │
  │                 ├─ analyze_hand()         ← poker_logic/hand_analysis.py
  │                 ├─ check_draws()          ← poker_logic/hand_analysis.py
  │                 │
  │                 └─ strategy == 'the_lord'?
  │                       → _postflop_the_lord()   ← poker_logic/postflop_the_lord.py
  │                            └─ wraps _postflop_value_lord() ← poker_logic/postflop_value_lord.py
  │                                 + opponent-aware adjustments by archetype
  │
  └─ _display_result() → updates right panel with advice + stats
        └─ [Windows] Start _mem_poll_loop from _pending_mem_poll
              └─ rescan_buffer() every 200ms (<1ms each)
              └─ _update_mem_display() → right panel updates live
              └─ Falls back to GPT cards if memory_cards is None
              └─ Time label shows LIVE (N) during polling
```

**Key files in the chain:**
| Step | File | Function |
|------|------|----------|
| Memory scan | memory_calibrator.py | scan_live() (2-4s initial), rescan_buffer() (<1ms poll) |
| Memory poll | helper_bar.py | _mem_poll_loop(), _update_mem_display() |
| Vision | vision_detector_v2.py | detect_table() |
| Opponent DB | helper_bar.py | _lookup_opponent_stats() → player_stats.json |
| Router | strategy_engine.py | get_action() → preflop or postflop path |
| Preflop | poker_logic/preflop.py | preflop_action() |
| Postflop dispatch | poker_logic/_monolith.py | postflop_action() |
| Hand eval | poker_logic/hand_analysis.py | analyze_hand(), check_draws() |
| the_lord | poker_logic/postflop_the_lord.py | _postflop_the_lord() |
| value_lord | poker_logic/postflop_value_lord.py | _postflop_value_lord() |
| Inactive | poker_logic/postflop_inactive.py | optimal_stats/value_max/gpt/sonnet_max |
| Config-driven | poker_logic/postflop_base.py | kiro/kiro_lord/sonnet |
| Constants | poker_logic/card_utils.py | RANKS, SUITS, parse_card, equity |

### V2 Vision Mode (Default since Session 60)
```bash
python helper_bar.py          # V2 default (~5.5s)
python helper_bar.py --v1     # V1 mode (~3.9s, no player detection)
```
- Detects player names from screenshots
- Tracks opponents across screenshots (handles action words like "Fold", "Call €0.10")
- Looks up stats from player_stats.json
- Classifies archetypes (fish/nit/lag/tag/maniac/rock)
- Shows actionable advice per opponent in sidebar

### Opponent Tracking (Session 61)
When a player acts, PokerStars shows their action instead of name. V2 handles this:
```python
# Action words filtered out, real names kept from previous screenshots
ACTION_WORDS = ['fold', 'check', 'call', 'raise', 'bet', 'all-in', 'post', ...]

# _merge_opponents() keeps real names across F9 presses
# num_players calculated from opponents with has_cards=True
```

### Test Screenshots
```bash
python test_screenshots.py              # V1 vs V2 comparison (default)
python test_screenshots.py --compare 20 # Compare 20 screenshots
python test_screenshots.py --track 10   # Test opponent tracking
python test_screenshots.py --v1         # V1 only
python test_screenshots.py --v2         # V2 only
```

### Player Database Architecture
**Single Source of Truth:**
- `build_player_stats.py` - Creates player_stats.json with archetypes AND advice
- All analysis scripts READ from DB (no duplicate classification logic)
- helper_bar.py reads advice directly from DB

**Deep Research Classification (PokerTracker, Poker Copilot, 2+2, Reddit):**

Key rule: gap > PFR = fish (for loose players VPIP 25+)

| Archetype | VPIP | PFR | Gap | Key Rule |
|-----------|------|-----|-----|----------|
| Maniac | 40+ | 30+ | any | Both very high |
| Fish | 40+ | <20 | any | Loose passive |
| Fish | 25+ | any | >PFR | gap > PFR = fish |
| Nit | ≤18 | any | any | Ultra tight |
| Rock | ≤20 | ≤5 | any | Tight passive |
| TAG | 18-25 | 15+ | ≤5 | Solid reg |
| LAG | 26-35 | 20+ | ≤10 | Loose aggressive |

### Default Strategy: `the_lord` (Session 62-67)
- Opponent-aware version of value_lord
- Uses V2 vision opponent detection + player database
- Multiway pot discipline (Session 67): smaller bets, no bluffs vs 3+ players
- **+59.10 EUR** postflop-only (best strategy, +18% from multiway)
- **+1091 BB** total improvement vs hero (preflop + postflop)

**Multiway betting (3+ players):**
| Hand Strength | Bet Size | Reason |
|---------------|----------|--------|
| Nuts/Set | 50% pot | Keep callers |
| Two pair/Overpair | 40% pot | Value + protection |
| TPGK/Combo draw | 33% pot | Thin value |
| Everything else | CHECK | No bluffs in multiway |

**Archetype-specific adjustments:**
| Archetype | Postflop Adjustment |
|-----------|---------------------|
| fish | Never bluff, value bet big, call down |
| nit/rock | Fold to bets (bet = nuts), bluff more |
| maniac | Call down (they bluff too much) |
| lag | Call down more, fold to big raises |
| tag | Baseline value_lord behavior |

### Key Design Principles
1. **Single source of truth**: All hand analysis uses `analyze_hand()` which computes properties directly from cards - NO string matching on descriptions
2. **Strategy files are truth**: Code must match pokerstrategy_* files exactly
3. **Test the live path**: Simulations test poker_logic.py directly, but live play goes through strategy_engine.py

### Client-Server Architecture
**Windows Client** (C:\aws\onyx-client\)
- User runs helper_bar.py
- Screenshots taken locally
- GPT-5.2 API called directly from Windows (not via server)
- `send_logs.py` uploads session logs to server

**EC2 Server** (54.80.204.92:5001)
- Receives uploads at POST /logs
- Stores in /home/ubuntu/mcpprojects/onyxpoker/server/uploads/

### Memory Reading Architecture (Sessions 71-78)

**Goal:** Replace ~5s GPT vision latency with <1ms memory reads.

**Anti-cheat:** ReadProcessMemory is standard Windows API, undetectable without kernel hooks. PokerTracker uses same approach ("Memory Grabber").

**Packet sniffing ruled out (Session 75):** PokerStars uses TLS + LZHL compression + custom binary protocol. Memory reading is the only viable path.

**poker-supernova offsets are WRONG for our build (Session 76-77):**
The poker-supernova repo assumed cards as int32 rank/suit at seat+0x9C with 0x08 spacing. Our analysis proved cards are stored as ASCII text in a completely different structure (message buffer). The old TABLE/SEAT offset dicts were removed from the code.

### Memory Calibrator v4.1 (Sessions 78-82)

**Complete rewrite of `memory_calibrator.py` based on actual message buffer findings.**

**What was removed (all wrong):**
- poker-supernova TABLE/SEAT offset dicts
- Pointer chain resolution (`_resolve_pointer_chain`)
- Name cluster search at 0x160 spacing (that was the UI struct, not game state)
- Int32 card verification at seat+0x9C
- gzip compression in save_dump()
- `cmd_pointers()` — CE-style pointer chain scan (infeasible in pure Python: 130M dict entries per dump)

**What was added (based on verified findings):**
- `decode_entry()` / `decode_buffer()` — decode 0x40-byte message buffer entries
- `extract_hand_data()` — pulls hero cards, player names, actions, community cards
- `find_buffer_in_dump()` — signature scan for 0x88 marker, validate first entry
- `scan_live()` — runtime: signature scan on live process, returns full hand data dict + `buf_addr`
- `rescan_buffer(buf_addr, hand_id)` — re-read known buffer in <1ms (30 entries x 64B = ~2KB)
- Action code table: CALL=0x43, RAISE=0x45, FOLD=0x46, POST_BB=0x50, POST_SB=0x70, BET=0x42, CHECK=0x63

**Runtime flow (Session 83 — memory polling + GPT parallel):**
```
F9 pressed (helper_bar.py)
  ├─ screenshot + start mem_thread (parallel)
  │     └─ scan_live() (2-4s) → {hero_cards, hand_id, players, actions, buf_addr}
  ├─ GPT V2 call (5.5s) → board, pot, to_call, opponents
  ├─ merge:
  │     memory cards override GPT (ground truth)
  │     hand_id from memory if GPT missed it
  │     player names from memory (no action-word confusion)
  │     UI: [MEM] 8h5d hand=259644772106 (2.3s)
  │     Log: memory_cards, memory_hand_id, memory_players, memory_scan_time, memory_status
  ├─ _display_result() → draw right panel with advice + stats
  └─ _start_mem_poll(buf_addr, hand_id) → starts AFTER display
        └─ rescan_buffer() every 200ms (<1ms each)
        └─ Falls back to GPT cards if memory_cards is None
        └─ Time label: LIVE (N), left panel: [MEM LIVE]
```

**memory_status values:** CONFIRMED (GPT matches), OVERRIDE (GPT wrong, memory corrected), NO_BUFFER (scan failed)

**Calibration workflow (--calibrate mode, for offline verification):**
```
F9 pressed (helper_bar.py --calibrate)
  ├─ save_dump() → memory_dumps/dump_TIMESTAMP.bin + .json
  ├─ GPT returns cards/opponents (~5.5s)
  └─ tag_dump() → writes GPT data into .json sidecar

Offline: python memory_calibrator.py analyze
  → Finds buffer via 0x88 signature + first entry validation
  → Decodes all entries, verifies cards + names against GPT data
```

**Commands:**
```bash
python helper_bar.py                 # V2 default + memory scan + live polling on Windows
python helper_bar.py --calibrate     # Also dumps memory for offline analysis (not needed anymore)
python memory_calibrator.py list     # Show tagged dumps
python memory_calibrator.py analyze  # Verify message buffer in all dumps
python memory_calibrator.py read     # Read cards live (Windows only)
```

**Verified: 17 dumps (14 OK, 2 buffer GC, 1 GPT error caught)** — all cards, names, and actions match. Memory caught 2 GPT suit errors (Qc→Qs, Jc→Jh), both confirmed by HH ground truth.

### Memory Analysis Findings (Sessions 76-78)

**BREAKTHROUGH: Complete game event buffer decoded and verified across ALL 5 dumps.**

The message buffer contains everything needed for poker decisions: hero cards, all player names with seats, and every action with amounts. Stack sizes are NOT in this buffer but are unnecessary — we only need to know what players bet.

**Message buffer entry format (0x40 = 64 bytes):**
```
+0x00: hand_id (8B little-endian)
+0x08: sequence_number (4B, incrementing 1,2,3...)
+0x14: msg_type (1B) — 0x0A=new_hand, 0x01=action, 0x02=seated, 0x07=action_start
+0x16: seat_index (1B, 0-based, 255=table-level)
+0x17: action_code (1B) — 0x43=CALL, 0x45=RAISE, 0x46=FOLD, 0x50=POST_BB, 0x70=POST_SB
+0x18: amount (2B uint16, in cents) — e.g. 55 = €0.55
+0x1C: name_ptr (4B) -> null-terminated player name string
+0x20: name_len (4B)
+0x24: name_capacity (4B)
+0x28: extra_ptr (4B) -> for hero's type 0x02 entry: 4-byte ASCII card string
+0x2C: extra_len (4B)
```

**Entry sequence per hand:**
1. type=0x0A: NEW HAND (table-level, seat=255)
2. type=0x01: POST_SB (action_code=0x70, amount=SB in cents)
3. type=0x01: POST_BB (action_code=0x50, amount=BB in cents)
4. type=0x02: SEATED x6 (one per player, hero entry has extra_ptr -> ASCII cards)
5. type=0x07: ACTION_START (first player to act)
6. type=0x01: Actions in order (CALL/RAISE/FOLD with amounts in cents)

**Action codes (verified against HH ground truth):**
| Code | Action | Amount field |
|------|--------|-------------|
| 0x43 | CALL | call amount in cents |
| 0x45 | RAISE | raise-to amount in cents |
| 0x46 | FOLD | 0 |
| 0x50 | POST_BB | BB amount in cents |
| 0x70 | POST_SB | SB amount in cents |

**How to read hero cards at runtime:**
1. Find buffer (array of 0x40-byte entries, each starting with same hand_id LE)
2. Scan entries for msg_type=0x02 where name_ptr -> "idealistslp"
3. Dereference extra_ptr at entry+0x28 — first 4 bytes = ASCII cards (e.g. "8h5d")
4. Card format: rank+suit+rank+suit, e.g. "8h5d" = 8♥ 5♦, "TdJh" = T♦ J♥

**Verified across ALL 5 dumps (0 errors):**
| Dump | Time | Buffer Addr | Hand ID | Hero Cards | Players | HH Match |
|------|------|------------|---------|------------|---------|----------|
| 1 | 182230 | 0x199F6048 | 259644772106 | "8h5d" | 6/6 names OK | FULL |
| 2 | 182250 | 0x1E4B8758 | 259644777045 | "2dQc" | 6/6 names OK | FULL |
| 3 | 182319 | 0x1E4B97C0 | 259644786517 | "TdJh" | 6/6 names OK | cards+names |
| 4 | 182804 | 0x1ED6A3A0 | 259644860629 | "3h7d" | 6/6 names OK | FULL |
| 5 | 182822 | 0x19105D80 | 259644864917 | "5d4d" | 6/6 names OK | FULL |

Dumps 1,2,4,5: full action sequence verified against hand history files (every action, amount, player matches).
Dump 3: hand_id not in HH files (different table session), but cards and opponent names match screenshot metadata.

**What the buffer gives us (complete for poker decisions):**
- Hero hole cards (ASCII, instant read)
- All 6 player names with seat indices
- Who posted blinds and how much
- Every action in order: who called/raised/folded and for how much
- Pot is calculable from summing all amounts

**What the buffer does NOT contain:**
- Stack sizes (not needed — we only need bet amounts)
- Community cards (likely appear in later entries post-flop, but all 5 dumps captured preflop action only)

**SOLVED: Fast Buffer Finder (Session 79) — 2-4 seconds, 5/5 dumps correct.**

No pointer chain needed. The buffer has a discoverable signature:

**Signature (10 bytes immediately before first entry):**
```
00 88 00 00 00 00 00 00 00 00 [first entry starts here]
```
- byte at buf-10: always `0x00`
- byte at buf-9: always `0x88` ← magic marker
- bytes buf-8 to buf-1: always 8 zero bytes
- Then the first 0x40-byte entry begins (hand_id LE, seq=1)

**Algorithm:**
1. Scan all committed readable memory for the 10-byte signature `00 88 00 00 00 00 00 00 00 00`
2. For each match, check if what follows is a valid first entry: `hand_id` in 200B-300B range AND `seq == 1`
3. Typically 1-4 candidates (stale buffers from previous hands remain in memory)
4. Pick the candidate with the **highest hand_id** (= most recent hand)
5. If tied (rare — dump4 had two with same hand_id), pick the one where hero's SEATED entry has a readable `name_ptr` → "idealistslp"

**Performance:** 2-4 seconds per ~500MB dump (signature scan). No pointer chains, no module offsets, no Cheat Engine needed.

**Why stale buffers exist:** Old hand buffers aren't zeroed out after the hand ends. They keep the 0x88 signature and valid-looking entries, but their name pointers may become dangling (freed strings). The current hand's buffer always has the highest hand_id and valid string pointers.

**Verified: 5/5 dumps, 0 errors, avg 2.6s per dump.**

**Pointer Chain Investigation (Session 84):**

The buffer pointer is NOT stored directly — `buf-8` (allocation base) is stored instead. A table object on the heap holds this pointer at offset +0xE4:

```
Table object (heap, session-stable address):
+0x10: 8 pointers (player/seat data?)
+0xAC: pointer → "EUR\0" (currency string)
+0xE0: 0x00000001
+0xE4: pointer → buf-8 (THE BUFFER POINTER)
+0xE8: pointer → buf+0x558 (end of entries?)
+0xEC: pointer → buf+0x698 (capacity?)
```

Container addresses are stable within a table session but change between tables:
- Early session: `0x1CB872E4` (7 of 14 dumps)
- Late session: `0x19BDFE3C` (4 of 11 dumps)

No static module pointer chain found yet — the table object is not directly referenced from the module. `module+0x01DDA74 = 0x1CB868FF` is a false lead (x86 instruction immediate, not data). The 0x88 signature scan (2-4s) remains the production solution.

**HH-verified seat assignments:**
| Dump | Seat 0 | Seat 1 | Seat 2 | Seat 3 | Seat 4 | Seat 5 |
|------|--------|--------|--------|--------|--------|--------|
| 1 | andresrodr8 | JaviGGWP | **idealistslp** | kemberaid | TJDasNeves | sramaverick2 |
| 2 | fidotc3 | **idealistslp** | codolfito | Prisedeguerre | Ferchyman77 | Miguel_C_Ca |
| 3 | CORDEVIGO | hope201319 | **idealistslp** | Thendo888 | sramaverick2 | chiinche |
| 4 | Miguel_C_Ca | SirButterman | **idealistslp** | iam_xCidx | urubull | kemberaid |
| 5 | **idealistslp** | kastlemoney | GOLDGAMMER | Bestiote | hotboycowboy | CHIKANEUR |

---

## 📁 FILE STRUCTURE

```
onyxpoker/                    # Main repo (GitHub: apmlabs/OnyxPoker)
├── AGENTS.md                 # Permanent knowledge (NEVER DELETE)
├── AmazonQ.md                # Current state + history (NEVER DELETE)
├── README.md                 # Quick start (NEVER DELETE)
├── idealistslp_extracted/    # Real PokerStars hand histories (2830 hands, 53 files)
│   └── HH*.txt               # Raw hand history files from live play
│
├── client/
│   │ # === CORE (live play) ===
│   ├── helper_bar.py         # Main UI (F9=advice, F10=bot, F11=stop, F12=hide)
│   ├── poker_logic/          # Refactored package (Session 73-74)
│   │   ├── __init__.py       # Re-exports everything (existing imports unchanged)
│   │   ├── card_utils.py     # RANKS, SUITS, RANK_VAL, parse_card, equity, outs
│   │   ├── hand_analysis.py  # analyze_hand(), check_draws() (single source of truth)
│   │   ├── preflop.py        # expand_range(), 19 STRATEGIES, preflop_action()
│   │   ├── postflop_base.py  # Config-driven postflop (kiro/kiro_lord/sonnet)
│   │   ├── postflop_value_lord.py  # Active base strategy (value_lord)
│   │   ├── postflop_the_lord.py    # Active default strategy (wraps value_lord + opponent-aware)
│   │   ├── postflop_inactive.py    # 4 inactive strategies (optimal_stats/value_max/gpt/sonnet_max)
│   │   └── _monolith.py      # postflop_action() dispatcher + archetype simulation handlers
│   ├── strategy_engine.py    # Applies strategy (default: the_lord)
│   ├── vision_detector.py    # AI-only mode: gpt-5.2 for vision + decisions
│   ├── vision_detector_lite.py # V1 vision: gpt-5.2 for vision only (~3.9s)
│   ├── vision_detector_v2.py # V2 vision: + opponent detection + hand_id (default, ~5.5s)
│   │
│   │ # === MEMORY CALIBRATION (Windows only) ===
│   ├── memory_calibrator.py  # Auto-dump on F9 + offline analysis (v4, signature-based)
│   │
│   │ # === SIMULATION ===
│   ├── poker_sim.py          # Monte Carlo simulator (200k+ hands)
│   ├── pokerkit_adapter.py   # PokerKit simulation with external engine
│   │
│   │ # === HH ANALYSIS (on hand histories: idealistslp_extracted/*.txt) ===
│   ├── analyse_real_logs.py  # Main HH analysis (--postflop-only is primary mode)
│   ├── analyze_table_composition.py  # Player archetype distribution (calibration)
│   ├── analyze_archetype_behavior.py # Real vs sim postflop behavior (calibration)
│   ├── analyze_bet_sizes.py          # Real bet sizes by archetype (calibration)
│   ├── analyze_betting_strategy.py   # Bet/call win rates by hand strength (calibration)
│   ├── analyze_hole_cards.py         # Hole card BB analysis (calibration)
│   │
│   │ # === SESSION EVALUATION (on session logs: server/uploads/*.jsonl) ===
│   ├── eval_session_logs.py  # VPIP/PFR/CBet stats, replay, compare (consolidated)
│   ├── eval_deep.py          # Simulated benchmark stats vs industry standards
│   │
│   │ # === PLAYER DATABASE ===
│   ├── build_player_stats.py # Creates player_stats.json (single source of truth)
│   ├── opponent_lookup.py    # Lookup opponent stats
│   ├── player_stats.json     # 663 players with archetypes + advice
│   │
│   │ # === TESTS ===
│   ├── run_tests.py          # Test runner (--quick, --all modes)
│   ├── audit_strategies.py   # Strategy file vs code (30 tests)
│   ├── test_strategy_engine.py # Live code path (55 tests)
│   ├── test_postflop.py      # Edge cases (67 tests)
│   ├── test_poker_rules.py   # Poker rules + poker_sim mechanics (24 tests)
│   ├── test_screenshots.py   # V1 vs V2 vision comparison (Windows only)
│   │
│   │ # === UTILITIES ===
│   ├── send_logs.py          # Upload logs to server
│   ├── send_to_kiro.py       # Send to Kiro server
│   │
│   └── pokerstrategy_*       # 19 strategy definition files
│
├── server/
│   ├── kiro_analyze.py       # Flask server on port 5001
│   ├── app.py                # Alternative Flask app (imports poker_strategy.py)
│   ├── poker_strategy.py     # Poker strategy via Kiro CLI subprocess
│   ├── analyze_session.py    # Session log + screenshot correlation
│   └── uploads/              # 71 session logs (.jsonl) + 3018 screenshots (.png)
│       └── compare_with_ground_truth.py  # One-off GPT accuracy comparison
│
└── docs/
    └── DEPLOYMENT.md         # Setup guide
```

### Two Data Sources

| Source | Location | Files | Scripts | Purpose |
|--------|----------|-------|---------|---------|
| Hand Histories | idealistslp_extracted/*.txt | 53 HH files (2830 hands) | analyse_real_logs.py, analyze_*.py | Strategy optimization |
| Session Logs | server/uploads/*.jsonl | 71 sessions + 3018 screenshots | eval_session_logs.py, eval_deep.py | Live play evaluation |

### Script Categories

**Calibration scripts** (run when new HH data arrives):
- analyze_table_composition.py — Update archetype distribution
- analyze_archetype_behavior.py — Update postflop behavior
- analyze_bet_sizes.py — Update bet sizing
- analyze_betting_strategy.py — Update win rates by hand strength
- analyze_hole_cards.py — Hole card BB analysis

**Analysis scripts** (run for strategy development):
- analyse_real_logs.py --postflop-only — Primary analysis tool (the_lord vs hero)
- eval_session_logs.py — Session log analysis (VPIP/PFR/CBet)
- eval_deep.py — Simulated benchmark stats vs industry standards

**Simulation scripts** (run for strategy validation):
- poker_sim.py — Monte Carlo (200k+ hands, internal engine)
- pokerkit_adapter.py — PokerKit simulation (external engine, calibrated archetypes)

---

## 🧪 TESTING FRAMEWORK

### Test Runner (`run_tests.py`)

```bash
cd client && python3 run_tests.py          # Core tests (rules + audit + strategy_engine)
cd client && python3 run_tests.py --quick  # Just rules + audit (fastest)
cd client && python3 run_tests.py --all    # Core + extended (includes postflop)
```

### Automated Tests (run before every commit)

| # | Test | File | Count | What It Tests |
|---|------|------|-------|---------------|
| 1 | Poker Rules | test_poker_rules.py | 24 | Hand rankings, kickers, straights, betting mechanics, showdown. Also tests poker_sim.py mechanics. |
| 2 | Strategy Audit | audit_strategies.py | 30 | Code matches pokerstrategy_* files: preflop ranges, postflop value betting, paired boards, two pair detection |
| 3 | Strategy Engine | test_strategy_engine.py | 55 | Live code path (vision → strategy_engine → poker_logic): facing detection, position ranges, postflop actions, edge cases |
| 4 | Postflop Edge Cases | test_postflop.py | 67 | Per-strategy postflop scenarios: value_lord, the_lord |

**Target: All pass. Run `python3 run_tests.py --all` before commits.**

### Manual Validation (not automated — run as needed)

| Tool | Command | What It Does |
|------|---------|--------------|
| HH Analysis | `python3 analyse_real_logs.py --postflop-only` | Replays all ~2300 real hands through strategy, shows saves/misses vs hero |
| Session Replay | `python3 eval_session_logs.py --replay` | Shows disagreements between strategy and actual live play |
| Strategy Compare | `python3 eval_session_logs.py --compare` | Compares multiple strategies on same session hands |
| Monte Carlo Sim | `python3 poker_sim.py 200000` | 200k hands vs realistic 2NL opponents (internal engine) |
| PokerKit Sim | `python3 pokerkit_adapter.py` | External engine simulation with calibrated archetypes |
| Vision Test | `python3 test_screenshots.py` | V1 vs V2 vision comparison (Windows only) |

### What Has NO Automated Tests (and why)

| Script | Why No Tests |
|--------|-------------|
| analyse_real_logs.py | Analysis tool — output is human-reviewed, not pass/fail |
| pokerkit_adapter.py | Simulation — validated by BB/100 results, not unit tests |
| poker_sim.py | Tested indirectly via test_poker_rules.py (imports simulate_hand, Player, POSITIONS) |
| eval_session_logs.py / eval_deep.py | Evaluation tools — output is stats for human review |
| analyze_*.py (5 calibration scripts) | One-off calibration — run when new HH data arrives, results feed into code changes |
| build_player_stats.py | DB builder — validated by checking player_stats.json output |
| helper_bar.py / vision_detector*.py | Windows-only GUI + GPT API — can't unit test on Linux |
| memory_calibrator.py | Windows-only — requires PokerStars process |

### Testing Workflow
1. Make strategy change in `poker_logic/`
2. Run `python3 run_tests.py --all` → **ALL MUST PASS**
3. Run `analyse_real_logs.py --postflop-only` → check HH performance
4. Run `poker_sim.py 200000` → verify simulation results
5. If all pass, commit changes

---

## 🧠 AGENT WORKFLOW

### After EVERY Coding Session
1. ✅ Update **AmazonQ.md** with session summary and timestamp
2. ✅ Update **AGENTS.md** if new permanent lesson learned
3. ✅ Update **README.md** if user-facing changes
4. ✅ Commit to GitHub with clear message

### Before STARTING New Work
1. ✅ Review **AmazonQ.md** for current status
2. ✅ Review **AGENTS.md** for relevant lessons
3. ✅ Check recent commits for changes

### Red Flags (I'm Failing)
- ⚠️ User asks "did you update docs?" → I forgot
- ⚠️ I suggest something already tried → Didn't read context
- ⚠️ I repeat a mistake → AGENTS.md wasn't updated
- ⚠️ User has to remind me twice → I failed first time

**Context files are my only memory. Without them, I start from scratch every time.**

---

## 📋 FILE RULES

- **NEVER delete**: AGENTS.md, AmazonQ.md, README.md
- **Can delete other .md files IF**: knowledge is incorporated into main files first

---

## ⚙️ TECHNICAL NOTES

### GPT-5.2 Vision
- Model: `gpt-5.2` (configurable in vision_detector.py line 12)
- Cost: ~$2 per 1000 hands
- Speed: 6-9 seconds per analysis
- Accuracy: 95%+ on clear screenshots

### GPT-5 Model Quirks
- GPT-5 models do NOT support `temperature` parameter (must omit, not set to 0)
- Use `max_completion_tokens` not `max_tokens`
- gpt-5.2 is faster than gpt-5-mini (6-9s vs 20-30s)
- gpt-5.1/gpt-5.2 support reasoning_effort="none"
- gpt-5/gpt-5-mini/gpt-5-nano only support "minimal"

### Windows Compatibility
- **NO emojis in logging** - Windows cp1252 encoding crashes on Unicode emojis
- Use ASCII only for cross-platform compatibility
- This has caused bugs 3+ times - NEVER use emojis in Python code

### Key Code Patterns

**analyze_hand() returns:**
```python
{
    'strength': 1-9,           # high card to straight flush
    'desc': "top pair Ks",     # human readable
    'is_pocket_pair': bool,
    'is_overpair': bool,
    'has_top_pair': bool,
    'has_good_kicker': bool,
    'has_two_pair': bool,
    'two_pair_type': str,      # pocket_over_board, pocket_under_board, both_cards_hit
    'has_set': bool,
    'has_flush_draw': bool,
    'is_nut_flush_draw': bool,
    # ... many more flags
}
```

**Two Pair Types (critical for paired boards):**
- `pocket_over_board`: KK on JJ = STRONG (only JJ beats us)
- `pocket_under_board`: 66 on JJ = WEAK (any Jx has trips)
- `both_cards_hit`: A7 on A72 = STRONG
- `one_card_board_pair`: K2 on K22 = depends on board pair rank

**Pot Percentage vs Pot Odds (CRITICAL - standardized Jan 17 2026):**
```python
# pot_pct = bet sizing as % of pot (use for fold thresholds)
pot_pct = to_call / pot  # €5 into €10 = 50%

# pot_odds = equity needed to call (use for draw decisions)
pot_odds = to_call / (pot + to_call)  # €5 into €10 = 33%
```
- Use `pot_pct` when comparing bet sizes: "fold if pot_pct > 0.6"
- Use `pot_odds` when comparing equity: "call if equity > pot_odds"
- NEVER mix them up - a 50% pot bet needs only 33% equity to call!

---

## 🔑 CRITICAL LESSONS

### 1. GPT Vision > OpenCV
AI understands poker semantically, not just visually. OpenCV was 60-70% accuracy with 2000 lines of calibration code. GPT-5.2 is 95%+ with no calibration.

### 2. No Calibration Needed
Screenshot active window directly. Don't build calibration tools - they become the project instead of the poker bot.

### 3. Single Source of Truth
Never have two functions computing the same thing. `evaluate_hand()` and `analyze_hand()` drifted apart causing bugs. Merged into single `analyze_hand()`.

### 4. Test the Live Code Path
Simulations (poker_sim.py) and evaluations (eval_session_logs.py) call poker_logic.py directly. But live play goes through strategy_engine.py. Bugs in the glue code are invisible to simulations. Created test_strategy_engine.py to catch these.

### 5. Equity vs Random is Wrong for Facing Bets
Monte Carlo equity assumes villain has random hands. When villain bets, their range is NOT random. Use hand strength categories instead: "fold one pair to 50% pot river bet" matches human thinking.

### 6. Simulation ≠ Reality
- Simulation rewards aggression (simulated opponents fold)
- Real 2NL rewards discipline (fish call everything AND hit hands)
- value_lord wins in simulation but kiro_lord wins on real data
- Choose strategy based on actual opponent pool

### 7. Array Indexing Matters
Session 49 bug: `preflop_actions[0]` (first raise) vs `preflop_actions[-1]` (last raise). A9s vs 3bet was detected as vs open because code used first raise amount. Always verify array semantics.

### 8. Context Files Are Memory
Without AGENTS.md and AmazonQ.md, agent starts from scratch every session. These files ARE the agent's long-term memory.

### 9. User Frustration = Audit Needed
When user says "moving back in time" or expresses frustration, STOP incremental fixes. Do complete audit of the system.

### 10. Listen to Repeated Constraints
User said "single monitor" multiple times while I kept designing for dual monitor. When user repeats a constraint, redesign with that constraint as PRIMARY requirement.

---

## 🐛 KEY BUG PATTERNS

### Never Do This

| Bug Pattern | Sessions | Why It's Bad | Fix |
|-------------|----------|--------------|-----|
| Emojis in Python | 10, 11 | Windows cp1252 crashes | ASCII only |
| String matching on desc | 35, 36 | Fragile, descriptions change | Use analyze_hand() flags |
| Two functions for same thing | 43.7 | They drift apart | Single source of truth |
| Using `[0]` when need `[-1]` | 49 | Wrong array element | Check semantics |
| Equity vs random for bets | 38 | Villain range not random | Hand strength categories |
| Testing poker_logic only | 34 | Misses strategy_engine bugs | Test live path |
| Hardcoding to_call=0 | 43.13 | Breaks postflop facing | Separate preflop/postflop |
| C-bets = bluffs | 70 | C-bets win when villain folds | Allow c-bets even vs fish |
| Start poll before display | 83 | Display overwrites poll output | Start poll AFTER _display_result |
| Raw file size on Windows | 83 | \r\n vs \n size mismatch | Compare content.encode() size |

### Common Gotchas

**C-bets are NOT bluffs (Session 70):**
```python
# BUG: Blocked all c-bets vs fish as "bluffs"
if base_action == 'bet' and strength < 2:
    return ('check', 0, "no bluff vs fish")  # WRONG - c-bets are profitable!

# FIX: Allow c-bets when aggressor on flop
if base_action == 'bet' and strength < 2:
    if is_aggressor and street == 'flop':
        return (base_action, base_amount, reason + " vs fish")  # C-bet allowed
    return ('check', 0, "no bluff vs fish")  # Only block turn/river bluffs
```

**Preflop loop affects postflop (Session 43.13):**
```python
# BUG: Preflop loop forces to_call=0, postflop reused this
for pos in positions:
    pos_data = {**table_data, 'to_call': 0}  # Forces to_call=0!
result = all_position_results['BTN']  # Wrong action for postflop!

# FIX: Separate paths
if street == 'preflop':
    # Loop with to_call=0 for open ranges
else:
    # Call directly with real to_call
```

**facing_raise removed from vision (Session 60):**
```python
# OLD: Vision returned facing_raise but it was unreliable and never used
# facing_raise was read in strategy_engine but _preflop() calculated facing from to_call

# NEW: Removed facing_raise entirely from vision prompts
# to_call is the sole indicator - read from CALL button on screen
if to_call <= big_blind:
    facing = 'none'  # No raise
elif to_call <= big_blind * 12:
    facing = 'open'  # Open raise
```

**Board trips ≠ hero trips (Session 43.7):**
```python
# BUG: KJ on 333 was classified as "trips 3s"
# evaluate_hand() counted board trips as hero trips

# FIX: Check if hero card matches trips
if board_trips and hero_card in board_ranks:
    has_trips = True  # Hero actually has trips
else:
    has_trips = False  # Just board trips, hero has high card
```

**Pocket pair on paired board (Session 43.6):**
```python
# BUG: 88 on 577 was raising - disaster!
# ANY pocket pair on paired board is vulnerable to trips

# FIX: Both pocket_over_board and pocket_under_board
# fold to big bets (>50% pot), call small bets
if two_pair_type in ['pocket_over_board', 'pocket_under_board']:
    if pot_pct > 0.5:
        return ('fold', 0, "fold vulnerable two pair")
```

**Underpair calling down (Session 43.4):**
```python
# BUG: JJ calling on Q-K-A board vs aggression
# Equity vs random (63-69%) is meaningless when villain bets 3 streets

# FIX: Underpair defense
if is_underpair:
    if street == 'flop' and pot_pct <= 0.5:
        return ('call', 0, "call once")  # See if villain slows down
    if street in ['turn', 'river']:
        return ('fold', 0, "fold underpair vs aggression")
```
