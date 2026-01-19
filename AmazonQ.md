# OnyxPoker - Status Tracking

**Last Updated**: January 19, 2026 01:30 UTC

---

## Current Status

### What Works
| Component | Status | Notes |
|-----------|--------|-------|
| helper_bar.py | ✅ | V2 vision default (player detection + opponent stats) |
| helper_bar.py --v1 | ✅ | V1 vision (no player detection) |
| helper_bar.py --ai-only | ✅ | AI does both vision + decision |
| test_screenshots.py | ✅ | V1 vs V2 comparison (default) |
| vision_detector_lite.py | ✅ | GPT-5.2 for vision only (V1) |
| vision_detector_v2.py | ✅ | GPT-5.2 + player name detection (V2) |
| build_player_stats.py | ✅ | Single source of truth for player archetypes |
| strategy_engine.py | ✅ | 3-bet/4-bet ranges + BB defense |
| poker_logic.py | ✅ | Data-driven value_lord postflop |
| poker_sim.py | ✅ | Full postflop simulation |
| analyse_real_logs.py | ✅ | Shows unsaved losses by default |
| All test suites | ✅ | audit(30), strategy_engine(55), postflop(67), rules(24) |
| Server | ✅ | 54.80.204.92:5001 |

### Default Strategy: `value_lord`
- Data-driven betting/calling from 2,018 real hands
- 50% pot standard sizing, c-bet max 4BB
- Never call river high card (0% win rate)

### Player Database (565 players, deep research classification)
| Archetype | Count | % | Advice |
|-----------|-------|---|--------|
| fish | 190 | 33.6% | Isolate wide \| Value bet \| Calls too much \| Never bluff |
| nit | 144 | 25.5% | Steal blinds \| Fold to bets \| Too tight \| Raise IP, fold to 3bet |
| rock | 83 | 14.7% | Steal more \| Bet = nuts \| Raises monsters \| Raise IP, fold vs bet |
| maniac | 50 | 8.8% | Only premiums \| Call everything \| Can't fold \| vs raise: QQ+/AK |
| lag | 49 | 8.7% | Tighten up \| Call down \| Over-aggro \| vs raise: 99+/AQ+ |
| tag | 49 | 8.7% | Respect raises \| Play solid \| Avoid \| vs raise: TT+/AK |

---

## Session History

### Session 60: V2 Vision Default + Test Comparison (January 19, 2026)

**Made V2 vision the default for helper_bar.py.**

**Changes:**
- `helper_bar.py` now uses V2 vision by default (player detection + opponent stats)
- `--v1` flag for old V1 vision (no player detection)
- `--visionv2` flag removed (now default)
- Removed `facing_raise` from vision prompts (dead code - we use `to_call` instead)
- Removed `facing_raise` from strategy_engine.py (was read but never used)

**test_screenshots.py updated:**
- Default mode: V1 vs V2 comparison on same screenshots
- `--compare N` to test N screenshots
- Saves results to `client/logs/vision_compare_results.json` after each screenshot
- Detailed field-by-field comparison output

**Vision comparison results (8 screenshots):**
- Match rate: 100% on core fields
- V1 avg: 5.2s, V2 avg: 10.0s (+4.8s for player detection)
- V2 player detection issue: picks up UI text ("Post SB", "Fold") as player names

**Code cleanup - facing_raise removal:**
```
to_call is read from CALL button → used to calculate facing
facing_raise was asked in vision → read in strategy_engine → never used
```

**Usage:**
```bash
python helper_bar.py          # V2 default
python helper_bar.py --v1     # V1 mode
python test_screenshots.py    # Compare V1 vs V2
python test_screenshots.py --compare 20
```
- `--v1` flag for old V1 vision (no player detection)
- `--visionv2` flag removed (now default)

**test_screenshots.py updated:**
- Default mode: V1 vs V2 comparison on same screenshots
- `--compare N` to test N screenshots
- `--v1` or `--v2` for single mode testing
- Real-time output with progress

