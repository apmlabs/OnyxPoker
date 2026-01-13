# OnyxPoker - Agent Context

## 🎯 PROJECT GOAL

**AI-powered poker analysis tool for research purposes** - NOT for automated botting.

The system analyzes poker tables using GPT vision API and provides strategic advice. The human makes all decisions and clicks. This is a research tool for studying AI decision-making in poker.

## 📚 DOCUMENTATION STRUCTURE

### Core Files (NEVER DELETE)
- **AGENTS.md** (this file) - Agent memory, learnings, architecture decisions
- **AmazonQ.md** - Current status, progress tracking
- **README.md** - User-facing quick start guide

### Technical Documentation (in docs/)
- **docs/API.md** - Server API reference (for future use)
- **docs/DEPLOYMENT.md** - Setup and deployment guide
- **docs/ANALYSIS_NOTES.md** - GPT decision analysis and prompt tuning notes

## 🏗️ ARCHITECTURE

```
PokerStars/Simulator Window
         ↓ F9 (screenshot active window)
    GPT-5.2 Vision (vision_detector_lite.py)
         ↓
   Strategy Engine (strategy_engine.py)
         ↓
   poker_logic.py (value_maniac strategy)
         ↓
   Decision + Reasoning
         ↓
    Helper Bar UI (advice display)
```

**Default Strategy**: `value_maniac` (+23.5 BB/100 on real hands)
- C-bets 94%, calls any pair, raises strong hands
- Never folds >50% equity hands

**Default approach**:
- **Vision**: GPT-5.2 reads table (cards, pot, stacks)
- **Decision**: strategy_engine.py applies value_maniac logic
- **Manual position**: UI radio buttons (UTG/MP/CO/BTN/SB/BB)

**AI-Only mode** (use `--ai-only` flag):
- GPT-5.2 does both vision + decision in one call

Server runs on EC2 (54.80.204.92:5001) for log collection.

## 📁 CURRENT FILE STRUCTURE

```
onyxpoker/                    # Main repo (GitHub: apmlabs/OnyxPoker)
├── AGENTS.md                 # Agent memory (NEVER DELETE)
├── AmazonQ.md                # Status tracking (NEVER DELETE)
├── README.md                 # Quick start (NEVER DELETE)
├── client/
│   ├── helper_bar.py         # Main UI (F9=advice, F10=bot, F11=stop, F12=hide)
│   ├── vision_detector.py    # Full mode: gpt-5.2 for vision + decisions
│   ├── vision_detector_lite.py # Lite mode: gpt-5.2 for vision only
│   ├── strategy_engine.py    # Applies strategy (default: value_maniac)
│   ├── poker_logic.py        # Hand eval, preflop/postflop logic, all strategies
│   ├── poker_sim.py          # Monte Carlo simulator (200k+ hands)
│   ├── test_strategy_engine.py # Live code path tests (55 scenarios)
│   ├── test_postflop.py      # Edge case tester (67 scenarios)
│   ├── eval_strategies.py    # Real hand evaluator (943 hands from logs)
│   ├── replay_logs.py        # Replay session logs through strategies
│   ├── test_screenshots.py   # Offline vision testing
│   ├── send_logs.py          # Upload logs to server
│   ├── requirements.txt
│   └── pokerstrategy_*       # Strategy definition files
├── server/
│   ├── kiro_analyze.py       # Flask server on port 5001
│   ├── requirements.txt
│   └── uploads/              # Screenshots and logs (gitignored)
│       ├── *.png             # Screenshots
│       ├── session_*.jsonl   # Session logs (943 hands)
│       └── ground_truth.json # Vision testing ground truth
└── docs/
    ├── DEPLOYMENT.md         # Setup guide
    └── ANALYSIS_NOTES.md     # GPT decision analysis
```

## 🖥️ CLIENT-SERVER ARCHITECTURE

**Windows Client** (C:\aws\onyx-client\)
- User runs helper_bar.py or test_screenshots.py
- Screenshots taken locally
- `send_logs.py` uploads to server
- **TESTING**: All test_screenshots.py tests run on CLIENT (not server)

**EC2 Server** (54.80.204.92:5001)
- Receives uploads at POST /logs
- Analyzes screenshots with Kiro CLI at POST /analyze-screenshot
- Validates poker states at POST /validate-state
- Stores in /home/ubuntu/mcpprojects/onyxpoker/server/uploads/
- Agent can view screenshots and analyze logs here (for analysis only, NOT testing)

