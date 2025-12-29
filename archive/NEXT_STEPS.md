# OnyxPoker - Next Steps & Development Roadmap

**Date**: December 29, 2025 16:26 UTC  
**Current Status**: Complete hotkey-driven workflow ready for testing

---

## 🎯 Immediate Next Steps (This Week)

### 1. User Testing on PokerStars (Priority 1)

**Goal**: Validate entire workflow on real poker table

**Steps**:
```bash
1. Pull latest code
   cd /home/ubuntu/mcpprojects/onyxpoker
   git pull origin main

2. Launch GUI
   cd client
   python poker_gui.py

3. Follow overlay guidance
   - Ctrl+C → Calibrate
   - F12 → Hide client
   - Ctrl+T → Capture & detect
   - Save configuration
   - Ctrl+T → Test OCR

4. Open PokerStars play money table

5. Test F9 (capture & analyze)
   - Does it capture correctly?
   - Does OCR read pot/stacks?
   - Does Kiro provide advice?
   - Is overlay updated?

6. Report results
   - What works?
   - What doesn't?
   - Screenshots of any issues
   - Copy Activity Log if errors
```

**Success Criteria**:
- [ ] Calibration completes without errors
- [ ] OCR reads pot amount (±10% accuracy)
- [ ] OCR reads stack amounts (±10% accuracy)
- [ ] F9 captures and analyzes
- [ ] Kiro provides poker advice
- [ ] Overlay shows decision
- [ ] No crashes

**Time Estimate**: 30 minutes

---

### 2. Measure OCR Accuracy (Priority 2)

**Goal**: Quantify how well OCR reads poker table

**Test Cases**:
```
Test 1: Small Pot ($20-50)
- Expected: $35
- Actual: $_____
- Accuracy: _____%

Test 2: Medium Pot ($100-200)
- Expected: $150
- Actual: $_____
- Accuracy: _____%

Test 3: Large Pot ($500+)
- Expected: $750
- Actual: $_____
- Accuracy: _____%

Test 4: Stack Sizes
- Expected: [500, 480, 500, 450, 520, 490]
- Actual: [___, ___, ___, ___, ___, ___]
- Accuracy: _____%
```

**Success Criteria**:
- [ ] Pot reading >90% accurate
- [ ] Stack reading >85% accurate
- [ ] No false positives (reading 0 when pot exists)

**Time Estimate**: 20 minutes

---

### 3. Test Kiro Decision Quality (Priority 3)

**Goal**: Validate Kiro understands poker and gives good advice

**Test Scenarios**:

**Scenario 1: Strong Hand (AA, KK, AK)**
```
Setup: Get dealt premium hand
Action: Press F9
Expected: Kiro recommends RAISE
Actual: _____
Reasoning: _____
Quality: Good / OK / Bad
```

**Scenario 2: Weak Hand (72o, 83o)**
```
Setup: Get dealt trash hand
Action: Press F9
Expected: Kiro recommends FOLD
Actual: _____
Reasoning: _____
Quality: Good / OK / Bad
```

**Scenario 3: Drawing Hand (Suited Connectors)**
```
Setup: Get dealt 78s, flop comes 9-6-2
Action: Press F9
Expected: Kiro considers pot odds
Actual: _____
Reasoning: _____
Quality: Good / OK / Bad
```

**Success Criteria**:
- [ ] Strong hands → Raise/Call (not fold)
- [ ] Weak hands → Fold (not raise)
- [ ] Drawing hands → Considers pot odds
- [ ] Reasoning makes sense

**Time Estimate**: 30 minutes

---

## 🔧 Bug Fixes & Improvements (Week 1)

### Based on Testing Results

**If OCR Accuracy < 90%**:
1. Adjust preprocessing (contrast, brightness)
2. Try different Tesseract config
3. Add multiple OCR attempts
4. Implement confidence scoring

**If Kiro Decisions Poor**:
1. Improve prompt engineering
2. Add more poker context
3. Include position information
4. Add opponent modeling

**If Hotkeys Don't Work**:
1. Check keyboard library version
2. Test with administrator privileges
3. Add fallback hotkey system
4. Improve error messages

**If Calibration Fails**:
1. Add manual coordinate entry
2. Improve window detection
3. Add calibration validation
4. Better error messages

---

## 🎴 Card Recognition (Week 2)

### Current Status
- Shows '??' for all cards
- Bot works without card recognition
- Uses pot/stacks/actions only

### Implementation Plan

**Option 1: Template Matching (Fast)**
```python
# Already have synthetic templates
# Just need to integrate

1. Load card templates (52 cards)
2. Capture card regions
3. Match against templates
4. Return best match with confidence

Time: 2-3 hours
Accuracy: 70-85%
```

**Option 2: Real Card Capture (Better)**
```python
# Capture real cards from PokerStars
# Replace synthetic templates

1. User plays hands
2. Bot captures card images
3. User validates (correct/wrong)
4. Save real templates
5. Use for future matching

Time: 1 day
Accuracy: 90-95%
```

