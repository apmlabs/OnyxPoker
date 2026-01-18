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
    GPT-5.2 Vision (vision_detector_lite.py or vision_detector_v2.py)
         ↓
   Strategy Engine (strategy_engine.py)
         ↓
   poker_logic.py
     ├── analyze_hand() - Card-based hand analysis (strength, desc, all flags)
     ├── preflop_action() - Position-based ranges
     └── postflop_action() - Strategy-specific logic
         ├── value_maniac: Wide ranges, overbets, paired board protection
         ├── value_lord: Conservative c-betting, aggressive value betting
         ├── value_max: Smart aggression with pot odds
         ├── gpt3/gpt4: Board texture aware
         └── sonnet: Big value bets
         ↓
   Decision + Reasoning
         ↓
    Helper Bar UI (advice display + opponent stats in V2 mode)
```

### V2 Vision Mode (Session 58)
```bash
python helper_bar.py --visionv2
```
- Detects player names from screenshots
- Looks up stats from player_stats.json
- Classifies archetypes (fish/nit/lag/tag/maniac)
- Shows actionable advice per opponent in sidebar

### Default Strategy: `value_lord` (switched Session 46)
- +24.1 BB/100 in PokerKit simulation (20k hands)
- More conservative c-betting than value_maniac
- Aggressive value betting extracts more from fish
- Good balance of aggression and discipline

### Key Design Principles
1. **Single source of truth**: All hand analysis uses `analyze_hand()` which computes properties directly from cards - NO string matching on descriptions
2. **Strategy files are truth**: Code must match pokerstrategy_* files exactly
3. **Test the live path**: Simulations test poker_logic.py directly, but live play goes through strategy_engine.py

### Client-Server Architecture
**Windows Client** (C:\aws\onyx-client\)
- User runs helper_bar.py
- Screenshots taken locally
- `send_logs.py` uploads to server

**EC2 Server** (54.80.204.92:5001)
- Receives uploads at POST /logs
- Stores in /home/ubuntu/mcpprojects/onyxpoker/server/uploads/

---

## 📁 FILE STRUCTURE

```
onyxpoker/                    # Main repo (GitHub: apmlabs/OnyxPoker)
├── AGENTS.md                 # Permanent knowledge (NEVER DELETE)
├── AmazonQ.md                # Current state + history (NEVER DELETE)
├── README.md                 # Quick start (NEVER DELETE)
├── idealistslp_extracted/    # Real PokerStars hand histories (1422 hands)
│   └── HH*.txt               # Raw hand history files from live play
├── client/
│   ├── helper_bar.py         # Main UI (F9=advice, F10=bot, F11=stop, F12=hide)
│   ├── vision_detector.py    # Full mode: gpt-5.2 for vision + decisions
│   ├── vision_detector_lite.py # Lite mode: gpt-5.2 for vision only
│   ├── strategy_engine.py    # Applies strategy (default: value_lord)
│   ├── poker_logic.py        # Hand eval, preflop/postflop logic, strategies + archetypes
│   ├── poker_sim.py          # Monte Carlo simulator (200k+ hands)
│   ├── pokerkit_adapter.py   # PokerKit simulation with external engine
│   │
│   │ # === ANALYSIS (on hand histories: idealistslp_extracted/*.txt) ===
│   ├── analyse_real_logs.py  # Main HH analysis (--big N, --strategy X, --detailed)
│   ├── analyze_table_composition.py  # Classifies players into archetypes
│   ├── analyze_archetype_behavior.py # Real vs simulated postflop behavior
│   ├── analyze_bet_sizes.py          # Real bet sizes by archetype
│   │
│   │ # === EVALUATION (on session logs: server/uploads/*.jsonl) ===
│   ├── eval_strategies.py    # Evaluates on session logs (good/bad folds)
│   ├── eval_deep.py          # Deep stats (VPIP/PFR/AF)
│   │
│   │ # === TESTS ===
│   ├── audit_strategies.py   # Strategy file vs code (30 tests)
│   ├── test_strategy_engine.py # Live code path (55 tests)
│   ├── test_postflop.py      # Edge cases (67 tests)
│   ├── test_poker_rules.py   # Poker rules (24 tests)
│   │
│   └── pokerstrategy_*       # Strategy definition files (16 files)
├── server/
│   ├── kiro_analyze.py       # Flask server on port 5001
│   └── uploads/              # Session logs + screenshots
└── docs/
    └── DEPLOYMENT.md         # Setup guide
