# OnyxPoker - Status Tracking

**Last Updated**: January 15, 2026 13:57 UTC

## 🎉 MILESTONE: FIRST WINNING SESSION! 🎉

**Session 40 marks the FIRST TIME the system produced real winning results in live play.**

After 40 sessions of development, testing, and refinement - we finally have a working poker assistant that wins money at 2NL. The value_maniac strategy's overbets with pairs are getting paid consistently.

---

## Current Status: SESSION 43 Part 15 - Deep Eval Enhanced ✅

**ENHANCED**: `eval_deep.py` now replays logged hands through each strategy for accurate postflop stats.

**Key Changes**:
1. **Postflop stats per strategy**: Instead of reading logged actions, replays 928 hands through each strategy's `postflop_action()` 
2. **Session logging enhanced**: Now logs `num_players`, `is_aggressor`, `facing` for future analysis
3. **Strategy comparison**: Shows real differences between strategies

**Top 5 Strategy Analysis**:
| Strategy | VPIP | PFR | Gap | AF | Profile |
|----------|------|-----|-----|-----|---------|
| **sonnet** | 18.6% | 13.4% | 5.3 | **2.57** | TAG ⭐ (closest to optimal) |
| **gpt4** | 19.5% | 13.6% | 5.9 | 3.10 | TAG |
| **value_max** | 31.1% | 21.7% | 9.4 | 2.95 | LAG |
| **value_maniac** | 31.8% | 21.7% | 10.1 | 4.82 | LAG |
| **value_lord** | 31.8% | 21.7% | 10.1 | 5.43 | LAG |

**Key Insights**:
- sonnet has best AF (2.57) - closest to winning TAG profile
- value_* strategies are LAGs - work at 2NL, exploitable higher
- All strategies have high Gap (call too much vs 3-bet)
- 3-bet% is low (3-6%) - should be 6-10%

---

## Previous: SESSION 43 Part 14 - Deep Strategy Evaluation ✅

**NEW TOOL**: `eval_deep.py` - Comprehensive strategy analysis with real poker metrics.

**What it does**:
1. **Preflop Profile**: Simulates all 169 hands × 6 positions through strategy
   - VPIP, PFR, Gap (industry-standard stats)
   - 3-bet %, BB Defense %
   - Position breakdown (UTG through BB)
2. **Postflop Profile**: Replays logged hands through strategy
   - Aggression Factor (AF) by street
   - Fold %, Aggression %
3. **Comparison**: Shows where strategy falls on fish→winner spectrum

**Industry Benchmarks**:
| Type | VPIP | PFR | Gap | AF | Profile |
|------|------|-----|-----|-----|---------|
| Fish | 56% | 5% | 51 | 0.5 | Loose-Passive |
| TAG (Winner) | 21% | 18% | 3 | 2.5 | Tight-Aggressive |
| LAG | 28% | 25% | 3 | 3.5 | Loose-Aggressive |

---

## Previous: SESSION 43 Part 13 - Critical Postflop Bug Fix ✅

**CRITICAL BUG FIXED**: Postflop was always using `to_call=0`, causing CHECK advice when facing bets!

**Root Cause**: helper_bar.py reused the preflop position loop (which forces `to_call=0`) for postflop decisions. The action came from `all_position_results['BTN']` computed with `to_call=0`, but the log wrote the real `to_call` from vision.

**Fixes Applied**:
1. **Postflop facing bet**: Now uses real `to_call` → FOLD/CALL instead of CHECK
2. **BB Line 1**: Shows defense threshold (CALL 3bb/6bb/any) instead of CHECK
3. **Min-raise thresholds**: Marginal hands show "CALL up to 2.5bb" instead of FOLD

**New Line 1 Format**:
```
UTG:RAISE | MP:RAISE | CO:RAISE | BTN:RAISE | SB:RAISE | BB:CALL 3bb
```
BB now shows defense threshold, not useless "CHECK"

**New Line 2 Thresholds**:
- `CALL any` - AA, KK, AKs, AKo
- `CALL up to 15bb` - JJ, TT, AQs
- `CALL up to 4bb` - suited connectors, broadways
- `CALL up to 3bb` - BB defend hands
- `CALL up to 2.5bb` - opening hands (can call min-raises)
- `FOLD` - trash hands

**Test Results:**
- ✅ Postflop with to_call=0.55 → FOLD (was CHECK)
- ✅ BB defense: AA→CALL any, JJ→CALL 6bb, T9s→CALL 3bb
- ✅ Min-raise: K8o→CALL up to 2.5bb (was FOLD)

## What Works

