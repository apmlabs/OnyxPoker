# OnyxPoker - Status Tracking

**Last Updated**: January 12, 2026 17:58 UTC

## Current Status: SESSION 28 - KIRO CLI SPEED OPTIMIZATION

Optimized Kiro CLI from 12.7s → 4.3s (66% faster!) via model fix + prompt simplification.

## What Works

| Component | Status | Notes |
|-----------|--------|-------|
| helper_bar.py | ✅ Ready | Main UI, F9 screenshots active window |
| vision_detector.py | ✅ Ready | Full mode: GPT-5.2 for vision + decisions |
| vision_detector_lite.py | ✅ Ready | Lite mode: gpt-4o-mini for vision only |
| strategy_engine.py | ✅ Ready | Lite mode: applies strategy-specific postflop |
| poker_logic.py | ✅ Ready | Shared logic with strategy-specific postflop |
| poker_sim.py | ✅ Ready | Full postflop simulation |
| Server | ✅ Running | 54.80.204.92:5001 receives uploads |

## Architecture

### Full Mode (gpt-5.2)
```
F9 → screenshot → vision_detector.py (gpt-5.2) → action + reasoning
```

### Lite Mode (gpt-4o-mini + hardcoded strategy)
```
F9 → screenshot → vision_detector_lite.py (gpt-4o-mini) → table data
                → strategy_engine.py → poker_logic.py → action + reasoning
```

### Postflop Logic Architecture
```
postflop_action(archetype=None, strategy=None)
         ↓
    ┌────┴────┐
archetype    strategy
(fish/nit/   (gpt3/gpt4/
tag/lag)     sonnet/kiro)
    ↓            ↓
archetype    _postflop_gpt() or _postflop_sonnet()
logic
```

## Server Locations

**Windows Client**: C:\aws\onyx-client\
**EC2 Server**: /home/ubuntu/mcpprojects/onyxpoker/server/
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

### Bot Strategies (4 in sim)
- gpt3, gpt4, sonnet, kiro_optimal

### Player Archetypes (4 total)
- fish (loose passive), nit (ultra tight), lag (loose aggressive), tag (tight aggressive)

### Strategy-Specific Postflop
| Strategy | Style | Key Differences |
|----------|-------|-----------------|
| gpt3/gpt4 | Board texture aware | Small c-bets (25-35%) on dry boards |
| sonnet/kiro_optimal | Big value bets | 75-85% pot sizing, overpair logic |

### Latest Results (50k hands with strategy-specific postflop)
| Rank | Strategy | BB/100 |
|------|----------|--------|
| 1 | kiro_optimal | +29.85 |
| 2 | sonnet | +29.52 |
| 3 | gpt3 | +21.54 |
| 4 | gpt4 | +14.79 |

## Session Log

### Session 28 (January 12, 2026)
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
- Commits: 2fcf2fa, 636e0dd, 609d1df, d353009, c84d71f, d81145c, d3fd49a, b618d09, 7aa46e7, 2f811d9, 377818f, 0647033

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