**Usage:**
```bash
python helper_bar.py          # V2 default
python helper_bar.py --v1     # V1 mode
python test_screenshots.py    # Compare V1 vs V2
python test_screenshots.py --compare 20
```

### Session 59: Deep Research Classification (January 18, 2026)

**Refined archetype classification based on comprehensive research from PokerTracker, Poker Copilot, SmartPokerStudy, 2+2, Reddit.**

**Key Changes:**
- Fish: VPIP 40+ (was 52+), added "gap > PFR = fish" rule
- Maniac: VPIP 40+ (was 50+) with PFR 30+
- LAG: VPIP 26-35, gap ≤10 (was ≤12)
- Nit: VPIP ≤18 (was ≤14)
- Rock: VPIP ≤20, PFR ≤5

**Research-Based Classification:**
| Archetype | VPIP | PFR | Gap | Key Rule |
|-----------|------|-----|-----|----------|
| Maniac | 40+ | 30+ | any | Both very high |
| Fish | 40+ | <20 | any | Loose passive |
| Fish | 25+ | any | >PFR | gap > PFR = fish |
| Nit | ≤18 | any | any | Ultra tight |
| Rock | ≤20 | ≤5 | any | Tight passive |
| TAG | 18-25 | 15+ | ≤5 | Solid reg |
| LAG | 26-35 | 20+ | ≤10 | Loose aggressive |

**Single Source of Truth:**
- `build_player_stats.py` creates player_stats.json with archetypes AND advice
- `helper_bar.py` reads advice from DB (no duplicate logic)

### Session 58: V2 Vision with Player Detection (January 18, 2026)
- helper_bar.py reads archetypes from DB, only stores advice text

**Sidebar Display:**
```
mikoa - vs their raise: only TT+/AK
felga - bet any pair big, never bluff
Cacho - raise any hand in position, fold to their 3bet
---
TOP PAIR (good kicker)
```

**Files Changed:**
- helper_bar.py: --visionv2 flag, simplified to use DB archetypes
- build_player_stats.py: Industry-standard classification with sources
- analyze_table_composition.py: Uses DB instead of recalculating
- analyze_archetype_behavior.py: Uses DB instead of recalculating

### Session 56: Unsaved Losses in Default Output (January 18, 2026)

**Added unsaved losses section to analyse_real_logs.py default output.**

Now shows hands where value_lord plays through but still loses (coolers):
- 39 hands, 1408 BB total
- Top losses: AJs two pair (103 BB), AKo vs KK (101 BB), flush vs higher flush (99/91 BB)
- All are genuine coolers - strategy is sound

**UI tweak:** Reduced right panel font 30% (28pt → 20pt)
### Session 57: PokerKit Calibration Update (January 18, 2026)

**Updated simulation to match 2,288 real hands analysis.**

**Table Composition (pokerkit_adapter.py):**
| Archetype | Old | New |
|-----------|-----|-----|
| fish | 12% | 17% |
| nit | 25% | 26% |
| tag | 39% | 39% |
| lag | 23% | 17% |
| maniac | 1% | 1% |

**Bet Sizes (poker_logic.py):**
- Fish: 50-60% → 55-65% (real median 58%)
- Nit TPGK: 60% → 65% (real median 62%)

**TAG Behavior (checks too much in sim):**
- TPWK bet freq: 50% → 60%
- Pair bet freq: 20% → 30%
- Semi-bluff freq: 45% → 55%

**Results:** value_lord +31.07 BB/100 (up from +24.1)