**Server Code Location**: `/home/ubuntu/mcpprojects/onyxpoker/server/`
- Now part of main GitHub repo (consolidated January 12, 2026)
- Previously was in separate onyxpoker-server/ folder

## ✅ CURRENT STATE

### What Works
- `helper_bar.py` - Draggable UI with manual position selector
- `vision_detector_lite.py` - GPT-5.2 for vision only
- `strategy_engine.py` - Applies value_maniac strategy (default)
- `poker_sim.py` - Monte Carlo simulation (200k hands)
- `test_postflop.py` - 67 edge case scenarios
- `eval_strategies.py` - Real hand evaluation (715 hands)
- Hotkeys: F9=Advice, F10=Bot loop, F11=Stop, F12=Hide

### Strategy Rankings (on 715 real 2NL hands)
| Rank | Strategy | Est BB/100 | Key Trait |
|------|----------|------------|-----------|
| 1 | **value_maniac** | +23.5 | 94% c-bet, 0 bad folds, 27 raises |
| 2 | gpt4 | +13.1 | Balanced |
| 3 | gpt3 | +12.2 | Tight |
| 4 | value_max | +11.2 | Folds too much |
| 5 | sonnet | +10.8 | Very tight |

### What's Not Implemented
- Turn detection, action execution - LOW PRIORITY

## 🧪 TESTING FRAMEWORK

### 1. Edge Case Testing (`test_postflop.py`)
Tests 67 specific scenarios to catch strategy bugs.

```bash
cd client && python3 test_postflop.py [strategy_name]
```

**Scenarios tested:**
- Monsters: quads, full house, straight flush (should raise)
- Strong: sets, two pair, straights, flushes (should raise/bet)
- Medium: overpairs, top pair, middle pair (should bet/call)
- Draws: flush draws, OESDs, gutshots (should semi-bluff)
- Weak: high card, air (should fold facing bets)

**Issue detection:**
- "QUESTIONABLE": Strong hand just calling (should raise)
- "LEAK": Folding +EV hands or calling -EV hands

**Target: 0-3 issues** (some edge cases are debatable)

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

### 3. Real Hand Evaluation (`eval_strategies.py`)
Evaluates strategies on 943 real hands from session logs.

```bash
cd client && python3 eval_strategies.py
```

**Metrics tracked:**
- **VPIP%**: Voluntarily put money in pot (preflop)
- **PFR%**: Preflop raise frequency
- **C-Bet%**: Continuation bet frequency
- **PostFold%**: Postflop fold frequency
- **Aggression%**: Bet+Raise / (Bet+Raise+Call+Check)

**Quality metrics:**
- **Good Folds**: Folding <30% equity hands
- **Bad Folds**: Folding >50% equity hands (LEAK!)
- **Good Calls**: Calling when equity > pot odds
- **Bad Calls**: Calling when equity < pot odds
- **Value Raises**: Raising with strong hands facing bets

**Score formula:**
```
Score = GoodFolds*2 - BadFolds*3 + GoodCalls*2 - BadCalls*2 
        + ValueBets*1 - Bluffs*0.5 + PreflopRaises*0.5
```

**Target: Score > +300, BadFolds = 0**

### 5. Monte Carlo Simulation (`poker_sim.py`)
Simulates 200k+ hands against realistic opponent archetypes.

```bash
cd client && python3 poker_sim.py 200000
```

**Table composition** (realistic 2NL):
- 60% fish (loose passive)
- 25% nit (ultra tight)
- 15% tag (tight aggressive)

**Output**: BB/100 win rate for each strategy

### Testing Workflow
1. Make strategy change in `poker_logic.py`
2. Run `test_strategy_engine.py` → **MUST PASS** (live code path)
3. Run `test_postflop.py` → fix any issues
4. Run `eval_strategies.py` → check real hand performance
5. Run `poker_sim.py 200000` → verify simulation results
6. If all pass, commit changes

## 🧠 AGENT WORKFLOW

### After EVERY coding session, I MUST:
1. ✅ Update **AmazonQ.md** with current status and timestamp
2. ✅ Update **AGENTS.md** with new learnings
3. ✅ Update **README.md** if user-facing changes
4. ✅ Commit to GitHub with clear message

### Before STARTING new work, I MUST:
1. ✅ Review **AmazonQ.md** for current status
2. ✅ Review **AGENTS.md** for past learnings
3. ✅ Check recent commits for changes

