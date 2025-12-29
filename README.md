# OnyxPoker - AI-Powered Poker Bot

**Status**: ✅ Server Operational | Ready for Client Testing

## Quick Start

### Server (Linux - AWS)
```bash
Server URL: http://54.80.204.92:5000
API Key: test_key_12345
Status: Running ✅
```

### Client (Windows)
```bash
ONYXPOKER_SERVER_URL=http://54.80.204.92:5000
ONYXPOKER_API_KEY=test_key_12345
```

## Project Overview
OnyxPoker is an intelligent poker bot that combines poker-specific screen reading with Kiro CLI-powered decision making for 6-max No-Limit Texas Hold'em.

## What It Does
- **Reads Poker Tables**: OCR-based parsing of cards, bets, stacks, and actions
- **AI Decision Making**: Uses Kiro CLI for poker strategy (real AI, not mocked)
- **Dual Modes**: Local (Windows-only) or Remote (Windows + Linux server)
- **Safe Testing**: Analysis mode displays decisions without clicking

## Architecture
```
Windows Machine
    ↓ PyAutoGUI Screenshot
    ↓ Poker OCR (cards, bets, stacks)
    ↓ Parse Poker State
    ↓ HTTP POST to Linux Server
Linux Server (AWS)
    ↓ Kiro CLI Analysis (REAL AI)
    ↓ Poker Decision (fold/call/raise)
    ↑ JSON Response
Windows Machine
    ↓ Display or Execute Action
```

## Current Status

### ✅ Phase 1 Complete: Server Setup
- Flask API running on AWS (54.80.204.92:5000)
- Real Kiro CLI integration tested and confirmed
- Authentication working
- Port 5000 publicly accessible
- All 8 comprehensive tests passed

### ➡️ Phase 2: Client Setup
- Configure Windows client
- Test end-to-end communication
- Calibrate screen regions
- Test poker bot in analysis mode

## Documentation
- **SERVER_TEST_REPORT.md** - Comprehensive test results
- **SERVER_QUICK_REFERENCE.md** - Quick API reference
- **SERVER_STATUS.md** - Current server status
- **QUICKSTART.md** - Setup and usage guide
- **INTEGRATION_PLAN.md** - 3-week development roadmap
- **TESTING_PLAN.md** - Step-by-step testing guide
- **TESTING_GUIDE.md** - Detailed testing procedures

## Technology Stack
- **Server**: Python + Flask + Kiro CLI (Linux/AWS)
- **Client**: Python + PyAutoGUI + Tesseract OCR (Windows)
- **OCR**: pytesseract, opencv-python, imagehash
- **Communication**: HTTP REST API with JSON

## Test Results Summary

| Test | Result | Details |
|------|--------|---------|
| Health Check | ✅ PASS | Server responding |
| Authentication | ✅ PASS | API key validation |
| Pocket Aces | ✅ PASS | Raise (correct) |
| Seven-Two | ✅ PASS | Fold (correct) |
| King-Queen | ✅ PASS | Raise (correct) |
| External Access | ✅ PASS | Publicly accessible |
| Kiro CLI | ✅ CONFIRMED | Real AI integration |
| Background Operation | ✅ PASS | Stable |

## Legal Notice
⚠️ **For research and educational purposes only**. Use only on play money tables or private simulations.

## Next Steps
1. ✅ Server setup and testing complete
2. ➡️ Configure Windows client
3. ➡️ Test end-to-end communication
4. ➡️ Calibrate screen regions
5. ➡️ Run poker bot in analysis mode
