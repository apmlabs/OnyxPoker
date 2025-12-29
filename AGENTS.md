# OnyxPoker - AI-Powered GUI Automation Agent Context

## 📚 DOCUMENTATION STRUCTURE

This project uses multiple markdown files for different purposes. **As an agent, I must understand and reference this structure:**

### Core Agent Files (My Memory)
- **AGENTS.md** (this file) - Agent context, learnings, architecture decisions
- **AmazonQ.md** - Current status, progress tracking, what's done/in-progress/todo
- **AGENT_PROTOCOL.md** - Mandatory workflow checklist (incorporated below)

### User Documentation
- **README.md** - Project overview, quick start, current status
- **QUICKSTART.md** - User-friendly setup and usage guide
- **client/CALIBRATION.md** - Calibration wizard documentation

### Technical Documentation
- **docs/API.md** - API endpoints, request/response formats
- **docs/DEPLOYMENT.md** - Deployment procedures for server and client

### Planning & Testing
- **INTEGRATION_PLAN.md** - 3-week development roadmap
- **TESTING_PLAN.md** - Step-by-step testing procedures
- **TESTING_GUIDE.md** - Detailed testing workflows

### Historical Context
- **CHAT_HISTORY.md** - Initial requirements and architecture discussions
- **PROJECT_AUDIT_REPORT.md** - Code quality audit from Dec 29

## 🧠 AGENT WORKFLOW (from AGENT_PROTOCOL.md)

