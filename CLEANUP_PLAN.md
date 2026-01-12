# Project Cleanup - COMPLETED ✅
**Date**: January 12, 2026 18:45 UTC

## Cleanup Summary

**Deleted**: 14 temporary files
- 1 from root (FIXES_PLAN.md)
- 1 from server/uploads/ (PROMPT_UPDATE_SUMMARY.md)
- 12 from /tmp/ (all .md, .json, .py analysis files)

**Result**: Clean, organized project with only essential files

## Final Project Structure

```
onyxpoker/
├── AGENTS.md                    # Agent memory (NEVER DELETE)
├── AmazonQ.md                   # Status tracking (NEVER DELETE)
├── README.md                    # User guide (NEVER DELETE)
├── CLEANUP_PLAN.md              # This file
├── .env.example                 # Environment template
│
├── client/                      # Windows client code
│   ├── helper_bar.py            # Main UI
│   ├── vision_detector.py       # Full mode (gpt-5.2)
│   ├── vision_detector_lite.py  # Lite mode (gpt-4o-mini)
│   ├── vision_detector_test.py  # Testing detector
│   ├── strategy_engine.py       # Lite mode strategy
│   ├── poker_logic.py           # Hand evaluation + decisions
│   ├── poker_sim.py             # Strategy simulator
│   ├── test_screenshots.py      # Offline testing
│   ├── send_to_kiro.py          # Upload to server
│   ├── send_logs.py             # Upload logs
│   └── requirements.txt
│
├── server/                      # EC2 server code
│   ├── kiro_analyze.py          # Kiro CLI server (port 5001)
│   ├── app.py                   # Old server (not used)
│   ├── poker_strategy.py        # Strategy logic
│   ├── analyze_session.py       # Log analysis
│   ├── requirements.txt
│   └── uploads/                 # Screenshots + logs (gitignored)
│       ├── VISION_COMPARISON_REPORT.md  # Model comparison
│       ├── compare_with_ground_truth.py # Testing script
│       ├── ground_truth.json            # Test data
│       ├── *.png                        # Screenshots (gitignored)
│       └── *.jsonl                      # Logs (gitignored)
│
└── docs/
    ├── DEPLOYMENT.md            # Setup guide
    └── ANALYSIS_NOTES.md        # GPT decision analysis
```

## Code Statistics

**Total**: ~2,606 lines of actual code (excluding comments/blanks)

### By Component
- **Core Logic**: 664 lines (poker_logic.py)
- **UI & Testing**: 784 lines (helper_bar, poker_sim, test_screenshots)
- **Vision & Strategy**: 447 lines (3 vision detectors + strategy engine)
- **Server**: 711 lines (kiro_analyze, app, analysis tools)

## Repository Status

- ✅ Both folders (client + server) in same GitHub repo
- ✅ All temporary files removed
- ✅ Only essential documentation kept
- ✅ Clean commit history
- ✅ Ready for continued development

## Next Steps

1. Pull latest on Windows: `git pull`
2. Test both models: `python test_screenshots.py --lite --test-all-models`
3. Upload logs: `python send_logs.py`
4. Analyze results on server
