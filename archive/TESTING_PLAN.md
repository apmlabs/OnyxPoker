# OnyxPoker Testing Plan - Step by Step

**Date**: December 29, 2025  
**Goal**: Test poker bot from setup to full operation  
**Duration**: ~2-3 hours

---

## 🎯 Testing Objectives

1. Verify server setup and Kiro CLI integration
2. Test client GUI and controls
3. Calibrate screen regions for OCR
4. Validate decision-making quality
5. Test full automation (play money only)

---

## 📋 Pre-Testing Checklist

### **What You Need:**
- [ ] Linux server (AWS or local) with Kiro CLI installed
- [ ] Windows machine with Python 3.8+
- [ ] PokerStars client installed
- [ ] Play money account on PokerStars
- [ ] Tesseract OCR installed on Windows
- [ ] Network connection between Windows and Linux

### **Before Starting:**
- [ ] Close unnecessary applications
- [ ] Ensure stable internet connection
- [ ] Have notepad ready for recording coordinates
- [ ] Prepare to take screenshots if issues occur

---

## 🧪 Testing Phases

---

## **PHASE 1: Server Setup (15 minutes)**

### **Step 1.1: Clone Repository**

**On Linux server:**
```bash
cd ~
git clone https://github.com/apmlabs/OnyxPoker.git
cd OnyxPoker
```

**✅ Success:** Repository cloned, you see project files

**❌ If fails:** 
- Check GitHub access
- Verify git is installed: `git --version`
- **Report:** "Cannot clone repo: [error message]"

---

### **Step 1.2: Setup Server**

```bash
cd server
./setup.sh
```

**✅ Success:** 
```
Server setup complete!
To start the server:
  source venv/bin/activate
  python app.py
```

**❌ If fails:**
- Check Python version: `python3 --version` (need 3.8+)
- Check permissions: `chmod +x setup.sh`
- **Report:** "Setup failed at: [step] with error: [message]"

---

### **Step 1.3: Configure Environment**

```bash
cp ../.env.example .env
nano .env
```

**Set these values:**
```bash
API_KEY=test_key_12345
FLASK_PORT=5000
FLASK_HOST=0.0.0.0
DEBUG=True
KIRO_CLI_PATH=kiro-cli
```

**Save:** Ctrl+O, Enter, Ctrl+X

**✅ Success:** File saved with your values

**❌ If fails:**
- Use `vi .env` instead of nano
- **Report:** "Cannot edit .env: [error]"

---

### **Step 1.4: Test Kiro CLI**

```bash
which kiro-cli
echo "You are playing poker with AA. Pot is $100. Should you fold, call, or raise?" | kiro-cli chat
```

**✅ Success:** Kiro CLI responds with poker advice

**❌ If fails:**
- Check Kiro CLI installation
- Try full path: `/usr/local/bin/kiro-cli`
- **Report:** "Kiro CLI not found or error: [message]"

---

### **Step 1.5: Start Server**

```bash
source venv/bin/activate
python app.py
```

**✅ Success:**
```
 * Serving Flask app 'app'
 * Running on http://0.0.0.0:5000
```

**❌ If fails:**
- Check port 5000 not in use: `lsof -i :5000`
- Check firewall: `sudo ufw allow 5000`
- **Report:** "Server won't start: [error]"

---

### **Step 1.6: Test Server (New Terminal)**

```bash
curl http://localhost:5000/health
```

**✅ Success:**
```json
{"status":"healthy","timestamp":"...","version":"1.0.0"}
```

**❌ If fails:**
- Check server is running
- Try: `curl http://127.0.0.1:5000/health`
- **Report:** "Health check failed: [response]"

---

### **Step 1.7: Test Poker Endpoint**

```bash
curl -X POST http://localhost:5000/analyze-poker \
  -H "Authorization: Bearer test_key_12345" \
  -H "Content-Type: application/json" \
  -d '{"state":{"hero_cards":["As","Kh"],"pot":150,"stacks":[500,480,500,450,520,490],"actions":{"fold":"Fold","call":"Call 20","raise":"Raise"}}}'
```

