# Testing OnyxPoker Bot - Quick Guide

## Prerequisites

1. **OpenAI API Key**
   - Go to https://platform.openai.com/api-keys
   - Create new key (starts with `sk-`)
   - Copy it

2. **PokerStars Play Money Account**
   - Download PokerStars
   - Create account
   - Go to play money tables

3. **Windows Machine**
   - Python 3.8+
   - Display (not headless)

---

## Setup (5 minutes)

### 1. Install Dependencies
```bash
cd client
pip install -r requirements.txt
```

### 2. Set API Key
```bash
# Windows CMD
set OPENAI_API_KEY=sk-your-key-here

# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-key-here"

# Or create .env file
echo OPENAI_API_KEY=sk-your-key-here > .env
```

### 3. Launch GUI
```bash
python poker_gui.py
```

---

## Calibration (2 minutes)

1. **Open PokerStars**
   - Sit at play money table
   - Make window visible

2. **Calibrate**
   - Click on PokerStars window (to focus it)
   - Press **F8** in OnyxPoker GUI
   - Wait 5-10 seconds (GPT-4o analyzing)
   - Review preview with colored boxes
   - Click "Save Configuration"

3. **Test (Optional)**
   - Press **F5** to test OCR
   - Check if pot/stacks read correctly

---

## Testing Modes

### Mode 1: Advice Only (Recommended First)

**What it does**: Shows recommendations, you click manually

**Steps**:
1. In GUI Control Panel:
   - Mode: `remote` (or `local`)
   - Execution: **`analysis`** ← Important!
   - Max Hands: `10`

2. Press **F10** (Start Bot)

3. Play poker normally:
   - When your turn comes
   - Bot shows: "💡 Recommended: RAISE $60"
   - Bot shows: "📝 Strong hand with straight draw"
   - **You click manually**

4. Bot waits for next turn

5. Press **F11** to stop

**Expected**:
- ✅ Bot detects your turn
- ✅ Shows recommendation
- ✅ Shows reasoning
- ✅ Doesn't click anything
- ✅ You stay in control

---

### Mode 2: Auto-Play (After Testing Advice)

**What it does**: Bot clicks buttons automatically

**Steps**:
1. In GUI Control Panel:
   - Mode: `remote`
   - Execution: **`auto`** ← Bot will click!
   - Max Hands: `5` (start small)

2. Press **F10** (Start Bot)

3. **Don't touch mouse/keyboard**:
   - Bot monitors table
   - When your turn: bot clicks
   - Watch Activity Log

4. Press **F11** to emergency stop

**Expected**:
- ✅ Bot detects turn
- ✅ Bot clicks fold/call/raise
- ✅ Bot types raise amounts
- ✅ Actions execute correctly

---

## What to Watch

### Activity Log (in GUI)
```
🃏 Hand 1
Cards: ['As', 'Kh'], Pot: $150
💡 Recommended: RAISE $60
📝 Strong hand with straight draw, good pot odds
✅ Executed: raise
```

### Mini Overlay (always visible)
```
┌─────────────────────────┐
│ 🎰 OnyxPoker            │
│ ─────────────────────── │
│ Table: $150 pot         │
│ Cards: A♠ K♥            │
│ Stack: $500             │
│ ─────────────────────── │
│ 💡 RAISE $60            │
│ Strong hand             │
└─────────────────────────┘
```

---

## Troubleshooting

### "OPENAI_API_KEY not found"
- Set environment variable
- Or create `.env` file in client/ folder

### "No actions detected"
- Wait for your turn
- Make sure buttons are visible
- Try F8 to recalibrate

### "Bot doesn't click"
- Check Execution mode is `auto`
- Check PokerStars window is visible
- Check button positions in calibration

### "Wrong button clicked"
- Recalibrate with F8
- GPT-4o will detect new positions

### "Too slow"
- Normal: 5-10 seconds per decision
- GPT-4o API takes 3-5 seconds
- Can't be faster (API limitation)

---

## Performance Metrics

### Expected Results

**Vision Accuracy**: 95%+
- Cards: Should read correctly
- Pot: Should read correctly
- Stacks: Should read correctly

**Decision Quality**: Reasonable
- Strong hands: Raise/Call
- Weak hands: Fold
- Drawing hands: Consider pot odds

**Response Time**: 5-10 seconds
- Screenshot: 0.5s
- GPT-4o API: 3-5s
- Click: 0.5s

**Error Rate**: <5%
- Occasional misreads
- Occasional wrong decisions
- Should be rare

---

## Cost Tracking

**Per Hand**: ~$0.002
**10 hands**: ~$0.02
**100 hands**: ~$0.20
**1000 hands**: ~$2.00

Check your OpenAI usage at: https://platform.openai.com/usage

---

## Safety Tips

1. **Start with Advice Mode**
   - Test before auto-play
   - Verify decisions make sense

2. **Use Play Money**
   - Never test on real money
   - PokerStars play money is free

3. **Monitor First Session**
   - Watch Activity Log
   - Check decisions are reasonable
   - Stop if anything wrong (F11)

4. **Start Small**
   - Max Hands: 5-10 first time
   - Increase after successful test

5. **Emergency Stop**
   - F11 stops bot immediately
   - Or close GUI window

---

## Reporting Results

After testing, report:

1. **Vision Accuracy**
   - Did it read cards correctly?
   - Did it read pot correctly?
   - Any misreads?

2. **Decision Quality**
   - Were decisions reasonable?
   - Any obviously bad plays?
   - Did reasoning make sense?

3. **Execution**
   - Did buttons click correctly?
   - Did raise amounts work?
   - Any errors?

4. **Performance**
   - How long per decision?
   - Any crashes?
   - Any freezes?

---

## Next Steps After Testing

If everything works:
- ✅ Increase max hands
- ✅ Try multi-tabling (future)
- ✅ Collect hand history
- ✅ Analyze performance

If issues found:
- Report in Activity Log
- Copy error messages
- Take screenshots
- We'll fix and iterate

---

**Ready to test!** Start with Advice Mode, then try Auto-Play. Good luck! 🎰
