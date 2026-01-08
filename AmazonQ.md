# OnyxPoker - Status Tracking

**Last Updated**: January 8, 2026 22:39 UTC

## Current Status: PROMPT TUNING - SESSION 20

Major breakthrough: is_hero_turn detection now 100% accurate. Fixed poker decision bugs.

## What Works

| Component | Status | Notes |
|-----------|--------|-------|
| helper_bar.py | ✅ Ready | Main UI, F9 screenshots active window |
| vision_detector.py | ✅ Ready | GPT-5.2 API wrapper |
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

## Next Steps

1. **Test on PokerStars** - Play money tables
2. **Test on simulator** - Any poker software
3. **Measure accuracy** - Card/board/pot detection
4. **Measure speed** - Target <10s per analysis

## Session Log

### Session 20 (January 8, 2026)
- Analyzed 24 hands - **100% is_hero_turn accuracy** (24/24 correct)
- Fixed: Never recommend "fold" when check is free (A9 on KJQ with no bet)
- Fixed: Pre-action advice for playable hands (K9o BTN should be "raise" not "fold")
- Set up systemd service for Kiro server (auto-restart, survives reboots)
- Commit: 8391ad5

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