**✅ Success:** JSON response with action, amount, reasoning

**❌ If fails:**
- Check API_KEY matches in .env
- Check Kiro CLI is working
- **Report:** "Poker endpoint error: [response]"

---

**📊 Phase 1 Complete!**
- [ ] Server running
- [ ] Health check passes
- [ ] Kiro CLI responds
- [ ] Poker endpoint works

**Note server IP for Phase 2:** `_________________`

---

## **PHASE 2: Client Setup (20 minutes)**

### **Step 2.1: Clone on Windows**

**Open Command Prompt:**
```cmd
cd C:\
git clone https://github.com/apmlabs/OnyxPoker.git
cd OnyxPoker\client
```

**✅ Success:** Repository cloned

**❌ If fails:**
- Install git for Windows
- Download ZIP from GitHub instead
- **Report:** "Cannot clone on Windows: [error]"

---

### **Step 2.2: Run Setup**

```cmd
setup.bat
```

**✅ Success:**
```
Client setup complete!
To run the client:
  venv\Scripts\activate.bat
  python poker_gui.py
```

**❌ If fails:**
- Check Python installed: `python --version`
- Install Python 3.8+ from python.org
- **Report:** "Setup.bat failed: [error]"

---

### **Step 2.3: Install Tesseract OCR**

1. Download: https://github.com/UB-Mannheim/tesseract/wiki
2. Run installer
3. Install to: `C:\Program Files\Tesseract-OCR`
4. Add to PATH (installer option)

**Test:**
```cmd
tesseract --version
```

**✅ Success:** Shows version number

**❌ If fails:**
- Manually add to PATH
- Set in code: `pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'`
- **Report:** "Tesseract not working: [error]"

---

### **Step 2.4: Configure Client**

```cmd
copy ..\.env.example .env
notepad .env
```

**Set these values:**
```bash
ONYXPOKER_SERVER_URL=http://YOUR_SERVER_IP:5000
ONYXPOKER_API_KEY=test_key_12345
```

**Replace YOUR_SERVER_IP with actual IP from Phase 1**

**✅ Success:** File saved

**❌ If fails:**
- Check server IP is correct
- Try localhost if same machine
- **Report:** "Cannot configure .env: [error]"

---

### **Step 2.5: Launch GUI**

```cmd
venv\Scripts\activate.bat
python poker_gui.py
```

**✅ Success:** GUI window opens with all panels visible

**❌ If fails:**
- Check tkinter: `python -c "import tkinter"`
- Install if needed: `pip install tk`
- **Report:** "GUI won't start: [error]" + screenshot

---

### **Step 2.6: Test Connection**

**In GUI:**
1. Click "🔧 Test Connection" button
2. Wait for response

**✅ Success:** 
- Popup: "Connected to server!"
- Log shows: "✅ Server connection successful!"

**❌ If fails:**
- Check server is running
- Check firewall on server
- Verify .env has correct URL
- **Report:** "Connection test failed: [error message from popup]"

---

**📊 Phase 2 Complete!**
- [ ] Client installed
- [ ] Tesseract working
- [ ] GUI launches
- [ ] Connects to server

---

## **PHASE 3: Screen Calibration (30 minutes)**

### **Step 3.1: Open PokerStars**

1. Launch PokerStars
2. Login to play money account
3. Join a 6-max No-Limit Hold'em table
4. **Important:** Position table window consistently (same spot every time)

**✅ Success:** Seated at table, can see cards/buttons

---

### **Step 3.2: Find Table Coordinates**

**Create test script:** `find_coords.py`
```python
import pyautogui
import time

print("Move mouse to TABLE TOP-LEFT corner, press Ctrl+C")
time.sleep(3)
try:
    while True:
        x, y = pyautogui.position()
        print(f"Position: ({x}, {y})", end='\r')
        time.sleep(0.1)
except KeyboardInterrupt:
    print(f"\nRecorded: ({x}, {y})")
```

**Run:**
```cmd
python find_coords.py
```

**Record these positions:**