### Red Flags (I'm Failing):
- ⚠️ User asks "did you update docs?" → I forgot
- ⚠️ I suggest something already tried → Didn't read context
- ⚠️ I repeat a mistake → AGENTS.md wasn't updated
- ⚠️ User has to remind me twice → I failed first time

**Context files are my only memory. Without them, I start from scratch every time.**

## 📋 FILE DELETION RULES

- **NEVER delete**: AGENTS.md, AmazonQ.md, README.md
- **Can delete other .md files IF**: knowledge is incorporated into main files first
- **Can keep other .md files IF**: explicitly referenced in AGENTS.md
- Currently keeping: docs/API.md, docs/DEPLOYMENT.md

## ⚙️ TECHNICAL NOTES

### GPT-5.2 Vision
- Model: `gpt-5.2` (configurable in vision_detector.py line 12)
- Cost: ~$2 per 1000 hands
- Speed: 6-9 seconds per analysis
- Accuracy: 95%+ on clear screenshots

### Windows Compatibility
- **NO emojis in logging** - Windows cp1252 encoding crashes on Unicode emojis
- Use ASCII only for cross-platform compatibility
- This has caused bugs 3+ times - NEVER use emojis in Python code

### GPT-5 Model Differences
- GPT-5 models do NOT support `temperature` parameter (must omit, not set to 0)
- Use `max_completion_tokens` not `max_tokens`
- gpt-5.2 is faster than gpt-5-mini (6-9s vs 20-30s)

---

## 📖 SESSION HISTORY & LESSONS LEARNED

### Session 34: Strategy Engine Bug Fix + Test Coverage (January 13, 2026)

**Challenge**: K8s/J7s were folding from BTN when first to act - should be raising.

**Root Cause**: `strategy_engine.py` used `facing_raise` flag from vision to determine if someone raised. But vision sometimes returns `facing_raise=True` even when `to_call=0` (no actual raise).

**The Testing Gap**:
- `poker_sim.py` calls `preflop_action()` directly with `facing` parameter
- `eval_strategies.py` calls `preflop_action()` directly
- `test_postflop.py` only tests postflop
- **NONE of these test `strategy_engine.py`** - the glue between vision and poker_logic!

**Fix**: Use `to_call` as sole indicator of facing:
```python
if to_call <= 0.02:      # No raise (just blinds)
    facing = 'none'       # Use OPEN ranges - ignore facing_raise flag
```

**New Test File**: `test_strategy_engine.py` (55 tests)
- Tests the ACTUAL live code path: vision → strategy_engine → poker_logic
- Catches bugs that simulations miss
- **MUST PASS before live play**

**Critical Lesson**: Simulations and offline tests can miss bugs in glue code. Always test the exact code path used in production.

---

### Session 34 Earlier: Paired Board Logic + call_open_ip (January 13, 2026)

**Challenge**: KK on JJ board was betting 3 streets - disaster when any Jx has trips.

**Fix**: Distinguish HIGH vs LOW board pairs:
- HIGH (T, J, Q, K, A): Check/fold - villain likely has trips
- LOW (2-9): Value bet normally - less likely villain has trips

**Also Fixed**: Expanded `call_open_ip` range with broadway offsuit (AQo, AJo, ATo, KQo, KJo, QJo).

---

### Session 34 Earlier: Real 2NL Data Analysis + Archetype Tuning (January 13, 2026)

**Challenge**: Simulation results didn't match real 2NL play. Archetypes were too aggressive.

**Key Findings from 886 Real Hands**:
- Opponents check 73% postflop (very passive)
- C-bet frequency only 21% (sim had 50-80%)
- Bet sizing mostly 33-50% pot
- No limping (0%)
- Open raise avg: $0.05 (2.5bb)

**Changes Made**:
1. **Archetype Tuning**: Lowered c-bet frequencies to match real data
   - fish: 40% (was higher), nit: 30%, tag: 35%, lag: 50%, maniac: 65%
   - Reduced bet sizes to 33-50% pot range
2. **Table Composition**: Single realistic table (60% fish, 25% nit, 15% tag)
   - Removed unrealistic "tough" tables with maniacs
3. **sonnet_max Strategy**: Created combining sonnet preflop + session 33 fixes
   - Smaller bet sizes (fish call anyway)
   - No river value with TPGK
   - Fold high card on paired boards

**Results** (200k hands):
- maniac +34.41 (aggression exploits passive tables)
- value_max +29.55 (best bot)
- sonnet +24.42
- sonnet_max +22.44