**Option 3: Machine Learning (Best)**
```python
# Train CNN for card recognition

1. Collect training data (1000+ cards)
2. Train model (ResNet/EfficientNet)
3. Deploy model
4. Real-time inference

Time: 1 week
Accuracy: 95-99%
```

**Recommendation**: Start with Option 1, upgrade to Option 2 based on results

---

## 🚀 Advanced Features (Week 3+)

### 1. Multi-Table Support
**Goal**: Play multiple tables simultaneously

**Implementation**:
- Detect multiple poker windows
- Track state per table
- Queue analysis requests
- Rotate between tables

**Time**: 3-4 days

---

### 2. Hand History Logging
**Goal**: Record all hands for analysis

**Implementation**:
- Log every hand state
- Log every decision
- Log outcomes
- Export to CSV/JSON

**Time**: 1 day

---

### 3. Strategy Profiles
**Goal**: Different playing styles

**Profiles**:
- Tight-Aggressive (TAG)
- Loose-Aggressive (LAG)
- Tight-Passive (Rock)
- Loose-Passive (Calling Station)

**Implementation**:
- Adjust Kiro prompts per profile
- Add profile selector in GUI
- Save profile preferences

**Time**: 2 days

---

### 4. Opponent Modeling
**Goal**: Track opponent tendencies

**Features**:
- Track opponent actions
- Calculate VPIP/PFR stats
- Adjust strategy per opponent
- Show opponent notes in overlay

**Time**: 1 week

---

### 5. Bankroll Management
**Goal**: Track wins/losses

**Features**:
- Track session results
- Calculate win rate
- Show graphs
- Set stop-loss limits

**Time**: 2-3 days

---

## 📊 Development Priorities

### Phase 1: Core Validation (This Week)
1. ✅ User testing on PokerStars
2. ✅ Measure OCR accuracy
3. ✅ Test Kiro decisions
4. ✅ Fix critical bugs

### Phase 2: Card Recognition (Week 2)
1. Implement template matching
2. Test accuracy
3. Capture real cards if needed
4. Optimize performance

### Phase 3: Production Ready (Week 3)
1. Multi-table support
2. Hand history logging
3. Strategy profiles
4. Performance optimization

### Phase 4: Advanced Features (Week 4+)
1. Opponent modeling
2. Bankroll management
3. Advanced statistics
4. Machine learning integration

---

## 🎯 Success Metrics

### Week 1 (Testing)
- [ ] OCR accuracy >90%
- [ ] Kiro decisions reasonable
- [ ] No crashes in 1 hour session
- [ ] All hotkeys working

### Week 2 (Card Recognition)
- [ ] Card recognition >85% accurate
- [ ] Full game state captured
- [ ] Response time <10 seconds

### Week 3 (Production)
- [ ] Multi-table support working
- [ ] Hand history logging
- [ ] Strategy profiles implemented
- [ ] Ready for extended use

---

## 📝 Testing Checklist

### Before Each Session
- [ ] Pull latest code
- [ ] Check server running
- [ ] Test connection
- [ ] Verify hotkeys work

### During Testing
- [ ] Record OCR accuracy
- [ ] Note any errors
- [ ] Copy Activity Log if issues
- [ ] Screenshot problems

### After Testing
- [ ] Report results
- [ ] Share logs if errors
- [ ] Suggest improvements
- [ ] Update documentation

---

## 🆘 How to Report Issues

**Format**:
```
ISSUE: [Brief description]
WHEN: [What you were doing]
EXPECTED: [What should happen]
ACTUAL: [What actually happened]
LOGS: [Activity Log - use Copy Logs button]
SCREENSHOTS: [GUI + poker table]
```

**Example**:
```
ISSUE: OCR reads $0 for pot
WHEN: Pressed F9 with $150 pot on table
EXPECTED: Should read ~$150
ACTUAL: Shows $0 in overlay
LOGS: [paste from Copy Logs]
SCREENSHOTS: [attached]
```

---

## 🎉 Current Status Summary

### ✅ What's Complete
- Server running (systemd service)
- Client connects to server
- Screenshot capture (background)
- Kiro CLI validation
- 7 hotkeys (all working)
- Mini overlay with guidance
- System tray
- Auto-hide main window
- Setup status detection
- Window geometry persistence
- Hotkey-based calibration

### 🔄 Ready for Testing
- OCR on real poker table
- Kiro decision quality
- Card recognition (shows '??')
- Full workflow validation

### 📝 Future Development
- Multi-table support
- Hand history logging
- Strategy profiles
- Opponent modeling
- Bankroll management

---

## 🚀 Let's Start Testing!

**Next Action**: Follow "Immediate Next Steps" above

**Time Required**: ~1-2 hours for complete testing

**Goal**: Validate entire system on real PokerStars table

**Ready?** Let's go! 🎰🤖

---

**Questions? Check USER_GUIDE.md or ask for help!**