1. **Table top-left:** `(_____, _____)`
2. **Table bottom-right:** `(_____, _____)`
3. **Your card 1 (top-left):** `(_____, _____)`
4. **Your card 1 (bottom-right):** `(_____, _____)`
5. **Your card 2 (top-left):** `(_____, _____)`
6. **Your card 2 (bottom-right):** `(_____, _____)`
7. **Pot text (top-left):** `(_____, _____)`
8. **Pot text (bottom-right):** `(_____, _____)`
9. **Fold button (center):** `(_____, _____)`
10. **Call button (center):** `(_____, _____)`
11. **Raise button (center):** `(_____, _____)`

---

### **Step 3.3: Update config.py**

**Edit:** `client/config.py`

```python
# Calculate from your coordinates
TABLE_REGION = (top_left_x, top_left_y, width, height)

HOLE_CARD_REGIONS = [
    (card1_x, card1_y, card1_width, card1_height),
    (card2_x, card2_y, card2_width, card2_height),
]

POT_REGION = (pot_x, pot_y, pot_width, pot_height)

BUTTON_REGIONS = {
    "fold": (fold_x, fold_y, button_width, button_height),
    "call": (call_x, call_y, button_width, button_height),
    "raise": (raise_x, raise_y, button_width, button_height),
}
```

**✅ Success:** File saved with your coordinates

---

### **Step 3.4: Test OCR**

**In GUI:**
1. Make sure PokerStars table is visible
2. Click "📸 Test OCR" button

**✅ Success:**
- Popup shows pot and stack values
- Log shows OCR results
- Game State panel updates

**❌ If fails:**
- Values are 0 or wrong
- **Report:** "OCR test results: Pot=$[value], Stacks=[values]" + screenshot of table

---

**📊 Phase 3 Complete!**
- [ ] Table positioned
- [ ] Coordinates recorded
- [ ] config.py updated
- [ ] OCR reads values

---

## **PHASE 4: Bot Testing - Analysis Mode (30 minutes)**

### **Step 4.1: Configure Bot**

**In GUI:**
1. Mode: Select "Remote (Server)"
2. Execution: Select "Analysis Only"
3. Max Hands: Enter "3"

---

### **Step 4.2: Start Bot**

1. Sit at PokerStars table
2. Wait for a hand to start
3. Click "▶ Start Bot" in GUI

**✅ Success:**
- Status changes to "Waiting for turn"
- Log shows "Bot started, waiting for your turn..."

**❌ If fails:**
- Button stays disabled
- Error in log
- **Report:** "Bot won't start: [log message]" + screenshot

---

### **Step 4.3: Observe First Hand**

**When it's your turn:**

**✅ Success:**
- Status changes to "Playing"
- Game State panel updates with:
  - Cards (may show ??)
  - Board
  - Pot amount
  - Stack amount
- Decision panel shows:
  - Action (FOLD/CALL/RAISE)
  - Reasoning from Kiro CLI
- Log shows decision
- **NO CLICKING** (analysis mode)

**❌ If fails:**
- Bot doesn't detect turn
- OCR values wrong
- No decision shown
- **Report:** "Hand 1 issue: [describe]" + screenshot of GUI + screenshot of table

---

### **Step 4.4: Record Results**

**For each of 3 hands, record:**

**Hand 1:**
- Pot: $______
- Stack: $______
- Decision: ______
- Reasoning: ______________________
- Correct? (Y/N): ___

**Hand 2:**
- Pot: $______
- Stack: $______
- Decision: ______
- Reasoning: ______________________
- Correct? (Y/N): ___

**Hand 3:**
- Pot: $______
- Stack: $______
- Decision: ______
- Reasoning: ______________________
- Correct? (Y/N): ___

---

### **Step 4.5: Stop Bot**

Click "⏹ Stop Bot"

**✅ Success:**
- Status changes to "Stopped"
- Hands played shows 3
- Start button re-enabled

---

**📊 Phase 4 Complete!**
- [ ] Bot detects turns
- [ ] OCR reads game state
- [ ] Kiro CLI makes decisions
- [ ] No crashes