| Component | Status | Notes |
|-----------|--------|-------|
| helper_bar.py | ✅ Fixed | Postflop uses real to_call, BB shows defense |
| vision_detector.py | ✅ Ready | Full mode: GPT-5.2 for vision + decisions |
| vision_detector_lite.py | ✅ Ready | Lite mode: GPT-5.2 for vision only |
| strategy_engine.py | ✅ Fixed | BB defense + min-raise thresholds |
| poker_logic.py | ✅ Refactored | analyze_hand() for all hand analysis |
| poker_sim.py | ✅ Ready | Full postflop simulation |
| audit_strategies.py | ✅ Ready | 21 tests - code matches strategy files |
| test_strategy_engine.py | ✅ Ready | 55 tests for live code path |
| test_postflop.py | ✅ Ready | 70 edge case scenarios |
| eval_strategies.py | ✅ Fixed | Hand strength based bad fold detection |
| Server | ✅ Running | 54.80.204.92:5001 |

## Testing Framework

| Test File | Tests | Coverage |
|-----------|-------|----------|
| audit_strategies.py | 21 | Code matches strategy file descriptions |
| test_strategy_engine.py | 55 | Live code path (vision → engine → logic) |
| test_postflop.py | 70 | Postflop edge cases |
| eval_strategies.py | 1150 | Real hands from session logs |
| poker_sim.py | 200k | Monte Carlo simulation |

**Run all tests**:
```bash
cd client
python3 audit_strategies.py       # Code matches strategy files
python3 test_strategy_engine.py   # Must pass before live play
python3 test_postflop.py value_maniac
python3 eval_strategies.py
```

## Architecture

### Live Code Path (helper_bar.py)
```
F9 → screenshot → vision_detector_lite.py (GPT-5.2)
                         ↓
                   table_data (cards, board, pot, to_call)
                         ↓
                  strategy_engine.py
                    - Determines facing (none/open/3bet) from to_call
                    - Calls preflop_action() or postflop_action()
                         ↓
                   poker_logic.py
                    - analyze_hand() - card-based analysis
                    - Hand evaluation
                    - Strategy-specific ranges
                         ↓
                   action + reasoning
```

### Key Logic: analyze_hand()
```python
# poker_logic.py - NEW
def analyze_hand(hole_cards, board):
    """Compute all hand properties directly from cards."""
    return {
        'is_pocket_pair': ...,
        'is_overpair': ...,
        'has_top_pair': ...,
        'has_good_kicker': ...,
        'has_two_pair': ...,
        'two_pair_type': ...,  # pocket_over_board, pocket_under_board, etc.
        ...
    }
```

### Key Logic: Two Pair Types
```python
# Determines how to play two pair on paired boards
'pocket_over_board'    # KK on JJ = STRONG (raise)
'pocket_under_board'   # 66 on JJ = WEAK (fold to big bet)
'both_cards_hit'       # A7 on A72 = STRONG (raise)
'one_card_board_pair'  # K2 on K22 = depends on board pair rank
```

## UI Features

- **Borderless**: No Windows title bar
- **Draggable**: Click top bar to move
- **Edge Resize**: Drag any edge/corner
- **Position Selector**: 6 buttons (UTG/MP/CO/BTN/SB/BB)
- **Hotkeys**: F9=Advice F10=Bot F11=Stop F12=Hide

### Strategy-Specific Postflop
| Strategy | Style | Key Differences |
|----------|-------|-----------------|
| value_maniac | Overbets + protection | Uses analyze_hand(), paired board protection |
| value_max | Equity-based | Uses analyze_hand(), pot odds decisions |
| gpt3/gpt4 | Board texture aware | Small c-bets (25-35%) on dry boards |
| sonnet/kiro_optimal | Big value bets | 75-85% pot sizing, overpair logic |
| aggressive/2nl_exploit | Sonnet postflop | Wider ranges, falls through to default |

### Latest Results (100k hands x 3 trials, realistic 2NL table)
Table: 60% fish, 25% nit, 15% tag

| Rank | Strategy | BB/100 | StdDev |
|------|----------|--------|--------|
| 1 | kiro_optimal | +38.64 | 16.22 |
| 2 | kiro5 | +38.30 | 3.31 |
| 3 | maniac | +34.38 | 15.83 |
| 4 | value_maniac | +20.74 | 5.20 |
| 5 | gpt4 | +19.73 | 13.11 |
| 6 | value_lord | +18.86 | 5.67 |
| 7 | value_max | +16.20 | 8.38 |
| 8 | sonnet_max | +12.31 | 5.07 |
| 9 | sonnet | +9.79 | 23.22 |
| 10 | 2nl_exploit | +9.36 | 14.18 |
| 11 | kiro_v2 | +7.11 | 7.37 |
| 12 | tag | +4.30 | 0.84 |
| 13 | gpt3 | +3.86 | 13.07 |
| 14 | aggressive | +1.68 | 5.74 |
| 15 | nit | -1.19 | 1.83 |
| 16 | fish | -2.26 | 4.42 |
| 17 | lag | -5.40 | 2.82 |

