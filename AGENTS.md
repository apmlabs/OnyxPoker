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

### System Flow
```
PokerStars/Simulator Window
         ↓ F9 (screenshot active window)
    GPT-5.2 Vision (vision_detector_v2.py default)
         ↓
   Strategy Engine (strategy_engine.py)
         ↓
   poker_logic/              # Refactored package
     ├── card_utils.py      - Constants, parsing, equity calculation
     ├── hand_analysis.py   - analyze_hand(), check_draws() (single source of truth)
     ├── preflop.py         - expand_range(), STRATEGIES, preflop_action()
     ├── postflop_base.py   - Config-driven postflop (kiro/kiro_lord/sonnet)
     ├── postflop_value_lord.py  - Active base strategy (value_lord)
     ├── postflop_the_lord.py    - Active default (wraps value_lord + opponent-aware)
     ├── postflop_inactive.py    - 4 inactive strategies (optimal_stats/value_max/gpt/sonnet_max)
     └── _monolith.py       - postflop_action() dispatcher + archetype simulation handlers
         ├── the_lord: Opponent-aware (default) - adjusts by villain archetype
         ├── value_lord: Conservative c-bet, aggressive value betting
         └── 4 inactive: gpt, sonnet_max, optimal_stats, value_max
         ↓
   Decision + Reasoning
         ↓
    Helper Bar UI (advice display + opponent stats in V2 mode)
```

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

### Memory Reading Architecture (Session 71)

**Goal:** Replace ~5s GPT vision latency with <1ms memory reads.

**Challenge:** Memory offsets change with PokerStars updates. Need auto-calibration.

**Solution:** Use GPT vision as "oracle" to find offsets automatically.

```
Windows (memory_calibrator.py):
  1. F9 pressed (or automatic trigger)
  2. Screenshot + Memory scan (SAME INSTANT)
     - Scan for all card-like values (0-51, 2-14, ASCII)
     - Save: {address: value} for all matches
  3. Send screenshot to GPT-5.2 (~5s)
  4. GPT returns: "Ah Kd" (hero cards)
  5. Correlate: which addresses had Ah=14/0, Kd=13/1?
  6. Log candidate addresses to JSON
  
  After N hands:
  - Addresses that consistently match = stable offsets
  - Save to offsets.json
  - Future reads use offsets directly (<1ms)
```

**Known Offsets (poker-supernova, PokerStars 7 Build 46014):**
```python
OFFSETS = {
    'table': {'hand_id': 0x40, 'card_values': 0x64, 'card_suits': 0x68},
    'seat': {'name': 0x00, 'card_values': 0x9C, 'card_suits': 0xA0}
}
```

**Anti-cheat:** ReadProcessMemory is standard Windows API, undetectable without kernel hooks. PokerTracker uses same approach ("Memory Grabber").

### Memory Calibration v2 (Session 72)

**Problem:** Card values (0-12) are too common - millions of matches in memory.

**Solution:** Use hand_id as unique anchor:
1. GPT reads `hand_id` (12-digit number) from screenshot
2. Scan memory for hand_id - essentially unique
3. Explore nearby memory for card pattern
4. Track across hands until stable

```
Flow:
  F9 → Screenshot → GPT returns {hand_id, hero_cards}
                  → Scan for hand_id bytes
                  → Check nearby memory for [r1, r2, ?, ?, s1, s2]
                  → Track candidates across hands
                  → Save stable address to memory_offsets.json
```

**Files:**
- `memory_calibrator.py` - Auto-calibration using hand_id anchor
- `memory_offsets.json` - Saved calibration (card address)
- `memory_tracking.json` - Candidate tracking across hands

---

## 📁 FILE STRUCTURE

```
onyxpoker/                    # Main repo (GitHub: apmlabs/OnyxPoker)
├── AGENTS.md                 # Permanent knowledge (NEVER DELETE)
├── AmazonQ.md                # Current state + history (NEVER DELETE)
├── README.md                 # Quick start (NEVER DELETE)
├── idealistslp_extracted/    # Real PokerStars hand histories (~2300 hands, 47 files)
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
│   ├── memory_calibrator.py  # Auto-find card address using hand_id anchor
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
│   ├── player_stats.json     # 613 players with archetypes + advice
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
| Hand Histories | idealistslp_extracted/*.txt | 47 HH files (~2300 hands) | analyse_real_logs.py, analyze_*.py | Strategy optimization |
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