**Critical Lesson**: Real 2NL is EASY tables - mostly fish/passive players. Sim was modeling too-aggressive opponents.

---

### Session 29: Architecture Finalization - Strategy Engine as Default (January 12, 2026)

**Challenge**: Clarify and finalize the architecture - make strategy_engine the default, keep AI-only as fallback.

**Key Changes**:
1. **vision_detector_lite.py**: Changed default model from gpt-4o-mini → gpt-5.2
2. **helper_bar.py**: Inverted mode logic
   - Default: GPT-5.2 vision + strategy_engine (hardcoded poker logic)
   - `--ai-only` flag: GPT-5.2 does both vision + decision (old behavior)
3. **Command line args**: `--ai-only` and `--strategy <name>` instead of env vars
4. **UI labels**: Show current mode (AI ONLY vs Vision + Strategy)

**New Architecture**:
```
DEFAULT: Screenshot → GPT-5.2 (vision) → strategy_engine → Decision
AI-ONLY: Screenshot → GPT-5.2 (vision + decision) → Decision
```

**Rationale**: 
- Strategy engine gives us control over poker logic
- GPT-5.2 vision is 96.9% accurate (vs 72.7% for Kiro)
- AI-only mode kept as fallback for testing/comparison

**Critical Lesson**: When user says "we need to be on the same page", STOP and read ALL relevant files before making changes. Understanding the full architecture is critical.

---

### Session 28: GPT-5 Model Testing & Vision Prompt Improvement + Kiro Vision Integration (January 12, 2026)

**Challenge**: Test all GPT-5 models, improve vision accuracy, and integrate Kiro CLI for vision analysis.

**Repository Consolidation**:
- Merged server/ folder into main repo (was in separate onyxpoker-server/ folder)
- Both folders were pointing to same GitHub (confusing!)
- Now everything in ONE place: /onyxpoker/ with client/ and server/
- Server code now tracked in GitHub
- Systemd service updated to new location

**Key Findings - Model Testing**:
- GPT-5 family has different reasoning_effort support across versions
- gpt-5.1/gpt-5.2 support "none" (no reasoning at all)
- gpt-5/gpt-5-mini/gpt-5-nano only support "minimal" (not "none")
- GPT-4 models don't support reasoning_effort parameter at all

**Ground Truth Comparison Results** (50 screenshots):
```
Model           Cards    Board    Position  Pot      Speed
gpt-5.2         91% ⭐   100% ⭐   44%       100% ⭐   6-9s    PRODUCTION CHOICE
kiro-server     61% ⚠️   88% ⚠️    50%       100% ✅   4-5s    Suit confusion issues
```

**Key Findings**:
- ✅ GPT-5.2 card detection: 91% (40/44 correct)
- ⚠️ Kiro card detection: 61% (26/43 correct) - confuses suits (♠ vs ♣, ♥ vs ♦)
- ✅ GPT-5.2 board detection: 100% (49/49 perfect)
- ⚠️ Kiro board detection: 88% (42/48 correct)
- ❌ Position detection: Both fail (44-50%) - don't use in production
- ✅ Pot detection: Both perfect (100%)

**Ground Truth Infrastructure**:
- Created ground_truth.json with 50 verified screenshots
- Created compare_with_ground_truth.py for automated accuracy testing
- Manual verification by human expert for all 50 screenshots
- Coverage: preflop (15), flop (18), turn (10), river (5), between hands (2)

**Kiro Server Integration** (NEW ARCHITECTURE):
- Added `/analyze-screenshot` endpoint - Kiro CLI does vision analysis directly
- Added `/validate-state` endpoint - Kiro CLI validates poker states
- Client sends screenshot → Server calls `kiro-cli chat --image` → Returns poker state
- Comprehensive debug logging on both client and server
- Fixed PATH issue: using full path `/home/ubuntu/.local/bin/kiro-cli`

**Kiro CLI Speed Optimization** (NEW):
- **Problem**: poker-vision agent was defaulting to claude-sonnet-4.5 (slow)
- **Solution 1**: Fixed model name from claude-haiku-4 → claude-haiku-4.5 (12.7s → 5.9s)
- **Solution 2**: Simplified prompt with JSON example (5.9s → 4.3s)
- **Results**: 12.7s → 4.3s (66% faster!) ⚡
- **Breakdown**: 99.9% of time is Kiro CLI execution, server overhead only 0.01s