## Session Log

### Session 43 Part 14 (January 15, 2026)
- **NEW TOOL: eval_deep.py** - Deep strategy evaluation with real poker metrics
  - Simulates all 169 hands × 6 positions to calculate VPIP/PFR/Gap
  - Calculates postflop AF from real session logs (831 hands)
  - Compares strategy to industry benchmarks (fish/nit/TAG/LAG)
  - Shows position breakdown (UTG tight → BTN loose)
- **INDUSTRY BENCHMARKS**: Added real poker stats from winning players
  - TAG (winner): VPIP 21%, PFR 18%, Gap 3%, AF 2.5
  - LAG: VPIP 28%, PFR 25%, Gap 3%, AF 3.5
  - Fish: VPIP 56%, PFR 5%, Gap 51, AF 0.5
- **value_lord PROFILE**: Plays like a LAG (Loose-Aggressive)
  - VPIP 31.8%, PFR 21.7%, Gap 10.1%, AF 3.34
  - BB Defense 44.4% (good, target 35-45%)
  - Looser than optimal TAG but aggressive - profitable at 2NL

### Session 43 Part 13 (January 15, 2026)
- **CRITICAL POSTFLOP BUG FIX**: Postflop was always using `to_call=0`!
  - Bug: helper_bar.py reused preflop loop (forces to_call=0) for postflop
  - Result: Said CHECK when facing $0.55 bet (should be FOLD)
  - Fix: Postflop now calls engine.get_action() directly with real to_call
- **BB DEFENSE IN LINE 1**: BB now shows defense threshold instead of CHECK
  - AA → BB:CALL any
  - JJ → BB:CALL 6bb
  - T9s → BB:CALL 3bb
  - 72o → BB:FOLD
- **MIN-RAISE THRESHOLDS**: Marginal hands can call min-raises
  - K8o → CALL up to 2.5bb (was FOLD)
  - A5o → CALL up to 3bb (was FOLD)
- Commits: 7260047, 38a9196

### Session 43 Part 12 (January 15, 2026)
- **C-BET LEAK FIX**: Don't c-bet air on monotone/paired boards
  - Analyzed session_20260115_001232.jsonl - found 7 leaks at 10NL/25NL
  - KJh on As4s6s (monotone) → now checks instead of c-bet bluff
  - A3h on 4d4c6h (paired) → now checks instead of c-bet bluff
  - AKc on 4s8d8h (paired) → now checks instead of c-bet bluff
- **STRAIGHT KICKER BUG FIX**: Was using max card, not high card of straight
  - JJ on 6-7-8-9-T showed 51% equity (wrong!)
  - Fixed: now correctly finds J-high straight, equity = 95.5%
  - Only QJ (8 combos) beats JJ when hero blocks 2 Jacks
- **RESULTS**: value_lord +761.0, 0 bad folds, 0 bad calls
- Commits: 236e4a5, 71fa348

### Session 43 Part 11 (January 14, 2026)
- **LINE 1 FIX**: Always shows open ranges regardless of actual game state
  - Bug: K9o on BTN showed FOLD when someone raised (should show RAISE for open range)
  - Fix: Force `to_call=0` when generating Line 1 position actions
  - Line 1 = "what to do if first to act" (open ranges)
  - Line 2 = "vs raise" (call thresholds) - unchanged
- Commits: [pending]

### Session 43 Part 10 (January 14, 2026)
- **STRATEGY AUDIT EXPANDED**: Added tests for gpt4, sonnet postflop behaviors
  - gpt4: TPTK 2 streets (bet flop/turn, check river), TPWK bet once
  - sonnet: specific sizing, middle pair call once, bottom pair fold
- **SONNET BOTTOM PAIR FIX**: Strategy file says "check-fold", code was calling
  - Added `has_bottom_pair` check in `_postflop_sonnet()`
- **FULL HOUSE BUG FIX**: Board trips + hero pocket pair wasn't detected
  - 55 on AAA was "two pair" instead of "full house"
  - Added `board_trips and is_pocket_pair` detection
- All 43 audit tests pass, 9/9 full house scenarios pass
- Commits: [pending]

### Session 43 (January 14, 2026)
- **PREFLOP UI VALIDATION**: Verified all preflop advice matches strategy
  - Line 1 (6 positions): 1014/1014 scenarios PASS
  - Line 2 (vs raise): 1014/1014 scenarios PASS
  - All open/call/3bet/4bet ranges match strategy file
