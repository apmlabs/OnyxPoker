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

### Auto-Calibration System
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

## CURRENT PROJECT STATUS (2025-12-29 13:56 UTC)

**See AmazonQ.md for detailed status tracking**

### Completed ✅
- Flask API server (running at 54.80.204.92:5000)
- Secure API key generation and deployment
- Windows client framework (automation_client.py)
- Poker-specific OCR (poker_reader.py)
- Main bot orchestrator (poker_bot.py)
- **NEW**: Unified GUI with 3 tabs (poker_gui.py)
- **NEW**: Auto-calibration system (window_detector.py)
- **NEW**: Debug tab with OCR analysis and screenshots
- Server-client communication tested and working

### In Progress 🔄
- Card recognition (template matching) - NEXT
- Testing and validation - AFTER CARDS
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