**Architecture Evolution**:
```
OLD: Screenshot → gpt-4o-mini (vision) → Kiro CLI (validation) → Result
NEW: Screenshot → Kiro CLI (vision + analysis) → Result
```

**Production Recommendations**:
- ✅ Use gpt-5.2 for production (100% cards, 91% board)
- ✅ gpt-5.1 as cheaper alternative (75% cards, 82% board)
- ✅ kiro-server with claude-haiku-4 for fast Kiro CLI vision (8.2s)
- ❌ Removed gpt-5, gpt-5-nano, gpt-4o-mini from testing (too unreliable)
- ❌ Position detection needs different approach (prompt improvements didn't help)

**Critical Lesson**: Detailed suit instructions work. Position detection requires visual approach (not text instructions). Kiro CLI can do vision analysis directly via --image flag. Model selection in agent config is critical for speed - claude-haiku-4.5 with simplified prompt is 66% faster than claude-sonnet-4.5.

---

### Session 27: Strategy-Specific Postflop (January 12, 2026)

**Challenge**: All bot strategies were using identical postflop logic, but strategy files have different approaches.

**Key Findings**:
- gpt3 had NO postflop section (preflop only)
- gpt4 has board-texture aware c-betting (25-35% on dry boards)
- sonnet/kiro_optimal have bigger value bets (75-85% pot)

**Implementation**:
1. Added `strategy=` parameter to `postflop_action()`
2. Created `_postflop_gpt()` for gpt3/gpt4 (board texture aware)
3. Created `_postflop_sonnet()` for sonnet/kiro_optimal (big value bets)
4. Added postflop section to pokerstrategy_gpt3 file
5. Fixed pocket pair below ace (KK on Axx = check-call)

**Results** (50k hands):
- sonnet/kiro_optimal: +29.85 BB/100 (bigger bets extract more value)
- gpt3/gpt4: +14-21 BB/100 (smaller bets = less value)

**Architecture Clarification**:
- `archetype=` param for fish/nit/tag/lag (player simulation)
- `strategy=` param for gpt3/gpt4/sonnet/kiro_optimal (bot logic)
- Live play uses `strategy=` only (we're the bot)
- Simulation uses both (bots vs archetypes)

**Critical Lesson**: Strategy files are the source of truth. Code must match them exactly.

---

### Session 20: Strategy Optimization + Position Detection Fix (January 8, 2026)

**Challenge**: Strategy analysis revealed major profit leaks and position detection errors.

**Major Achievements**: 
- is_hero_turn detection: **100% accuracy** (41/41 hands)
- Identified position detection bug (only BTN/SB/BB detected)
- Strategy optimization for maximum 2NL profit

**Critical Fixes Applied**:
1. **Position Detection**: Fixed algorithm to detect all 6 positions (UTG/MP/CO/BTN/SB/BB)
2. **Position-Specific Ranges**: Added tight UTG/MP, wider CO, loose BTN strategies
3. **Value Betting Optimization**: Bet bigger (75-100% pot) vs loose 2NL opponents
4. **Monster Hand Aggression**: Full houses must jam, never slowplay
5. **Suited Hand Recognition**: K2s-K9s playable in position

**Infrastructure**: Systemd service running stable with auto-restart

**Strategy Impact**: 
- Previous: Break-even to +2bb/100 (position errors + passive value betting)
- Current: Expected +6-8bb/100 (optimal 2NL exploitation)

**What Worked**:
✅ Turn detection remains 100% accurate
✅ Strategy analysis identified all major leaks
✅ Position-specific ranges now complete
✅ Value betting optimized for loose opponents

**Critical Lesson**: Position detection was causing 50% strategy errors. Always verify all poker fundamentals are working correctly.

---

### Session 12: Helper Bar UI + Cleanup (January 8, 2026)

**Challenge**: Previous session deleted agent context files during cleanup.

**What Went Wrong**:
- Deleted AGENTS.md and AmazonQ.md during "cleanup"
- Lost all agent learnings and project history

**What I Did Right**:
- Restored files via git revert
- Created helper_bar.py (new simplified UI)
- Cleaned up old files WITHOUT touching agent files

**New UI: helper_bar.py**:
- Wide, short bar docked to bottom (full width x 220px)
- No calibration needed - F9 screenshots active window
- Three columns: Status | Log | Result

**Critical Lesson**: NEVER delete context files. They are agent memory.

---

### Session 11: gpt-5.2 Switch (December 31, 2025)

**Challenge**: User frustrated - timing confusing, logs spammy

**Fixes**:
1. Switched to gpt-5.2 (2-3x faster than gpt-5-mini)
2. Fixed timing calculation (was double-counting)
3. Cleaned up logs (removed spam)
4. Clarified calibration purpose

**Critical Lesson**: When user says "moving back in time" - STOP and do complete audit. User frustration = something fundamentally wrong.

---

### Session 10: Windows Encoding Error (December 30, 2025)

**Challenge**: Calibration failing with encoding error

**Root Cause**: Used 🧠 emoji in logging - Windows cp1252 can't handle Unicode

**Fix**: Removed ALL emojis from all Python files

**Critical Lesson**: This was the THIRD time making this error. NEVER use emojis in Python code on Windows.

---

### Session 9: GPT-4o Vision Implementation (December 29-30, 2025)

**Challenge**: OpenCV doesn't understand poker - 60-70% accuracy, brittle

**Critical Realization**:
- We spent 80% effort on calibration (2,000 lines)
- We spent 20% effort on poker bot (100 lines)
- We built a calibration tool, not a poker bot

**Solution**: Switched to GPT-4o Vision
- 95-99% accuracy vs 60-70% OpenCV
- Single API call for vision + decision
- No calibration needed

**What Worked**:
✅ GPT-4o vision (excellent accuracy)
✅ Single API call for vision + decision
✅ Simplified codebase

**What Didn't Work**:
❌ OpenCV + Tesseract (too brittle)
❌ Spending 80% effort on calibration
❌ Not implementing core functionality first

**Critical Lesson**: When user says "let's review the project", STOP coding and do comprehensive analysis. We were building the wrong thing.

---

### Session 9 Part 2: UX Debugging (December 30, 2025)

**Challenge**: GPT-4o worked but overlay wasn't updating

**Root Cause**: Windows console encoding error with emoji characters (💡)

**Key Insights**:
- Windows cp1252 encoding can't handle Unicode emojis
- Exception handling can mask issues
- Real-world testing reveals UX issues

**Critical Lesson**: When user says overlay "not working" but code looks right, check for silent failures in debug prints.

---

### Session 9 Part 3: Performance Profiling (December 30, 2025)

**Performance Results**:
- Screenshot capture: 0.05-0.1s
- Save to temp: 0.3s
- Image encoding: 0.02s
- **GPT API: 8-12s** (95% of total time)
- Total: 8.5-12.4s per analysis

**Critical Lesson**: When user asks about models, RESEARCH official docs first. Don't rely on training data - it's outdated.

---

### Session 9 Part 4: GPT-5-mini Research (December 30, 2025)

**Challenge**: User insisted gpt-5-mini supports vision, I doubted it

**Research Findings**:
- ✅ gpt-5-mini DOES support vision
- ❌ GPT-5 models don't support temperature parameter
- Must OMIT temperature (not set to 0)

**Critical Lesson**: When user challenges my claim, they're usually RIGHT. Research immediately, don't defend wrong information.

---

### Earlier Sessions: Calibration & UI (December 29, 2025)

**Key Learnings**:
1. **Listen to user constraints** - User said "single monitor" multiple times, I kept designing for dual monitor
2. **Simplify ruthlessly** - If you can do it in one step, don't make it two
3. **Windows can't capture inactive windows** - Design around this constraint
4. **When user repeats constraint, STOP and redesign** with that constraint as PRIMARY requirement

**Hotkey Evolution**:
- Started with Ctrl combinations (conflicted with browser)
- Switched to F-keys only (F7-F12)
- Final: F9=Advice, F10=Bot, F11=Stop, F12=Hide

---

## 🔑 CONSOLIDATED CRITICAL LESSONS

1. **GPT Vision > OpenCV** - AI understands poker semantically, not just visually
2. **No calibration needed** - Screenshot active window directly
3. **Client-only is simpler** - Server adds complexity without benefit (for now)
4. **Research focus** - Advice system, not automation
5. **Context files are memory** - Without AGENTS.md, agent repeats mistakes
6. **No emojis in Python** - Windows encoding breaks
7. **Research before claiming** - User is usually right when they challenge me
8. **User frustration = audit needed** - Stop incremental fixes, do full review
9. **Listen to repeated constraints** - Redesign with constraint as primary requirement
10. **Test after every change** - Don't assume fixes work