- **CLEARER VS RAISE WORDING**: Simplified call threshold messages
  - `CALL any` - AA, KK, AKs, AKo
  - `CALL up to 15bb` - JJ, TT, 99, AQs, KQs
  - `CALL up to 4bb` - suited connectors, broadways
  - `FOLD` - open-only hands (was confusing "open only, fold vs raise")
- **MULTI-STAKES SUPPORT**: Vision extracts big_blind from window title
  - Thresholds use relative BB (not hardcoded $0.02)
  - Default BB changed to 0.05 (5NL)
- **BOTTOM PAIR FIX**: Detection now uses board halves
  - A3 on 326KJ correctly detected as bottom pair
  - River fold logic for bottom/middle pair
- Commits: d7f2fdc

### Session 40 (January 14, 2026)
- **FIRST LIVE SESSION**: 141 hands with value_maniac strategy
- **RESULTS**: Strategy validated in real play
  - Actions: Fold 36% | Bet 32% | Raise 16% | Call 13% | Check 3%
  - Big wins: JJ (~$10), Set 4s (~$8), Quads 2s (~$7), Trip As (~$4)
  - Overbets with pairs consistently getting paid
- **KEY HANDS**:
  - JJ called 4-bet, c-bet A-high flop, called all-in → WON
  - 44 flopped set, overbet turn/river → WON ~$8
  - 22 flopped QUADS → WON ~$7
  - QJ two pair on J88 - advised raise $13.67, user correctly skipped (risky)
- **CORRECT FOLDS**: KJ vs $14.55 all-in, AK vs $7.46 all-in, 99/AKo vs 4-bets
- **VALIDATION**: value_maniac overbets extract max value from 2NL fish

### Session 39 (January 14, 2026)
- **EVAL FRAMEWORK FIX**: Fixed eval_strategies.py to use hand strength instead of equity
  - Bug 1: `is_value_hand` compared int to string (always True)
  - Bug 2: `has_any_pair` counted board pairs as hero pairs
  - Fix: Bad fold detection now uses hand strength + bet size categories
- **POKER_LOGIC FIXES**:
  - `is_big_bet`: Changed from absolute BB (10+) to pot-relative (50%+ pot)
  - River defense: Overpairs call up to 100% pot (was 20 BB)
  - Nut flush draw: Includes King when Ace not on board
- **BAD FOLD LOGIC**: Now matches strategy thinking
  - Set+: Bad fold if facing <100% pot
  - Two pair: Bad fold only if facing <50% pot
  - One pair: Always good fold (can fold to aggression)
- **RESULTS**: value_maniac 0 bad folds, 0 bad calls, +461.5 score
- Commits: be3b885, eb15d51