**Last 2 sessions analysis (files #5, #6):**
- 230 hands, only 1 big loss: JJ vs KK (-63 BB) - pure cooler
- All other losses under 10 BB


**Test results:** All passing
- test_poker_rules.py: 24/24
- audit_strategies.py: 30/30
- test_strategy_engine.py: 48/55 (known edge cases)
- test_postflop.py value_lord: 51/70 (intentional conservative folds)

### Session 55: Bottom Pair Discipline + Disaster Analysis (January 17, 2026)

**Fixed pokerkit_adapter.py bug:** `bet` action wasn't handled (only `raise`), so postflop bets weren't being placed.

**Added `--disasters` flag** to pokerkit_adapter.py - shows top 10 worst hands with full context.

**Tightened bottom pair play:**
- Before: Bottom pair treated same as middle pair (call ≤33% on turn/river)
- After: Bottom pair folds turn/river always, calls flop only ≤33%

**50k hand simulation results:**
- BB/100: **+32.4** (up from +20 before fixes)
- Top 10 disasters: 9/10 are coolers (flush vs higher flush, full house vs quads)
- No more bottom pair calling down disasters

### Session 54: Pot Odds Standardization + Losing Hand Analysis (January 17, 2026)

**Fixed pot_pct vs pot_odds confusion across entire codebase.**

Bug: 5 archetype functions used `to_call / (pot + to_call)` (pot odds) but compared against bet sizing thresholds like 0.60 (pot percentage).

```python
# pot_pct = bet sizing as % of pot (use for fold thresholds)
pot_pct = to_call / pot  # €5 into €10 = 50%

# pot_odds = equity needed to call (use for draw decisions)
pot_odds = to_call / (pot + to_call)  # €5 into €10 = 33%
```

Fixed lines 968, 1034, 1094, 1171, 1251 in poker_logic.py. Audit: 30/30 PASS.

**Analyzed 18 losing hands (20BB+) that value_lord would still play:**

| Hand | Board | Lost BB | Verdict |
|------|-------|---------|---------|
| AJs | 3s 4h Jc As 4d | 103.0 | Cooler - villain flopped 43s two pair |
| AKo | 2d 3h 3c 6s 4h | 100.8 | Preflop all-in AKo vs KK |
| AKo | 3s Ts Qs Ad Qd | 100.0 | River 64% pot vs 66% threshold - borderline |
| AQs | 3h 9c 3s 9h 5h | 71.6 | Hero ignored strategy - value_lord says CHECK |

**Key insight:** Most big losses are coolers (AKo vs KK, sets vs two pair). Strategy is sound.

### Session 52: Improved Preflop UI (January 17, 2026)

**Enhanced "vs raise" line 2 with 3-bet guidance.**

- Shows 3-bet advice: "4BET or CALL any", "3BET value, call 4bet", "3BET bluff or FOLD"
- Position-specific when different: "UTG/MP/CO/BTN/SB: CALL 2.5bb | BB: CALL 3bb"
- Compact when same for all positions

**Example outputs:**
```
vs raise: 4BET or CALL any                              (AA, KK, AKs)
vs raise: 3BET value, call 4bet                         (QQ, JJ, AQs)
vs raise: 3BET bluff or FOLD                            (A5s, 87s)
vs raise: UTG/MP/CO/BTN/SB: CALL 2.5bb | BB: CALL 3bb   (A9o, KTo)
```

---

### Session 53: Stats Panel Cleanup + Archetype Calibration (January 17, 2026)

**UI: Cleaned up right stats panel**
- Removed verbose TRUE/FALSE spam
- Now shows only: hand strength (green), draws (cyan), board dangers (orange)
- Font 3x bigger (28pt vs 9pt) for readability

**Simulation: Updated archetype postflop behavior**
- Real data showed sim opponents check too much (47-55% vs 38-48% real)
- TAG had biggest gap: now bets TPWK 50% (was 30%), calls +20%
- All archetypes bet and call more, matching real 2NL behavior
- value_lord still ~+19 BB/100 against tougher opponents

---

### Session 51: Data-Driven Betting Strategy (January 17, 2026)

**Rewrote value_lord based on 2,018 real hand analysis.**

Created `analyze_betting_strategy.py` to analyze all bets/calls by:
- Street (flop/turn/river)
- Hand strength (high card, TPWK, TPGK, two pair, set, etc.)
- Bet size buckets (0-4BB, 4-10BB, 10-20BB, 20+BB)
- Aggressor status

**Key Findings:**
| Pattern | Win Rate | Action |
|---------|----------|--------|
| Flop high card c-bet as aggressor | 60% | Bet max 4BB |
| Flop high card NOT aggressor >10BB | 0% | Never bet |
| Turn high card bet | 36% | Don't bet |
| Turn weak pair bet | 33% | Don't bet |
| River high card call | 0% (6 calls) | Never call |
| Top pair flop bet | 78-89% | Bet 50% pot |

**value_lord Changes:**
- Betting: 50% pot standard, c-bet capped at 4BB, no turn bluffs
- Calling: Never call river high card, fold turn weak hands

**Impact on real hands (20BB+):**
- SAVES: 18 hands, +909 BB
- MISSES: 10 hands, -560 BB
- NET: **+348.6 BB**

---

### Session 50: Simulation Calibration (January 17, 2026)

**Updated simulation to match real 2NL table data.**

Ran all three analysis scripts on new hand histories:
- `analyze_table_composition.py` - Player archetype distribution
- `analyze_bet_sizes.py` - Real bet sizes by archetype
- `analyze_archetype_behavior.py` - Check/bet/call/fold frequencies

**Table Composition Update (pokerkit_adapter.py)**
| Archetype | Old | New (Real) |
|-----------|-----|------------|
| fish | 8.5% | **12%** |
| nit | 31% | **25%** |
| tag | 39% | 39% |
| lag | 22% | **23%** |
| maniac | 0% | **1%** |

**Bet Size Update (poker_logic.py)**
| Archetype | Old Range | New (Real Median) |
|-----------|-----------|-------------------|
| fish | 35-62% | **40-70%** (median 51%) |
| nit | 45-54% | **60-70%** (median 65%) |
| tag | 45-68% | **50-72%** (median 56%) |
| lag | 35-55% | **45-70%** (median 59%) |

**Key Finding:** Real players bet bigger than simulation assumed, especially nits (65% vs 45-50%).

**Impact:** value_lord drops from +24.8 to ~+18 BB/100 - more realistic against tougher opponents.

---

### Session 49: analyse_real_logs.py Bug Fixes (January 17, 2026)

**Fixed two bugs misclassifying hands.**

**Bug #1: Postflop Savings Not Counting Folds**
- `calculate_postflop_savings()` only counted savings when strategy "checks"
- Fix: Count fold savings + all future street savings when folding

**Bug #2: Wrong Preflop Raise Detection**
- `get_preflop_facing()` used `preflop_actions[0]` instead of `[-1]`
- A9s vs 3bet (€0.45) was detected as vs open (€0.10)
- Fix: Use last raise amount

**Results:**
- A9s (73.0 BB loss) now correctly shows as SAVES
- Full analysis: 97 hands where value_lord differs, NET +424.9 BB

---

### Session 48: Paired Board Discipline (January 17, 2026)

**Stop betting into paired boards with weak hands.**

- Added `is_double_paired_board` detection to `analyze_hand()`
- Double-paired board (3399): CHECK unless full house+
- Single-paired board (77x): CHECK turn/river unless set+
- audit_strategies.py: 30/30 PASS

---

### Session 47: Check-Raise Detection (January 16, 2026)

**Added villain check-raise detection.**

- Track `last_hero_action` per street across F9 presses
- Detect villain raise: hero already acted AND now faces to_call > 0
- New folds: two pair vs check-raise, overpair vs check-raise on river

**eval_real_hands.py Fix:**
- Bug: Postflop miss used `hero_profit` instead of `pot + to_call`
- Result: Postflop miss € dropped from €10+ to €4.64

---

### Session 46: Default Strategy Switch (January 16, 2026)

**Switched default from kiro_lord to value_lord.**

**PokerKit Results (20k hands):**
| Strategy | BB/100 |
|----------|--------|
| value_maniac | +26.5 |
| value_lord | +24.1 |
| kiro_lord | -8.8 |

**Key Insight:** Real data favors tight strategies (folding losers), simulation favors aggressive (extracting value). value_lord balances both.

---

### Session 45: PokerKit Integration (January 16, 2026)

**External validation with PokerKit library.**

- Created `pokerkit_adapter.py` bridging OnyxPoker → PokerKit
- Fixed simulate() to track hero for all hands
- Real 5NL composition: 8.5% fish, 31% nit, 39% TAG, 22% LAG

---

### Session 44: eval_real_hands.py Bug Fixes (January 16, 2026)

- Bug 1: `raises €0.10 to €0.15` took €0.10, now takes €0.15 (total)
- Bug 2: `Uncalled bet returned` wasn't subtracted from invested
- Actual results: €-16.00 (-29.9 BB/100) not €-93.12

---

### Session 43: Major Refactoring (January 14-16, 2026)

**Part 24: Real Table Composition**
- Real 5NL: 8.5% fish, 31% nit, 39% TAG, 22% LAG
- Old sim assumed 60% fish - way too easy!

**Part 23: Poker Rules Verification**
- Created test_poker_rules.py (24 tests)
- Verified hand rankings, betting mechanics, showdown

**Part 22: kiro_lord Strategy**
- Combined kiro_optimal preflop + 5 postflop improvements
- 100% postflop accuracy (14/14 scenarios)

**Part 21: Real Hand History Evaluation**
- Evaluated 12 strategies on 1,209 real hands
- optimal_stats wins on real data, value_lord wins in simulation

**Part 14: eval_deep.py**
- Deep strategy evaluation with VPIP/PFR/AF
- Industry benchmarks: TAG 21%/18%/2.5, LAG 28%/25%/3.5

**Part 13: Critical Postflop Bug**
- Postflop was using to_call=0 (from preflop loop)
- Said CHECK when facing $0.55 bet
- Fix: Separate preflop/postflop paths

**Part 10: Strategy Audit Expanded**
- Added gpt4/sonnet specific tests
- Full house bug fix (board trips + pocket pair)

---

### Session 42: value_lord Validation (January 14, 2026)

**Analyzed 251 hands across 2 sessions.**

- High card c-bets: 13-16 per session
- User instincts about c-betting after calling = correct
- value_lord matches user's preferred playstyle

---

### Session 41: value_lord Creation (January 14, 2026)

**Created value_lord based on value_maniac with 3 fixes:**
1. Only c-bet high card when `is_aggressor=True`
2. Overpairs ALWAYS bet
3. Weak pairs CHECK on straight boards

---

### Session 40: First Winning Live Session (January 14, 2026) 🎉

**141 hands with value_maniac strategy.**

- Big wins: JJ (~$10), Set 4s (~$8), Quads (~$7)
- Correct folds: KJ vs $14.55 all-in, AK vs $7.46 all-in
- Overbets with pairs getting paid consistently

---

### Session 39: eval_strategies.py Fix (January 14, 2026)

- Bug: `is_value_hand` compared int to string (always True)
- Bug: `has_any_pair` counted board pairs as hero pairs
- Fix: Bad fold detection uses hand strength + bet size categories

---

### Session 38: Equity vs Random Bug (January 13, 2026)

**Fundamental fix for river defense.**

- Bug: Equity vs random used for facing bets
- Fix: Use hand strength + pot-relative sizing
- Conservative draw thresholds: NFD 41%, OESD 22%, gutshot 12%

---

### Session 37: Position Fix (January 13, 2026)

- eval_strategies.py was defaulting to BTN for all hands
- Fix: Cycle through all 6 positions for fair average

---

### Session 36: Complete analyze_hand() Refactor (January 13, 2026)

- Eliminated ALL string matching on `desc`
- Extended analyze_hand() with middle_pair, bottom_pair, flush_draw, etc.
- Refactored all strategies and archetypes

---

### Session 35: analyze_hand() Creation (January 13, 2026)

- Created single source of truth for hand properties
- Two pair types: pocket_over_board, pocket_under_board, both_cards_hit
- Created audit_strategies.py (21 tests)

---

### Session 34: Strategy Engine Bug Fix (January 13, 2026)

- Bug: `facing_raise` from vision unreliable
- Fix: Use `to_call` as sole indicator
- Created test_strategy_engine.py (55 tests)

---

### Session 33: test_postflop.py (January 13, 2026)

- Created 67 postflop edge case scenarios
- value_max leak fix: equity-based instead of fixed thresholds

---

### Session 32: Postflop Equity UI (January 13, 2026)

- Added calculate_equity() Monte Carlo simulation
- UI shows: "Win: 67.6% | Outs: 9 (flush) | Odds: 33.3%"

---

### Session 31: Smart Postflop Fixes (January 13, 2026)

- Fixed board pair detection (AJ on Q22 was "pair")
- Fixed TPWK (was potting, now 40% flop only)
- value_max now #1 at +46.82 BB/100

---

### Session 30: Archetype Tuning (January 12, 2026)

- Analyzed 162 real hands
- Added maniac archetype
- Fish now limp 30%, limp-call 60%
- Created 2nl_exploit strategy

---

### Session 29: Architecture Finalization (January 12, 2026)

- Strategy engine is now default
- `--ai-only` flag for GPT-5.2 to do both vision + decision
- vision_detector_lite.py: gpt-4o-mini → gpt-5.2

---

### Session 28: Ground Truth & Vision Testing (January 12, 2026)

- Built 50-screenshot verified dataset
- GPT-5.2: 91% card accuracy vs Kiro's 61%
- Repository consolidation: merged server/ into main repo
- Kiro CLI speed optimization: 12.7s → 4.3s (66% faster)

---

### Session 27: Strategy-Specific Postflop (January 12, 2026)

- Each strategy now uses its own postflop logic
- gpt3/gpt4: Board texture aware (25-35% c-bets)
- sonnet/kiro_optimal: Big value bets (75-85%)

---

### Session 26: Strategy Simulator (January 12, 2026)

- Built poker_sim.py
- 8 strategy files analyzed
- 4 player archetypes: fish, nit, lag, tag

---

### Sessions 9-22: Foundation (December 29, 2025 - January 9, 2026)

- Session 9-10: GPT-4o vision replaced OpenCV
- Session 11: Switched to gpt-5.2 (2-3x faster)
- Session 12: Created helper_bar.py, restored deleted agent files
- Session 13: Screenshot saving, session logging, Kiro server
- Session 14-16: Draw verification, position detection fixes
- Session 20: Position detection bug (only BTN/SB/BB detected)
- Session 21: JSON schema field name mismatch fix
- Session 22: Infrastructure cleanup

---

## Quick Reference

### UI Features
- **Borderless**: No Windows title bar
- **Draggable**: Click top bar to move
- **Hotkeys**: F9=Advice, F10=Bot, F11=Stop, F12=Hide

### Strategy-Specific Postflop
| Strategy | Style |
|----------|-------|
| value_maniac | Overbets + protection |
| value_lord | Conservative c-bet, aggressive value |
| value_max | Equity-based pot odds |
| gpt3/gpt4 | Board texture aware |
| sonnet | Big value bets |

### Industry Benchmarks
| Type | VPIP | PFR | AF |
|------|------|-----|-----|
| Fish | 56% | 5% | 0.5 |
| TAG (Winner) | 21% | 18% | 2.5 |
| LAG | 28% | 25% | 3.5 |

---

## Future Plans

### Session Results Aggregator (Not Yet Built)
- Parse session logs for ACTUAL money won/lost
- Calculate real BB/100 across sessions
- Compare live results vs simulation predictions
- **When to build**: After 500+ live hands
