# OnyxPoker - Status Tracking

**Last Updated**: January 13, 2026 01:15 UTC

## Current Status: SESSION 31 - SMART POSTFLOP FIXES ✅

Fixed critical bugs: board pair detection, weak kicker sizing, pot odds. value_max now #1 at +46.82 BB/100.

## What Works

| Component | Status | Notes |
|-----------|--------|-------|
| helper_bar.py | ✅ Ready | Draggable UI, manual position selector at top |
| vision_detector.py | ✅ Ready | Full mode: GPT-5.2 for vision + decisions |
| vision_detector_lite.py | ✅ Ready | Lite mode: gpt-4o-mini for vision only |
| strategy_engine.py | ✅ Ready | Lite mode: applies strategy-specific postflop |
| poker_logic.py | ✅ Ready | Shared logic with strategy-specific postflop |
| poker_sim.py | ✅ Ready | Full postflop simulation |
| Server | ✅ Running | 54.80.204.92:5001 with Kiro Sonnet 4.5 |

## Architecture

### Default Mode (gpt-5.2 vision + strategy)
```
F9 → screenshot → vision_detector_lite.py (gpt-5.2) → table data
                → strategy_engine.py → poker_logic.py → action + reasoning
Position: Manual selection from UI radio buttons
```

### AI-Only Mode (--ai-only flag)
```
F9 → screenshot → vision_detector.py (gpt-5.2) → action + reasoning
Position: Manual selection from UI radio buttons
```

## UI Features

- **Draggable**: Click top bar to move window
- **Position Selector**: 6 buttons (UTG/MP/CO/BTN/SB/BB) at top
- **No Window Decorations**: Clean, minimal interface
- **Resizable**: Drag borders to resize
- **Hotkeys**: F9=Advice, F10=Bot, F11=Stop, F12=Hide

## Server Locations

**Windows Client**: C:\aws\onyx-client\
**EC2 Server**: /home/ubuntu/mcpprojects/onyxpoker/server/
**Uploads**: /home/ubuntu/mcpprojects/onyxpoker/server/uploads/ (471 screenshots, 13 logs, 177MB)

**Note**: Server code is now part of main GitHub repo (consolidated January 12, 2026)
**Uploads**: /home/ubuntu/mcpprojects/onyxpoker/server/uploads/

**Note**: Server code is now part of main GitHub repo (consolidated January 12, 2026)

## Quick Start

```bash
export OPENAI_API_KEY='sk-your-key'
cd client
pip install -r requirements.txt
python helper_bar.py
```

Then: Focus poker window → Press F9 → See advice in helper bar

## Strategy Simulator

```bash
cd client
python3 poker_sim.py 150000  # Run 150k hands simulation
```

### Bot Strategies (8 in sim)
- gpt3, gpt4, sonnet, kiro_optimal, kiro5, kiro_v2, aggressive, 2nl_exploit

### Player Archetypes (5 total)
- fish (loose passive), nit (ultra tight), lag (loose aggressive), tag (tight aggressive), maniac (overbets 100%+ pot)

### Strategy-Specific Postflop
| Strategy | Style | Key Differences |
|----------|-------|-----------------|
| gpt3/gpt4 | Board texture aware | Small c-bets (25-35%) on dry boards |
| sonnet/kiro_optimal/kiro5/kiro_v2 | Big value bets | 75-85% pot sizing, overpair logic |
| aggressive/2nl_exploit | Sonnet postflop | Wider ranges, falls through to default |

### Latest Results (30k hands x 3 trials, with maniac)
| Rank | Strategy | BB/100 | StdDev |
|------|----------|--------|--------|
| 1 | gpt4 | +43.12 | 22.47 |
| 2 | 2nl_exploit | +39.51 | 34.44 |
| 3 | aggressive | +32.76 | 36.63 |
| 4 | gpt3 | +31.35 | 12.03 |
| 5 | kiro_v2 | +29.31 | 33.28 |
| 6 | kiro_optimal | +24.04 | 26.91 |
| 7 | kiro5 | +19.50 | 15.44 |
| 8 | sonnet | +9.17 | 11.79 |

## Session Log

### Session 31 (January 13, 2026)
- **SMART POSTFLOP FIXES**: Analyzed 245-hand session log, found critical bugs ⭐
  - Fixed board pair detection (AJ on Q22 was "pair", now "high card")
  - Fixed top pair weak kicker (was potting, now 40% flop only then check)
  - Added pot odds calculation for calling decisions
  - C-bet only on dry boards or with equity (not 80% with air)
- **RESULTS**: value_max now #1 at +46.82 BB/100 (was +38)
  - Beats maniac (+46.82 vs +39.15) - smart > blind aggression
  - Lowest variance (StdDev 2.59)

### Session 30 (January 12, 2026)
- **VALUE_MAX OPTIMIZATION**: Analyzed why maniac beats all bots ⭐
  - Compared preflop: maniac opens 316 combos vs value_max 206
  - Compared postflop: maniac bets 100-125% pot, value_max was 60-85%
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