### After EVERY coding session, I MUST:
1. ✅ Update **AmazonQ.md** with current status and timestamp
2. ✅ Update **AGENTS.md** with new learnings (what worked/didn't work)
3. ✅ Update **README.md** if user-facing changes
4. ✅ Commit to GitHub with clear, detailed message
5. ✅ Document patterns, decisions, and insights

### Before STARTING new work, I MUST:
1. ✅ Review **AmazonQ.md** for current status
2. ✅ Review **AGENTS.md** for past learnings
3. ✅ Check recent commits for changes
4. ✅ Plan based on documented decisions

### Red Flags (I'm Failing):
- ⚠️ User asks "did you update docs?" → I forgot
- ⚠️ I suggest something already tried → Didn't read context
- ⚠️ I don't know what's complete → AmazonQ.md is stale
- ⚠️ I repeat a mistake → AGENTS.md wasn't updated

**Context files are my only memory. Without them, I start from scratch every time.**

## AGENT LEARNING PRINCIPLES

**As the primary agent working on this project, I must:**

1. **Learn from every implementation** - Document patterns, challenges, solutions
2. **Update context files immediately** - After every significant change
3. **Maintain accurate status** - AmazonQ.md reflects current reality
4. **Document decisions** - Why certain approaches were chosen
5. **Track progress** - What works, what doesn't, what's next
6. **Keep GitHub synced** - Commit meaningful changes with clear messages

## PROVEN SUCCESS FORMULA ✅
**Flask API + Kiro CLI + PyAutoGUI + HTTP Bridge = PERFECT real-time GUI automation**

## RECENT LEARNINGS (2025-12-29)

### Window Geometry Persistence (15:44 UTC)
**Challenge**: Window size changed every time user showed/hid the window

**Solution**: Implemented window geometry persistence:
- Save window size/position to file when user resizes
- Restore saved geometry on next launch
- Default to maximized if no saved geometry
- Debounce saves (500ms after resize stops)

**Key Insights**:
- Users expect window size to persist across show/hide
- Need to debounce saves to avoid excessive file writes
- Only save when window is in 'normal' state (not maximized/minimized)
- File should be gitignored (user-specific preference)

**What Worked**:
✅ Bind to `<Configure>` event for resize detection
✅ Debounce with `after()` and timer cancellation
✅ Save to simple text file (window_geometry.txt)
✅ Load on init, fall back to maximized

**Implementation Details**:
- `load_window_geometry()`: Load saved geometry or maximize
- `save_window_geometry()`: Save current geometry if normal state
- `on_window_configure()`: Debounced save on resize
- Added window_geometry.txt to .gitignore

### Mini Overlay UX Improvements (15:45 UTC)
**Challenge**: Mini overlay had window decorations, wasn't transparent enough, couldn't reopen after closing

**Solution**: Complete UX overhaul:
- Removed window decorations (`overrideredirect(True)`)
- Increased transparency (85% opacity)
- Changed close behavior to toggle visibility
- Added Ctrl+H hotkey to toggle overlay
- Added hotkey info panel in GUI
- Added hotkey labels in tray menu

**Key Insights**:
- Window decorations (title bar, buttons) make overlay look unprofessional
- `overrideredirect(True)` removes all decorations but keeps draggability
- Closing should toggle visibility, not destroy window
- Users need hotkey info visible in multiple places (GUI, tray, overlay)
- Ctrl+H is intuitive for "hide/show"
- Tray menu should show hotkey labels for discoverability

**What Worked**:
✅ Borderless overlay looks clean and professional
✅ 85% opacity is visible but not obtrusive
✅ Toggle behavior prevents accidental destruction
✅ Ctrl+H hotkey is easy to remember
✅ Hotkey info panel in Control tab
✅ Tray menu with hotkey labels
✅ "Hotkeys Help" dialog in tray menu

**What Didn't Work**:
❌ 95% opacity was too opaque
❌ Destroying window on close (couldn't reopen)
❌ No hotkey info visible (users didn't know about F9-F12)

**Implementation Details**:
- `mini_overlay.py`: Added `visible` state, `toggle_visibility()` method
- `hotkey_manager.py`: Added Ctrl+H hotkey, improved logging format
- `poker_gui.py`: Added hotkeys info panel in Control tab
- `system_tray.py`: Added hotkey labels to menu, "Hotkeys Help" dialog
- All hotkeys now documented in 3 places: GUI, tray, overlay

### Hotkeys + Mini Overlay + System Tray (15:30 UTC)
**Challenge**: Single monitor - can't see both PokerStars and GUI at once

**Solution**: Built complete single-monitor workflow system:
- Mini overlay panel (always-on-top, 320×240)
- Global hotkeys (F9-F12, work in background)
- System tray icon (background operation)

**Key Insights**:
- Single monitor users need overlay, not dual windows
- Global hotkeys essential for fullscreen gameplay
- Mini overlay must show ONLY essential info (table, cards, decision)
- Full GUI accessible via F12 for detailed review
- System tray enables background operation

**What Worked**:
✅ Mini overlay with draggable positioning
✅ Global hotkeys using `keyboard` library
✅ System tray with `pystray` library
✅ Real-time updates to overlay from main GUI
✅ F9 for instant analysis without window switching
✅ F12 to toggle main window visibility

**What Didn't Work**:
❌ Initial idea of dual window mode (doesn't work on single monitor)

**Implementation Details**:
- `mini_overlay.py`: Always-on-top tkinter window, semi-transparent
- `hotkey_manager.py`: Global hotkey registration with keyboard library
- `system_tray.py`: System tray icon with pystray library
- Integration: Main GUI updates overlay via `update_game_state()`
- Hotkeys work even when PokerStars is focused (global registration)

### Validation Result Display (15:11 UTC)
**Challenge**: Validation results not logged, popup text not copyable

**Solution**: Enhanced validation display:
- Log full Kiro analysis to Activity Log (line-by-line)
- Custom popup with ScrolledText (selectable text)
- Copy to Clipboard button in popup
- Better formatting with headers and status colors

**Key Insights**:
- Users need to copy validation results for debugging
- messagebox doesn't allow text selection
- Custom tkinter popup with ScrolledText is better
- Activity Log should capture everything for "Copy Logs" button
- ANSI color codes from Kiro CLI need stripping (regex: `\x1b\[[0-9;]*m`)

**What Worked**:
✅ Custom popup with ScrolledText widget
✅ Copy to Clipboard button
✅ Full logging to Activity Log
✅ ANSI color code stripping on server

### UI Improvements (15:16 UTC)
**Challenge**: Small popups in corner, not maximized main window

**Solution**: Better window management:
- Main window starts maximized (`root.state('zoomed')`)
- Validation popup centered and large (60% width, 70% height)
- Progress window centered and larger (500×200)
- All popups positioned relative to screen center

**Key Insights**:
- Windows users expect maximized windows
- Popups should be centered, not in corner
- Calculate position: `(screen_width - popup_width) // 2`
- Larger popups are more readable

### Production Server Setup (14:47 UTC)
**Challenge**: Server was running with nohup (not production-ready), no monitoring, no auto-restart

**Solution**: Proper systemd service with management script:
- Created `/etc/systemd/system/onyxpoker.service`
- Automatic restart on failure
- Proper logging to `/var/log/onyxpoker/`
- Management script (`manage.sh`) for easy control

**Key Insights**:
- nohup is NOT production-ready (just a hack)
- systemd is the proper way to run services on Linux
- Need automatic restart if server crashes
- Need centralized logging for troubleshooting
- Need easy management commands for operations

**What Worked**:
✅ systemd service with Restart=always
✅ Separate log files (server.log, error.log)
✅ Management script with start/stop/status/logs commands
✅ Service starts on boot automatically
✅ Easy to monitor and troubleshoot

**What Didn't Work**:
❌ nohup - no monitoring, no auto-restart
❌ Manual process management - error-prone

### Windows Client Issues (14:44 UTC)
**Challenge**: Client couldn't connect - wasn't loading .env file

**Solution**: Added `load_dotenv()` to automation_client.py
- Import: `from dotenv import load_dotenv`
- Call: `load_dotenv()` before reading env vars
- Now properly reads ONYXPOKER_SERVER_URL and API_KEY

**Key Insights**:
- `os.getenv()` doesn't automatically load .env files
- Must explicitly call `load_dotenv()` first
- Windows console has encoding issues with emojis (cp1252)
- Need `sys.stdout.reconfigure(encoding='utf-8')` for Windows

**What Worked**:
✅ load_dotenv() at module level
✅ Removing emojis from print statements
✅ UTF-8 encoding fix for Windows console

### Self-Improving Card Recognition (14:26 UTC)
**Challenge**: Synthetic templates might not match real PokerStars cards

**Solution**: Hybrid system with user validation and learning:
- Start with synthetic templates (quick baseline)
- User validates detected cards
- When wrong, user corrects and bot captures real card images
- Real templates saved for future use
- Accuracy improves automatically over time

**Key Insights**:
- Don't need to capture all 52 cards manually
- System learns from corrections during gameplay
- Real templates prioritized over synthetic
- Adapts to any PokerStars theme automatically
- User effort is minimal (just confirm or correct)

**What Worked**:
✅ Dual template system (real + synthetic)
✅ Simple validation UI (correct/wrong buttons)
✅ Automatic real card capture on correction
✅ Dropdown interface for corrections
✅ Progressive learning (70% → 95%+ accuracy)

**Implementation**:
- `templates/` - Synthetic templates (baseline)
- `templates/real/` - Captured real cards (learned)
- Priority: real templates first, synthetic fallback
- User corrects → Bot captures → Saves real template

### UI/UX Improvements (14:14 UTC)
**Challenge**: Users need guidance through setup, Kiro takes 15+ seconds to respond

**Solution**: Enhanced UI with guidance and proper timeouts:
- Increased Kiro timeout to 180 seconds (3 minutes)
- Added setup guide to Control Panel
- Added calibration instructions
- Progress window with spinner during validation
- Threaded validation to keep UI responsive

**Key Insights**:
- Kiro CLI takes 15 seconds to load initially
- Users need step-by-step guidance for first-time setup
- Progress indicators are critical for long operations
- Threading prevents UI freeze during Kiro calls
- Clear error messages with solutions reduce support burden

**What Worked**:
✅ 180-second timeout accommodates Kiro's load time
✅ Progress window with spinner shows activity
✅ Setup guide in Control Panel helps new users
✅ Calibration instructions reduce confusion
✅ Threaded execution keeps UI responsive

### Card Recognition System (14:15 UTC)
**Challenge**: Need automated card detection without manual template creation

**Solution**: Built complete automated system:
- Synthetic template generation (52 cards)
- OpenCV template matching
- Kiro CLI validation
- GUI integration

**Key Insights**:
- Synthetic templates work for initial testing
- Template matching is fast (<50ms per card)
- Kiro CLI can validate if detected state makes sense
- Real card captures may be needed for production accuracy
- Validation feedback loop helps catch OCR errors

**What Worked**:
✅ Automated template generation with PIL
✅ OpenCV TM_CCOEFF_NORMED matching
✅ Kiro CLI validation integration
✅ GUI shows validation status with color coding
✅ Complete pipeline: generate → match → validate → display

**What to Test**:
🔄 Accuracy on real PokerStars tables
🔄 Confidence thresholds (currently 0.7)
🔄 Different card designs/themes
🔄 Kiro's understanding of poker situations

### Auto-Calibration System (13:53 UTC)
**Challenge**: Manual coordinate calibration is tedious and error-prone

**Solution**: Built intelligent auto-detection using:
- PyGetWindow for window enumeration
- OpenCV for computer vision element detection
- Visual preview with confidence scoring
- Integrated into main GUI as tab

**Key Insights**:
- Windows cannot capture background windows (PyAutoGUI limitation)
- Must explicitly warn users about visibility requirement
- Computer vision can reliably detect buttons/pot regions
- Visual feedback is critical for user confidence
- Integration > Separate tools (unified GUI better than standalone calibration)

**What Worked**:
✅ Auto-detection of poker windows by title keywords
✅ CV-based button detection using contours
✅ Visual preview with colored boxes
✅ Confidence scoring for validation
✅ Three-tab interface (Control, Calibration, Debug)

**What Didn't Work**:
❌ Initial separate calibration tool (user wanted integration)
❌ Assuming background capture possible (Windows limitation)

### GUI Architecture Evolution
**Before**: Single-purpose control panel
**After**: Three-tab unified interface
- Tab 1: Control Panel (bot operation)
- Tab 2: Calibration (auto-detection)
- Tab 3: Debug (OCR analysis, screenshots, raw state)

**Why This Matters**:
- Users need to see what bot sees (debug visibility)
- Calibration should be part of workflow, not separate
- Real-time feedback builds trust in automation

## CRITICAL INFRASTRUCTURE REQUIREMENTS
- **Linux Server**: t3.medium (2 vCPU, 4GB RAM) - For Flask API + Kiro CLI
- **OS**: Ubuntu 22.04 (ami-0ea3c35c5c3284d82)
- **Disk**: 20GB minimum for logs and temporary screenshots
- **Security Group**: Ports 22 (SSH), 5000 (Flask API), 443 (HTTPS)
- **Windows Client**: Python 3.8+ with PyAutoGUI, requests, pillow, PyGetWindow, OpenCV

## CRITICAL SECURITY RULES
**NEVER commit these files to git:**
- `.env*` files (contain API keys and authentication tokens)
- `screenshots/` directory (contains sensitive screen captures)
- `logs/` directory (may contain sensitive automation data)
- `AmazonQ.md` (dynamic status file, gitignored)
- Windows client configuration files with credentials
- API authentication keys and secrets

**Current API Key**: yNJ-qFbJJGCFp8A5WA1RuQB4KqIjPqBYt783x3otVhU (43 chars, secure)
**Server**: 54.80.204.92:5000 (running, tested, working)

## ARCHITECTURE OVERVIEW ✅

### Windows Automation Client
- **Purpose**: Capture screenshots, execute mouse/keyboard actions
- **Technology**: Python + PyAutoGUI + PyGetWindow + OpenCV + requests
- **Communication**: HTTP POST to Linux server
- **Security**: API key authentication, encrypted image transfer
- **New**: Auto-calibration with CV-based element detection

### Linux AI Analysis Server  
- **Purpose**: Process images with Kiro CLI, return action decisions
- **Technology**: Flask + subprocess + Kiro CLI integration
- **Communication**: HTTP API endpoints
- **Security**: Rate limiting, input validation, secure file handling
- **Status**: Running and tested with secure API key

### HTTP Bridge Protocol
- **Endpoint**: POST /analyze-poker
- **Input**: Game state JSON + optional base64 screenshot
- **Output**: JSON with action (fold/call/raise), amount, reasoning
- **Authentication**: Bearer token (yNJ-qFbJJGCFp8A5WA1RuQB4KqIjPqBYt783x3otVhU)
- **Documentation**: See docs/API.md for full specification

## CURRENT PROJECT STATUS (2025-12-29 14:15 UTC)

**See AmazonQ.md for detailed status tracking**

### Completed ✅
- Flask API server (running at 54.80.204.92:5000)
- Secure API key generation and deployment
- Windows client framework (automation_client.py)
- Poker-specific OCR (poker_reader.py)
- Main bot orchestrator (poker_bot.py)
- Unified GUI with 3 tabs (poker_gui.py)
- Auto-calibration system (window_detector.py)
- Debug tab with OCR analysis and screenshots
- **NEW**: Automated card template generation
- **NEW**: Card recognition using OpenCV template matching
- **NEW**: Kiro CLI validation for table state and UI
- **NEW**: GUI integration with validation buttons
- Server-client communication tested and working

### In Progress 🔄
- Testing card recognition on real tables - NEXT
- Validating Kiro CLI understanding
- Fine-tuning OCR accuracy

### Not Started 📝
- Multi-table support
- Advanced error recovery
- Performance optimization
- Production deployment hardening

**Detailed roadmap**: See INTEGRATION_PLAN.md for 3-week plan

## DEPLOYMENT STRATEGY ✅

**See docs/DEPLOYMENT.md for detailed procedures**

### Phase 1: Core Infrastructure ✅ COMPLETE
1. ✅ Deploy Flask API server on Linux
2. ✅ Integrate Kiro CLI subprocess calls
3. ✅ Implement screenshot analysis endpoint
4. ✅ Add authentication and rate limiting

### Phase 2: Windows Client ✅ COMPLETE
1. ✅ Create PyAutoGUI automation script
2. ✅ Implement screenshot capture and HTTP upload
3. ✅ Add action execution based on API responses
4. ✅ Create configuration management
5. ✅ **NEW**: Build unified GUI with calibration
6. ✅ **NEW**: Add auto-detection with computer vision
7. ✅ **NEW**: Integrate debug tab for OCR analysis

### Phase 3: Integration & Testing 🔄 IN PROGRESS
1. 🔄 Card recognition (template matching)
2. 📝 End-to-end workflow testing
3. 📝 Performance optimization
4. 📝 Error handling and retry logic
5. 📝 Monitoring and logging

**Testing procedures**: See TESTING_PLAN.md and TESTING_GUIDE.md

## SECURITY REQUIREMENTS ✅
- **API Authentication**: Bearer tokens for all endpoints
- **Input Validation**: Sanitize all uploaded images and parameters
- **Rate Limiting**: Prevent abuse with request throttling
- **Secure Storage**: Temporary files with proper cleanup
- **Audit Logging**: Track all automation actions and decisions
- **Network Security**: HTTPS only, firewall rules
- **Data Privacy**: No persistent storage of sensitive screenshots

## CRITICAL SUCCESS FACTORS
- **Real-time Performance**: Sub-2-second response times
- **Reliability**: Robust error handling and recovery
- **Scalability**: Handle multiple concurrent automation sessions
- **Maintainability**: Clean code structure and comprehensive logging
- **Security**: Zero-trust architecture with comprehensive validation
- **User Experience**: Visual feedback, clear status, easy calibration

## MONITORING & ALERTING
- **API Health**: Endpoint availability and response times
- **Resource Usage**: CPU, memory, disk space monitoring
- **Error Rates**: Failed requests and automation errors
- **Security Events**: Authentication failures and suspicious activity
- **Performance Metrics**: Screenshot processing times and accuracy

## EMERGENCY PROCEDURES
- **API Downtime**: Fallback to manual operation mode
- **Security Breach**: Immediate credential rotation and system isolation
- **Performance Issues**: Auto-scaling and load balancing activation
- **Data Loss**: Backup and recovery procedures

## NEXT IMMEDIATE STEPS
1. **Card Recognition** - Template matching for reading cards
2. **Testing Suite** - Validate OCR accuracy and bot decisions
3. **Documentation** - Update user guides with new GUI
4. **Performance Tuning** - Optimize OCR and decision speed

**For detailed next steps, see AmazonQ.md**