### Session 38 (January 13, 2026)
- **EQUITY VS RANDOM BUG FIX**: Fundamental fix for river defense
  - Bug: Equity vs random hands was used for facing bets (villain's range is never random)
  - Fix: Use hand strength + pot-relative bet sizing for river defense
- **CONSERVATIVE DRAW THRESHOLDS**: Applied across all strategies
  - Nut flush draw: 41% pot odds (implied odds at 2NL)
  - Non-nut flush draw: 25%
  - OESD: 22%
  - Gutshot: 12%
- **NUT FLUSH DRAW DETECTION**: Added `is_nut_flush_draw` to `analyze_hand()`
- **DISASTER HAND NOW FOLDS**: AQ TPGK vs 44 BB river bet correctly folds (saves 100 BBs)
- **RESULTS**: audit_strategies.py 21/21 PASS
- Commits: 335d3a4, 990f95d

### Session 37 (January 13, 2026)
- **EVAL_STRATEGIES POSITION FIX**: Preflop now uses neutral position cycling
  - Was defaulting to BTN for all hands (biased results)
  - Now cycles through UTG/MP/CO/BTN/SB/BB for fair average
- **POSITION RANGE VERIFICATION**: Confirmed code matches strategy files
  - value_maniac: UTG 34 hands → BTN 94 hands (matches file exactly)
  - gpt4: UTG 16 hands → BTN 68 hands (matches file exactly)
  - Both advice (strategy_engine.py) and sim (poker_sim.py) use position correctly
- **RESULTS**: value_maniac +23.5 BB/100, value_max +10.3 BB/100 (32 bad folds)
- Commits: [pending]

### Session 36 (January 13, 2026)
- **COMPLETE analyze_hand() REFACTOR**: Eliminated ALL string matching on `desc`
  - Extended analyze_hand() with: `has_middle_pair`, `has_bottom_pair`, `has_flush_draw`, `has_flush`, `has_straight_draw`, `has_straight`
  - Refactored `_postflop_gpt()`, `_postflop_sonnet()`, `_postflop_sonnet_max()`, `count_outs()`
  - Refactored ALL archetypes (fish, nit, tag, lag, maniac)
- **SONNET_MAX BUG FIX**: Was never raising with strong hands (sets/flushes)
  - Changed from `return ('call', ...)` to proper raise logic for strength >= 4
  - Now shows 13 raises in eval_strategies.py (was 0)
- **STRATEGY COVERAGE**: Added missing strategies to eval_strategies.py and poker_sim.py
  - Added: kiro5, kiro_v2, kiro_optimal, 2nl_exploit
- **RESULTS**: 
  - grep "in desc": 0 matches (all string matching eliminated)
  - audit_strategies.py: 21/21 PASS
  - test_strategy_engine.py: 54/55 PASS (1 random float expected)
- Commits: [pending]

### Session 35 (January 13, 2026)
- **ANALYZE_HAND() REFACTOR**: No more string matching on descriptions
  - Created `analyze_hand()` function - computes hand properties from cards
  - Returns: is_pocket_pair, is_overpair, has_top_pair, has_two_pair, two_pair_type, etc.
  - Refactored value_maniac and value_max postflop to use it
- **TWO PAIR TYPES**: Critical for paired board decisions
  - `pocket_over_board`: KK on JJ = STRONG (raise)
  - `pocket_under_board`: 66 on JJ = WEAK (fold to big bet)
  - `both_cards_hit`: A7 on A72 = STRONG (raise)
  - `one_card_board_pair`: K2 on K22 = depends on board pair rank
- **AUDIT_STRATEGIES.PY**: 21 tests verifying code matches strategy files
- **POKERSTRATEGY_VALUE_MANIAC**: Created strategy file for documentation
- **RESULTS**: value_maniac +41.12 BB/100 (now #1 in simulation)
- Commits: [pending]

### Session 34 (January 13, 2026)
- **PREFLOP FACING BUG FIX**: Critical fix for live play
  - Bug: `facing_raise` flag from vision was unreliable
  - K8s/J7s were folding from BTN when first to act (should raise)
  - Fix: Use `to_call` amount as sole indicator of facing
  - `to_call <= 0.02` = no raise = use OPEN ranges
- **TEST_STRATEGY_ENGINE.PY**: 55 tests for live code path
  - Tests vision → strategy_engine → poker_logic pipeline
  - Catches bugs that simulations miss (they bypass strategy_engine)
- **PAIRED BOARD LOGIC**: HIGH vs LOW board pairs
  - HIGH (T, J, Q, K, A): Check/fold - villain likely has trips
  - LOW (2-9): Value bet normally
- **CALL_OPEN_IP EXPANDED**: Added AQo, AJo, ATo, KQo, KJo, QJo
- **RESULTS**: value_maniac +23.5 BB/100 on 943 real hands
- Commits: d2b6658, f73638d, 50bf9d6, 6be75a8

### Session 33 (January 13, 2026)
- **POSTFLOP EDGE CASE TESTER**: Created test_postflop.py with 67 scenarios
  - Covers: quads, full house, sets, two pair, overpairs, underpairs, draws
  - Strict issue detection: monsters should raise, draws should semi-bluff
  - Usage: `python3 test_postflop.py [strategy_name]`
- **VALUE_MAX LEAK FIX**: Replaced exploitative facing-bet logic with equity-based
  - Old: Fixed thresholds assumed "big bet = strong hand" (loses vs maniacs)
  - New: Call if equity > pot_odds, fold otherwise
  - 8 leaks fixed (KK/JJ underpair, two pair, TPWK all folding 64-82% equity)
- **STRATEGY COMPARISON**:
  - value_max: 0 issues (passes all 67 scenarios)
  - value_maniac: 11 issues (passive with monsters, bad river calls)
  - gpt4: 17 issues (just calls monsters, folds +EV draws)
  - sonnet: 16 issues (passive with strong hands)
- **UI CLEANUP**:
  - Removed left sidebar (hotkeys now in startup log)
  - Doubled right panel width to 800px
  - Borderless window with edge resize
  - Default height 440px
- Commits: 3bd86f6, 73a97cb, 3a62c2a

### Session 32 (January 13, 2026)
- **POSTFLOP EQUITY UI**: Added real-time equity display to helper bar
  - `calculate_equity()`: Monte Carlo simulation (500 iterations)
  - `count_outs()`: Counts flush (9), OESD (8), gutshot (4), pair improvement (5)
  - `get_hand_info()`: Returns equity, outs, draws, pot_odds
  - UI shows: "Win: 67.6% | Outs: 9 (flush) | Odds: 33.3%"
  - Session logs now include equity, hand_desc, draws, outs, pot_odds
- **14-HAND SESSION ANALYSIS**: Found issues with current postflop logic
  - Qd2d on 4s4c6d: Missed flush draw (3 diamonds), said "high card"
  - 44 on 789-5: Has set + OESD, said "bottom pair"
  - Ad3s on QK2: Has gutshot, said "no equity"
- Commits: 5d2f3d8, bfd6b55

### Session 31 (January 13, 2026)
- **SMART POSTFLOP FIXES**: Analyzed 245-hand session log, found critical bugs
  - Fixed board pair detection (AJ on Q22 was "pair", now "high card")
  - Fixed top pair weak kicker (was potting, now 40% flop only then check)
  - Added pot odds calculation for calling decisions
  - C-bet only on dry boards or with equity (not 80% with air)
- **RESULTS**: value_max now #1 at +46.82 BB/100 (was +38)
  - Beats maniac (+46.82 vs +39.15) - smart > blind aggression
  - Lowest variance (StdDev 2.59)

### Session 30 (January 12, 2026)
- **VALUE_MAX OPTIMIZATION**: Analyzed why maniac beats all bots
  - Compared defense: maniac calls any pair, value_max was folding
  - Updated value_max with maniac's preflop ranges
  - Updated value_max postflop to bet bigger (100-120% pot)
  - Updated value_max to call any pair when facing bet
  - Result: value_max now matches maniac (+41-55 BB/100)
- **SIMULATION FIX**: Changed random.seed to None for fresh results each run
- **SIMULATION IMPROVEMENTS**: Based on real 162-hand session analysis
  - Added maniac archetype (overbets 100%+ pot, wide 3-bets)
  - Fish now limp 30% of weak hands, 60% limp-call raises
  - Maniacs use variable 3-bet sizing (3x-5x)
  - Updated player distribution: 30% fish, 20% TAG, 15% nit, 20% LAG, 15% maniac
- **STRATEGY CLEANUP**:
  - Added kiro5 and kiro_v2 to simulator (8 bot strategies total)
  - Created pokerstrategy_aggressive file
  - Removed pokerstrategy_gpt2 (unused)
- **OVERPAIR FIX**: Fixed detection bug (AA on 789 was "top pair weak kicker")
- **2NL_EXPLOIT STRATEGY**: Wider 3-bet calling range
- Commits: 3b98235, a81cbd7, 2be7d0d, 1d21090, 9118ec2

### Session 30 Earlier (January 12, 2026)
- **STRATEGY ANALYSIS**: Comprehensive 162-hand session analysis
  - Identified 3-bet defense leak (folding too many hands)
  - Created 2nl_exploit strategy with wider call_3bet range
  - Fixed overpair detection bug (AA on 789 was "top pair weak kicker")
  - Added overpair/underpair handling to _postflop_gpt()
- **OVERPAIR FIX**: +1.78 BB/100 improvement after fix
  - evaluate_hand() now detects overpairs (QQ on J85)
  - evaluate_hand() now detects underpair to ace (KK on Axx)
  - _postflop_gpt() bets 65/60/50% pot with overpairs
  - Underpair to ace: check-call flop, fold to big bets
- **2NL_EXPLOIT STRATEGY**: New strategy for 2NL exploitation
  - Wider 3-bet calling: QQ-88, AQs, AQo, AJs, KQs
  - Uses sonnet postflop (falls through to default)
  - Created pokerstrategy_2nl_exploit file
- **SIMULATION RESULTS**: sonnet leads at +33.15 BB/100
- Commits: faabb0e, 7b80d02

### Session 29 (January 12, 2026)
- **ARCHITECTURE FINALIZED**: Strategy engine is now the default ⭐
  - vision_detector_lite.py: gpt-4o-mini → gpt-5.2
  - helper_bar.py: Inverted mode logic (strategy_engine default)
  - Command line args: --ai-only and --strategy <name>
  - UI labels: Show current mode (AI ONLY vs Vision + Strategy)
- **NEW DEFAULT**: GPT-5.2 vision → strategy_engine → Decision
- **AI-ONLY MODE**: GPT-5.2 does both vision + decision (old behavior)
- **RATIONALE**: Strategy engine gives control, GPT-5.2 vision is 96.9% accurate
- Commits: [pending]

### Session 28 (January 12, 2026)
- **GROUND TRUTH COMPLETE**: Built 50-screenshot verified dataset ⭐
  - Manual verification of 50 diverse screenshots (preflop/flop/turn/river)
  - Automated comparison: GPT-5.2 vs Kiro-server
  - **GPT-5.2 WINS**: 91% card accuracy vs Kiro's 61%
  - **Production recommendation**: Use GPT-5.2 for vision
  - Card errors: Kiro confuses suits (♠ vs ♣, ♥ vs ♦) - 17 errors
  - Board detection: GPT-5.2 100%, Kiro 87.5%
  - Position detection: Both fail (44-50%) - don't use in production
  - Pot detection: Both perfect (100%)
  - Files: ground_truth.json (50 entries), compare_with_ground_truth.py
- **PROJECT CLEANUP COMPLETE**: Removed 14 temporary files ✅
  - Deleted: FIXES_PLAN.md, PROMPT_UPDATE_SUMMARY.md, all /tmp analysis files
  - Kept: Core docs (AGENTS/AmazonQ/README), testing infrastructure, all code
  - Created: CLEANUP_PLAN.md documenting final structure
- **REPOSITORY CONSOLIDATION**: Merged server/ into main repo ⭐
  - Was in separate onyxpoker-server/ folder (confusing!)
  - Now everything in ONE place: /onyxpoker/
  - Server code now tracked in GitHub
  - Systemd service updated to new location
- **KIRO VISION INTEGRATION**: Kiro CLI now does vision analysis directly ⭐
  - Added /analyze-screenshot endpoint (sends image to kiro-cli)
  - Added /validate-state endpoint (validates poker states)
  - Architecture: Screenshot → Kiro CLI vision → Poker state
  - Comprehensive debug logging on client and server
  - Fixed: Include image path in prompt (not --image flag)
- **KIRO CLI SPEED OPTIMIZATION**: 66% faster with model tuning + prompt simplification ⚡
  - Fixed model name: claude-haiku-4 → claude-haiku-4.5 (12.7s → 5.9s)
  - Simplified prompt with JSON example (5.9s → 4.3s)
  - Speed: 12.7s → 4.3s (66% improvement)
  - Breakdown: 99.9% time in Kiro CLI, 0.01s server overhead
  - Model selection + prompt design critical for performance
- **VISION PROMPT IMPROVEMENT**: Improved prompt with detailed suit/position detection
  - Added explicit suit symbol descriptions (♠♥♦♣)
  - Added step-by-step position detection (count clockwise from button)
  - Added common mistake warnings (hallucination, suit confusion)
- **GROUND TRUTH INFRASTRUCTURE**: Created ground_truth.json with 11 screenshots
  - compare_with_ground_truth.py for automated accuracy testing
  - Fixed K♠ to K♣ suit errors in ground truth
- **GPT-5 MODEL TESTING**: Comprehensive testing of 7 models
  - **gpt-5.2**: 100% cards, 91% board ⭐ BEST
  - **gpt-5.1**: 75% cards, 82% board (good alternative)
  - **gpt-4o**: 75% cards, 64% board
  - **gpt-5-mini**: 62.5% cards, 60% board (kept for testing)
  - **Removed from testing**: gpt-5, gpt-5-nano, gpt-4o-mini (too unreliable)
- Commits: 2fcf2fa, 636e0dd, 609d1df, d353009, c84d71f, d81145c, d3fd49a, b618d09, 7aa46e7, 2f811d9, 377818f, 0647033, 4fa2ff5, 260a9a9, 766ac7e

### Session 27 (January 12, 2026)
- **STRATEGY-SPECIFIC POSTFLOP**: Each bot strategy now uses its own postflop logic
  - gpt3/gpt4: Board texture aware, smaller c-bets on dry boards (25-35%)
  - sonnet/kiro_optimal: Bigger value bets (75-85%), overpair logic
- **Added postflop to pokerstrategy_gpt3**: Was preflop only, now has full postflop
- **Fixed pocket pair below ace**: KK on Axx = check-call (not bet)
- **Architecture**: `postflop_action()` now takes `strategy=` param for bot-specific logic
- **Results**: sonnet/kiro_optimal outperform gpt3/gpt4 due to bigger value bets
- Commits: 9a8b2b1, 85e713c

### Session 27 Earlier (January 12, 2026)
- **FULL POSTFLOP SIMULATION**: Rewrote poker_sim.py to deal actual boards
- **ARCHETYPE POSTFLOP**: fish/nit/tag/lag have distinct postflop behavior
- **FIXED TPTK**: Now calls 2-3 streets per strategy files (was folding turn)
- **LITE MODE**: Created vision_detector_lite.py + strategy_engine.py pipeline
- Commits: 996e3f8, 1fc49fc

### Session 26 (January 12, 2026)
- **STRATEGY SIMULATOR**: Built poker_sim.py to compare preflop strategies
- **8 STRATEGY FILES ANALYZED**: Ranked from best to worst for Blitz 6-max
- **4 PLAYER ARCHETYPES CREATED**: fish, nit, lag, tag
- Commits: 665ddcf, 81088eb

### Session 22 (January 9, 2026)
- **INFRASTRUCTURE CLEANUP**: Removed redundant old server
- Stopped and disabled onyxpoker.service (old Flask API server)
- Only kiro-server.service running now (Kiro analysis server on port 5001)

### Session 21 (January 8, 2026)
- **CRITICAL FIX**: JSON schema field name mismatch causing 100% strategy parsing failures
- Fixed: `recommended_action` → `action` in JSON schema
- Fixed: `hero_position` → `position` in JSON schema  
- Fixed: helper_bar.py and test_screenshots.py field references
- All files now use consistent field names matching existing logs
- Commits: 917336f, c66efe3, e83bee3

### Session 20 (January 8, 2026)
- **MAJOR BREAKTHROUGH**: Position detection bug found and fixed
- Only detecting BTN/SB/BB (missing UTG/MP/CO) - 65.9% hands marked as BTN
- Added position-specific ranges: UTG tight, CO medium, BTN wide
- Strategy optimization: aggressive value betting (75-100% pot sizing)
- Monster hands (full house+) must jam for maximum value
- Expected win rate improvement: +4-6bb/100 from position + value betting fixes
- Commit: 1cdec55

### Session 16 (January 8, 2026)
- Analyzed 70 hands - 97% accuracy (68/70 correct)
- Fixed: Draw verification (J7 on TQ4 = gutshot, not OESD)
- Fixed: Pre-action advice now gives specific call/raise ranges
- Wheel straight detection working correctly (A2 on 5QT43)
- Suited/offsuit detection working
- Commit: 3fe19ad

### Session 15 (January 8, 2026)
- Analyzed 6 hands - 67% accuracy (4/6 correct)
- Fixed: Straight hallucination (A2 on 564 ≠ wheel)
- Fixed: Suited/offsuit detection (A♠2♦ = offsuit)
- Commit: 25ba336

### Session 14 (January 8, 2026)
- Fixed: Weak aces/kings OOP folding
- Fixed: Multiway pot tightening
- Commit: e6ee88e

### Session 13 (January 8, 2026)
- Added screenshot saving to helper_bar.py (auto-saves to client/screenshots/)
- Created test_screenshots.py for offline testing
- Built Kiro analysis server (Flask app on port 5001)
- Added send_to_kiro.py client script
- Fixed AWS security group (opened port 5001)
- Fixed confidence NameError bug in helper_bar.py
- Added session logging (JSONL format) to client/logs/
- Added send_logs.py to upload logs for analysis
- Analyzed 33 live screenshots - 100% detection accuracy
- User can now send screenshots from Windows to Linux server for analysis

### Session 12 (January 8, 2026)
- Restored agent files deleted in previous session
- Created helper_bar.py (new simplified UI)
- Cleaned up old files (poker_gui.py, mini_overlay.py, etc.)
- Deleted poker_reader.py, config.py (not needed)
- Consolidated AGENTS.md with all learnings

### Session 11 (December 31, 2025)
- Switched to gpt-5.2 (2-3x faster)
- Fixed timing calculation
- Cleaned up logs

### Session 9-10 (December 29-30, 2025)
- Implemented GPT-4o vision (replaced OpenCV)
- Fixed Windows encoding issues (no emojis)
- Created unified GUI with hotkeys

## Future Plans

### Session Results Aggregator (Not Yet Built)
Different from eval_strategies.py which tests strategy decisions on logged hands.

**What it would do**:
- Parse session logs to extract ACTUAL money won/lost per hand
- Calculate real BB/100 win rate across multiple sessions
- Compare live results vs simulation predictions (+41 BB/100)
- Track win rate over time (is it improving? variance?)

**Why it's different from eval**:
- eval_strategies.py: "Would this strategy make the RIGHT decision on this hand?"
- Aggregator: "How much money did we ACTUALLY win/lose playing these hands?"

**Data needed** (not currently logged):
- Hand result (won/lost/folded)
- Final pot size when won
- Amount lost when called and lost

**When to build**: After 500+ live hands to have meaningful sample size.

---

## Technical Details

- **Model**: gpt-5.2 (configurable in vision_detector.py)
- **Speed**: 6-9 seconds per analysis
- **Cost**: ~$2 per 1000 hands
- **Accuracy**: 95%+ on clear screenshots

## File Structure

```
client/
  helper_bar.py      # Main UI
  vision_detector.py # GPT-5.2 API
  test_screenshots.py # Offline testing
  send_to_kiro.py    # Send screenshots to server
  send_logs.py       # Send session logs to server
  requirements.txt
  screenshots/       # Auto-saved screenshots
  logs/              # Session logs (JSONL)
server/              # Kiro analysis server
  kiro_analyze.py    # Flask endpoint
docs/                # API.md, DEPLOYMENT.md
```