---

## **PHASE 5: Full Automation (CAREFUL!) (20 minutes)**

### **⚠️ CRITICAL WARNINGS:**
- **ONLY on play money tables**
- **Watch closely** - bot will click
- **Be ready to stop** - Ctrl+C or Stop button
- **Test with 1 hand first**

---

### **Step 5.1: Configure for Auto**

**In GUI:**
1. Mode: "Remote (Server)"
2. Execution: "Auto (Clicks)" ⚠️
3. Max Hands: "1"

---

### **Step 5.2: Single Hand Test**

1. Wait for new hand
2. Click "▶ Start Bot"
3. **WATCH CLOSELY**

**✅ Success:**
- Bot detects turn
- Shows decision
- **CLICKS the button**
- Action executes on table
- Hand completes

**❌ If fails:**
- Clicks wrong button
- Clicks wrong position
- Doesn't click
- Crashes
- **Report:** "Auto mode issue: [describe]" + video if possible

---

### **Step 5.3: Verify Click Accuracy**

**Check:**
- [ ] Clicked correct button (fold/call/raise)
- [ ] Typed amount correctly (if raise)
- [ ] Action executed on table
- [ ] No errors

---

**📊 Phase 5 Complete!**
- [ ] Auto mode works
- [ ] Clicks are accurate
- [ ] Actions execute

---

## 📝 How to Report Issues

### **Format for Feedback:**

```
ISSUE: [Brief description]
PHASE: [Phase number and step]
EXPECTED: [What should happen]
ACTUAL: [What actually happened]
ERROR MESSAGE: [Exact error text]
SCREENSHOTS: [Attach if relevant]
LOGS: [Copy from GUI log panel]
```

### **Example:**

```
ISSUE: OCR returns 0 for pot
PHASE: 3.4 - Test OCR
EXPECTED: Should read pot amount from table
ACTUAL: Always returns $0
ERROR MESSAGE: None
SCREENSHOTS: [table.png, gui.png]
LOGS:
[12:34:56] INFO: Testing OCR...
[12:34:57] INFO: OCR Result: {"pot": 0, "stacks": [0,0,0,0,0,0]}
```

---

## ✅ Success Criteria

### **Minimum for Success:**
- [ ] Server starts and responds
- [ ] Client connects to server
- [ ] OCR reads pot/stacks (±20% accuracy acceptable)
- [ ] Bot detects turns
- [ ] Kiro CLI provides decisions
- [ ] Analysis mode works for 3+ hands
- [ ] No crashes

### **Ideal Success:**
- [ ] OCR accuracy >90%
- [ ] Turn detection 100% reliable
- [ ] Decisions are reasonable
- [ ] Response time <10 seconds
- [ ] Auto mode clicks correctly

---

## 🔧 Quick Troubleshooting

### **Server won't start:**
- Check port 5000: `lsof -i :5000`
- Check Kiro CLI: `which kiro-cli`
- Check logs: `tail -f logs/app.log`

### **Client can't connect:**
- Ping server: `ping SERVER_IP`
- Check firewall: `telnet SERVER_IP 5000`
- Verify API key matches

### **OCR returns 0:**
- Check Tesseract: `tesseract --version`
- Verify table visible
- Check coordinates in config.py
- Try different PokerStars theme

### **Bot doesn't detect turn:**
- Check button OCR in log
- Verify BUTTON_REGIONS coordinates
- Test is_hero_turn() logic

---

## 📊 Testing Timeline

- **Phase 1**: 15 min - Server setup
- **Phase 2**: 20 min - Client setup
- **Phase 3**: 30 min - Calibration
- **Phase 4**: 30 min - Analysis testing
- **Phase 5**: 20 min - Auto testing
- **Total**: ~2 hours

---

## 🎯 Next Steps After Testing

1. **If successful:** Document settings, start research
2. **If issues:** Report with format above, we'll fix
3. **Improvements:** Card recognition, better prompts, multi-table

---

**Ready to test! Start with Phase 1 and report any issues immediately.** 🧪✅
