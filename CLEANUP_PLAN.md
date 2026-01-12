# Project Cleanup Plan
**Date**: January 12, 2026

## Files to DELETE

### Root Directory
- [x] FIXES_PLAN.md - Temporary, issues already fixed

### server/uploads/
- [x] PROMPT_UPDATE_SUMMARY.md - Temporary summary, info in AGENTS.md

### /tmp/ (all temporary analysis files)
- [x] /tmp/NEW_API_KEY.md
- [x] /tmp/PHASE1_COMPLETE.md
- [x] /tmp/SERVER_QUICK_REFERENCE.md
- [x] /tmp/SERVER_TEST_REPORT.md
- [x] /tmp/VISION_COMPARISON_REPORT.md (duplicate, kept in server/uploads/)
- [x] /tmp/amazonq_update.md
- [x] /tmp/analysis_data.json
- [x] /tmp/analyze_all.py
- [x] /tmp/ground_truth_manual.json
- [x] /tmp/kiro_vs_gpt52_comparison.json
- [x] /tmp/model_comparison.json
- [x] /tmp/test_same_prompt.py

## Files to KEEP

### Core Documentation (NEVER DELETE)
- AGENTS.md - Agent memory
- AmazonQ.md - Status tracking
- README.md - User guide

### Technical Documentation
- docs/DEPLOYMENT.md - Setup guide
- docs/ANALYSIS_NOTES.md - GPT decision analysis (useful reference)

### Testing Infrastructure
- server/uploads/VISION_COMPARISON_REPORT.md - Model comparison results
- server/uploads/compare_with_ground_truth.py - Testing script
- server/uploads/ground_truth.json - Test data

### Python Code (all .py files in client/ and server/)
- All production code

## Cleanup Commands

```bash
# Delete temporary files
rm /home/ubuntu/mcpprojects/onyxpoker/FIXES_PLAN.md
rm /home/ubuntu/mcpprojects/onyxpoker/server/uploads/PROMPT_UPDATE_SUMMARY.md
rm /tmp/*.md /tmp/*.json /tmp/*.py

# Commit cleanup
cd /home/ubuntu/mcpprojects/onyxpoker
git add -A
git commit -m "Clean up temporary files and documentation"
git push origin main
```

## Summary

**Deleting**: 14 temporary files (1 in root, 1 in server/uploads, 12 in /tmp)
**Keeping**: 3 core docs + 2 technical docs + 3 testing files + all code
