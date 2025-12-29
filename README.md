# OnyxPoker - AI-Powered Poker Bot

## Project Overview
OnyxPoker is an intelligent poker bot that combines poker-specific screen reading with Kiro CLI-powered decision making for 6-max No-Limit Texas Hold'em.

## What It Does
- **Reads Poker Tables**: OCR-based parsing of cards, bets, stacks, and actions
- **AI Decision Making**: Uses Kiro CLI (you) for poker strategy instead of GPT API
- **Dual Modes**: Local (Windows-only) or Remote (Windows + Linux server)
- **Safe Testing**: Analysis mode displays decisions without clicking

## Architecture
```
Windows Machine
    ↓ PyAutoGUI Screenshot
    ↓ Poker OCR (cards, bets, stacks)
    ↓ Parse Poker State
    ↓ HTTP POST to Linux Server
Linux Server
    ↓ Kiro CLI Analysis
    ↓ Poker Decision (fold/call/raise)
    ↑ JSON Response
Windows Machine
    ↓ Display or Execute Action
```

## Key Components
1. **Poker Screen Reader** - OCR for cards, pot, stacks, buttons
2. **Kiro CLI Strategy** - AI-powered poker decision engine
3. **Bot Orchestrator** - Main loop with turn detection
4. **HTTP Bridge** - Cross-platform communication

## Technology Stack
- **Client**: Python + PyAutoGUI + Tesseract OCR (Windows)
- **Server**: Python + Flask + Kiro CLI (Linux)
- **OCR**: pytesseract, opencv-python, imagehash
- **Communication**: HTTP REST API with JSON

## Quick Start

### Analysis Mode (Safe)
```cmd
cd client
python poker_bot.py --execution analysis
```

### Full Automation (Advanced)
```cmd
python poker_bot.py --execution auto --hands 10
```

See **QUICKSTART.md** for detailed setup instructions.

## Features
- ✅ Turn detection
- ✅ Pot/stack OCR
- ✅ Action button parsing
- ✅ Kiro CLI integration
- ✅ Analysis mode (safe testing)
- ✅ Auto mode (full automation)
- 📝 Card recognition (needs templates)

## Documentation
- **QUICKSTART.md** - Setup and usage guide
- **INTEGRATION_PLAN.md** - 3-week development roadmap
- **PROJECT_AUDIT_REPORT.md** - Code quality audit
- **docs/API.md** - API reference
- **docs/DEPLOYMENT.md** - Deployment guide

## Research Goals
- Analyze poker decision-making with AI
- Compare Kiro CLI strategies vs traditional GTO
- Log all decisions for learning
- Build training dataset for future models

## Legal Notice
⚠️ **For research and educational purposes only**. Use only on play money tables or private simulations. Automating actions on real money poker sites may violate terms of service.

## Status
✅ **Phase 1 Complete** - Core integration done, ready for testing!
