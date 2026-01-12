# OnyxPoker - Status Tracking

**Last Updated**: January 12, 2026 12:49 UTC

## Current Status: LITE MODE IMPLEMENTATION - SESSION 27

Built poker strategy simulator to compare 7 bot strategies against realistic player pools.

## What Works

| Component | Status | Notes |
|-----------|--------|-------|
| helper_bar.py | ✅ Ready | Main UI, F9 screenshots active window |
| vision_detector.py | ✅ Ready | GPT-5.2 API wrapper, no position detection |
| poker_sim.py | ✅ NEW | Strategy simulator - pits strategies against each other |
| Hotkeys | ✅ Ready | F9=Advice, F10=Bot, F11=Stop, F12=Hide |
| Server | ⏸️ Placeholder | Not needed for current workflow |

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

### Bot Strategies (7 total)
- kiro_v2, sonnet, kiro_optimal, kiro5, gpt4, gpt3, opus2

### Player Archetypes (4 total)
- fish (loose passive), nit (ultra tight), lag (loose aggressive), tag (tight aggressive)

### Latest Results (Realistic Zoom 2NL-5NL)
| Rank | Strategy | BB/100 |
|------|----------|--------|
| 1 | gpt3 | +21.72 |
| 2 | sonnet | +20.75 |
| 3 | kiro5 | +20.70 |
| 4 | lag | +20.09 |
| 5 | gpt4 | +20.02 |
| 6 | kiro_v2 | +19.59 |
| 7 | kiro_optimal | +19.23 |
| 8 | opus2 | +15.79 |

## Session Log

### Session 27 (January 12, 2026)
- **LITE MODE**: Created alternative analysis pipeline
  - `vision_detector_lite.py`: Uses gpt-5-nano for table data extraction only (cheaper/faster)
  - `strategy_engine.py`: Hardcoded top 4 strategies (gpt3, gpt4, sonnet, kiro_optimal)
- **Updated test_screenshots.py**: Added `--lite` and `--strategy=X` flags
- **Updated helper_bar.py**: Set `POKER_LITE_MODE=1` env var to use lite mode
- **Usage**: `python test_screenshots.py --lite --strategy=gpt3`

### Session 26 (January 12, 2026)
- **STRATEGY SIMULATOR**: Built poker_sim.py to compare preflop strategies
- **8 STRATEGY FILES ANALYZED**: Ranked from best to worst for Blitz 6-max
- **4 PLAYER ARCHETYPES CREATED**: fish, nit, lag, tag
- **REALISTIC TABLE COMPOSITION**: 147 table configs based on actual Zoom pool research
  - ~40% fish, ~25% nit, ~25% tag, ~10% LAG per table
- **KEY FINDINGS**:
  - All bot strategies profitable (+15 to +22 BB/100) in realistic pool
  - LAG archetype competitive with bots (+20 BB/100)
  - opus2 (tightest) underperforms - too passive
  - gpt3/sonnet/kiro5 top performers
- Commits: 665ddcf, 81088eb

### Session 22 (January 9, 2026)
- **INFRASTRUCTURE CLEANUP**: Removed redundant old server
- Stopped and disabled onyxpoker.service (old Flask API server)
- Only kiro-server.service running now (Kiro analysis server on port 5001)
- Server infrastructure now clean and minimal

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
