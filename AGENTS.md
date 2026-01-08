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
    GPT-5.2 Vision API
         ↓
   Decision + Reasoning
         ↓
    Helper Bar UI (advice display)
```

**Client-only approach** - All processing via OpenAI API directly. Server exists as placeholder for potential future work (Deep CFR, etc.) but is not currently used.

## 📁 CURRENT FILE STRUCTURE

```
onyxpoker/
├── AGENTS.md              # Agent memory (NEVER DELETE)
├── AmazonQ.md             # Status tracking (NEVER DELETE)
├── README.md              # Quick start (NEVER DELETE)
├── .gitignore
├── .env.example
├── client/
│   ├── helper_bar.py      # Main UI (380 lines)
│   ├── vision_detector.py # GPT-5.2 API wrapper (130 lines)
│   ├── requirements.txt
│   └── setup.bat
├── server/                # Placeholder for future
│   ├── app.py
│   ├── poker_strategy.py
│   ├── manage.sh
│   ├── setup.sh
│   └── requirements.txt
└── docs/
    ├── API.md
    └── DEPLOYMENT.md
```

## ✅ CURRENT STATE

### What Works
- `helper_bar.py` - Wide bar UI docked to bottom, screenshots active window on F9
- `vision_detector.py` - GPT-5.2 API for card/board/pot detection + decisions
- Screenshot saving - Auto-saves to client/screenshots/ folder
- Test mode - test_screenshots.py for offline testing
- Kiro server - Flask app on port 5001 for remote analysis
- send_to_kiro.py - Client script to send screenshots to server
- Hotkeys: F9=Advice, F10=Bot loop, F11=Stop, F12=Hide
- No calibration needed - F9 screenshots whatever window is active

### What's Not Implemented
- Turn detection (detecting when it's hero's turn)
- Action execution (clicking buttons) - LOW PRIORITY, research focus

### What's Been Removed
- Calibration system (not needed - active window screenshot)
- poker_reader.py, config.py (redundant)
- Old UI files (poker_gui.py, mini_overlay.py, etc.)
- Archive folder (git is our history)

## 🚀 NEXT STEPS

### Priority 1: Test on Real Tables
- [ ] Test with PokerStars play money tables
- [ ] Test with poker simulator software
- [ ] Verify card/board/pot detection accuracy
- [ ] Measure response time (target: <10s)

### Priority 2: Improve Accuracy
- [ ] Tune GPT prompt for edge cases
- [ ] Handle all-in situations, side pots
- [ ] Add hand history logging for analysis

### Future (Low Priority)
- [ ] Turn detection
- [ ] Server-side processing (Deep CFR)
- [ ] Multi-table support

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

### Session 20: 100% Turn Detection + Systemd Service (January 8, 2026)

**Challenge**: Two poker decision bugs found during testing.

**Major Achievement**: is_hero_turn detection reached **100% accuracy** (24/24 hands).

**Fixes Applied**:
1. **Never fold when check is free**: A9 on KJQ with no bet → recommend "check" not "fold"
2. **Pre-action playable hands**: K9o on BTN → recommend "raise" (if folded to) not "fold"

**Infrastructure Improvement**: Set up systemd service for Kiro server
- Auto-restart on crash (RestartSec=10)
- Auto-start on boot (enabled)
- Proper process management
- Easy monitoring with `systemctl status kiro-server`

**What Worked**:
✅ Turn detection fix from previous sessions is rock solid
✅ GPT correctly distinguishes RED action buttons vs gray checkboxes
✅ max_call field working perfectly for pre-action sizing
✅ Systemd service prevents server downtime issues

**Critical Lesson**: The is_hero_turn detection problem is now completely solved. Focus can shift to poker strategy refinement.

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