```

---

## 🧪 TESTING FRAMEWORK

### 1. Strategy Audit (`audit_strategies.py`)
Verifies code matches strategy file descriptions.

```bash
cd client && python3 audit_strategies.py
```

**Tests 30 scenarios:**
- Preflop ranges (open, 3bet, 4bet)
- Postflop value betting
- Paired board handling (KK on JJ vs 66 on JJ)
- Two pair strength detection
- gpt4/sonnet specific behaviors

**Target: 30/30 PASS**

### 2. Live Code Path Testing (`test_strategy_engine.py`)
Tests the ACTUAL code path used in live play (helper_bar.py).

```bash
cd client && python3 test_strategy_engine.py
```

**Why this matters:**
- poker_sim.py and eval_strategies.py call poker_logic.py DIRECTLY
- Live play goes: vision → strategy_engine.py → poker_logic.py
- Bugs in strategy_engine.py are INVISIBLE to simulations!

**Tests 55 scenarios:**
- Preflop facing detection (none/open/3bet/4bet)
- Buggy vision handling (facing_raise=True but to_call=0)
- Position-specific ranges
- Postflop action selection
- Edge cases (None values, invalid positions)

**MUST PASS before live play!**

### 3. Poker Rules Verification (`test_poker_rules.py`)
Verifies simulation follows actual Texas Hold'em rules.

```bash
cd client && python3 test_poker_rules.py
```

**Tests 24 scenarios:**
- Hand rankings (Royal→High Card)
- Hand comparison (higher beats lower)
- Kicker comparison
- Special straights (wheel, broadway)
- Flush/full house detection
- Position order (preflop & postflop)
- Betting mechanics (caps, all-in)
- Showdown (best hand wins, split pots)

### 4. Postflop Edge Cases (`test_postflop.py`)
Tests 67 postflop scenarios for each strategy.

```bash
cd client && python3 test_postflop.py [strategy_name]
```

### 5. Real Hand Evaluation (`eval_strategies.py`)
Evaluates strategies on real hands from session logs.

```bash
cd client && python3 eval_strategies.py
```

**Quality metrics (hand strength based, NOT equity):**
- **Good Folds**: Folding weak hands
- **Bad Folds**: Folding strong hands to small bets
- **Good Calls**: Calling when equity > pot odds
- **Bad Calls**: Calling when equity < pot odds

**Why hand strength, not equity?**
Equity vs random is meaningless when villain bets. A 50% pot bet means villain has something - their range is NOT random.

**Target: BadFolds = 0, BadCalls = 0**

### 6. Monte Carlo Simulation (`poker_sim.py`)
Simulates 200k+ hands against realistic opponent archetypes.

```bash
cd client && python3 poker_sim.py 200000
```

**Table composition** (realistic 2NL, updated Jan 17 2026):
- 12% fish (loose passive)
- 25% nit (ultra tight)
- 39% tag (tight aggressive)
- 23% lag (loose aggressive)
- 1% maniac

### Testing Workflow
1. Make strategy change in `poker_logic.py`
2. Run `audit_strategies.py` → **MUST PASS**
3. Run `test_strategy_engine.py` → **MUST PASS**
4. Run `test_postflop.py` → fix any issues
5. Run `eval_strategies.py` → check real hand performance
6. Run `poker_sim.py 200000` → verify simulation results
7. If all pass, commit changes

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
Simulations (poker_sim.py) and evaluations (eval_strategies.py) call poker_logic.py directly. But live play goes through strategy_engine.py. Bugs in the glue code are invisible to simulations. Created test_strategy_engine.py to catch these.

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

### Common Gotchas

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

**facing_raise from vision unreliable (Session 34):**
```python
# BUG: Vision sometimes returns facing_raise=True when to_call=0
if facing_raise:  # Unreliable!
    facing = 'open'

# FIX: Use to_call as sole indicator
if to_call <= 0.02:
    facing = 'none'  # No raise, use OPEN ranges
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
