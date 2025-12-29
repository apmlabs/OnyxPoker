# OnyxPoker Testing Guide

## 🧪 Complete Testing Workflow

This guide walks you through testing the poker bot from setup to full automation.

---

## Phase 1: Server Setup & Testing (Linux)

### **Step 1: Clone and Setup**

```bash
# Clone repository
git clone https://github.com/apmlabs/OnyxPoker.git
cd OnyxPoker

# Navigate to server
cd server

# Run setup script
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Verify dependencies installed
pip list | grep -E "flask|pillow|requests"
```

**Expected Output:**
```
flask                2.3.3
flask-cors           4.0.0
pillow              10.0.1
requests            2.31.0
python-dotenv       1.0.0
```

### **Step 2: Configure Environment**

```bash
# Copy environment template
cp ../.env.example .env

# Edit configuration
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

### **Step 3: Test Kiro CLI**

```bash
# Verify Kiro CLI is accessible
which kiro-cli

# Test Kiro CLI response
echo "You are playing poker. You have AA. Pot is $100. Should you fold, call, or raise?" | kiro-cli chat
```

**Expected:** Kiro CLI should respond with poker advice.

### **Step 4: Start Server**

```bash
# Start Flask server
python app.py
```

**Expected Output:**
```
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server.
 * Running on http://0.0.0.0:5000
```

### **Step 5: Test Server Endpoints**

**Open new terminal:**

```bash
# Test health endpoint
curl http://localhost:5000/health

# Expected: {"status":"healthy","timestamp":"...","version":"1.0.0"}

# Test poker endpoint (with auth)
curl -X POST http://localhost:5000/analyze-poker \
  -H "Authorization: Bearer test_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "state": {
      "hero_cards": ["As", "Kh"],
      "community_cards": [],
      "pot": 150,
      "stacks": [500, 480, 500, 450, 520, 490],
      "actions": {"fold": "Fold", "call": "Call 20", "raise": "Raise"}
    }
  }'
```

**Expected Response:**
```json
{
  "action": "raise",
  "amount": 75,
  "reasoning": "With AK offsuit, raising is optimal..."
}
```

---

## Phase 2: Client Setup & Testing (Windows)

### **Step 1: Setup Client**

```cmd
REM Navigate to client folder
cd client

REM Run setup
setup.bat

REM Activate virtual environment
venv\Scripts\activate.bat

REM Verify dependencies
pip list | findstr "pyautogui pytesseract opencv"
```

**Expected:**
```
pyautogui         0.9.54
pytesseract       0.3.10
opencv-python     4.8.1.78
imagehash         4.3.1
```

### **Step 2: Install Tesseract OCR**

1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to: `C:\Program Files\Tesseract-OCR`
3. Add to PATH or set in code

**Test Tesseract:**
```cmd
tesseract --version
```

### **Step 3: Configure Client**

```cmd
REM Copy environment template
copy ..\.env.example .env

REM Edit .env
notepad .env
```

**Set these values:**
```bash
ONYXPOKER_SERVER_URL=http://YOUR_LINUX_IP:5000
ONYXPOKER_API_KEY=test_key_12345
```

### **Step 4: Launch GUI**

```cmd
python poker_gui.py
```

**Expected:** GUI window opens with:
- Settings panel
- Control buttons
- Status display
- Game state panel
- Activity log

### **Step 5: Test Connection**

In GUI:
1. Click "🔧 Test Connection" button
2. **Expected:** Success message popup
3. **Check log:** Should show "✅ Server connection successful!"

**If fails:** Check server is running and .env has correct URL

---

## Phase 3: Screen Calibration

### **Step 1: Open PokerStars**

1. Open PokerStars client
2. Join a **play money** table (6-max)
3. Position table window consistently
4. Note the window position

### **Step 2: Find Coordinates**

**Run this script:**
```python
import pyautogui
import time

print("Move mouse to corners and press Ctrl+C")
print("Recording positions in 3 seconds...")
time.sleep(3)

try:
    while True:
        x, y = pyautogui.position()
        print(f"Position: ({x}, {y})")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nDone!")
```

**Record these positions:**
- Table top-left corner
- Table bottom-right corner
- Your card 1 position
- Your card 2 position
- Pot text location
- Fold button
- Call button
- Raise button

### **Step 3: Update config.py**

```python
# Example for 1920x1080 screen with table at (100, 100)
TABLE_REGION = (100, 100, 800, 600)

HOLE_CARD_REGIONS = [
    (350, 500, 50, 70),  # Card 1
    (420, 500, 50, 70),  # Card 2
]

POT_REGION = (450, 250, 100, 30)

BUTTON_REGIONS = {
    "fold": (300, 580, 80, 40),
    "call": (400, 580, 80, 40),
    "raise": (500, 580, 80, 40),
}
```

---

## Phase 4: OCR Testing

### **Test 1: Pot Reading**

```python
from poker_reader import PokerScreenReader
import config

reader = PokerScreenReader()

# Sit at table with visible pot
pot = reader.get_pot_size()
print(f"Pot detected: ${pot}")
```

**Expected:** Should read pot amount (e.g., `Pot detected: $150`)

### **Test 2: Stack Reading**

```python
stacks = reader.get_stack_sizes()
print(f"Stacks: {stacks}")
```

**Expected:** List of 6 stack sizes (e.g., `[500, 480, 500, 0, 0, 0]`)

### **Test 3: Button Detection**

```python
# Wait for your turn
actions = reader.get_action_buttons()
print(f"Actions: {actions}")
```

**Expected:** `{'fold': 'Fold', 'call': 'Call 20', 'raise': 'Raise'}`

### **Test 4: Turn Detection**

```python
# Wait for your turn
is_turn = reader.is_hero_turn()
print(f"Is my turn: {is_turn}")
```

**Expected:** `True` when it's your turn, `False` otherwise

### **Test 5: Full State**

```python
state = reader.parse_game_state()
print(f"Full state: {state}")
```

**Expected:**
```python
{
    'hero_cards': ['??', '??'],
    'community_cards': [],
    'pot': 150,
    'stacks': [500, 480, 500, 450, 520, 490],
    'actions': {'fold': 'Fold', 'call': 'Call 20', 'raise': 'Raise'}
}
```

---

## Phase 5: Bot Testing (Analysis Mode)

### **Test 1: Single Hand Analysis**

```cmd
python poker_bot.py --execution analysis --hands 1
```

**What to expect:**
1. Bot waits for your turn
2. Captures game state
3. Sends to Kiro CLI
4. Displays decision
5. Does NOT click anything

**Example Output:**
```
🎰 OnyxPoker Bot initialized
   Mode: remote
   Execution: analysis

⏳ Waiting for your turn...

==================================================
🃏 Hand 1
==================================================
Cards: ['??', '??']
Board: []
Pot: $150
Stack: $500
Actions: {'fold': 'Fold', 'call': 'Call 20', 'raise': 'Raise'}

💡 Decision: CALL $20
📝 Reasoning: With unknown cards, calling is safe to see the flop...
ℹ️  [ANALYSIS MODE - No action taken]

🛑 Bot stopped. Hands played: 1
```

### **Test 2: Multiple Hands**

```cmd
python poker_bot.py --execution analysis --hands 5
```

**What to test:**
- Bot waits between hands
- Correctly detects each turn
- Provides different decisions based on state
- Logs all decisions

### **Test 3: Continuous Analysis**

```cmd
python poker_bot.py --execution analysis
```

**What to test:**
- Runs indefinitely until Ctrl+C
- Handles table changes
- Recovers from errors
- Consistent performance

---

## Phase 6: Decision Quality Testing

### **Test Different Scenarios**

**Scenario 1: Strong Hand**
- Manually play until you get AA, KK, or AK
- Let bot analyze
- **Expected:** Should recommend raise

**Scenario 2: Weak Hand**
- Get 72o (worst hand)
- Let bot analyze
- **Expected:** Should recommend fold

**Scenario 3: Drawing Hand**
- Get suited connectors on a draw-heavy board
- Let bot analyze
- **Expected:** Should consider pot odds

**Scenario 4: All-in Situation**
- Face an all-in bet
- Let bot analyze
- **Expected:** Should evaluate risk carefully

### **Log Analysis**

Create a log file:
```cmd
python poker_bot.py --execution analysis > poker_log.txt
```

**Analyze logs for:**
- Decision consistency
- Reasoning quality
- Response time
- Error handling

---

## Phase 7: Performance Testing

### **Test 1: Response Time**

```python
import time
from poker_reader import PokerScreenReader

reader = PokerScreenReader()

# Time full cycle
start = time.time()
state = reader.parse_game_state()
elapsed = time.time() - start

print(f"OCR time: {elapsed:.2f}s")
# Target: < 2 seconds
```

### **Test 2: Server Response Time**

```python
from automation_client import OnyxPokerClient
import time

client = OnyxPokerClient()
state = {'hero_cards': ['As', 'Kh'], 'pot': 100, 'stacks': [500]*6, 'actions': {}}

start = time.time()
# Make request
elapsed = time.time() - start

print(f"Server response: {elapsed:.2f}s")
# Target: < 5 seconds
```

### **Test 3: Full Cycle Time**

```cmd
REM Run bot and time first decision
python poker_bot.py --execution analysis --hands 1
```

**Measure:** Time from "your turn" to decision displayed
**Target:** < 10 seconds total

---

## Phase 8: Error Handling Testing

### **Test 1: Server Disconnect**

1. Stop Flask server
2. Run bot
3. **Expected:** Should show connection error, not crash

### **Test 2: OCR Failure**

1. Minimize PokerStars window
2. Run bot
3. **Expected:** Should return 0 for pot/stacks, not crash

### **Test 3: Invalid State**

1. Send malformed state to server
2. **Expected:** Should return fold decision

### **Test 4: Timeout**

1. Simulate slow Kiro CLI response
2. **Expected:** Should timeout and fold

---

## Phase 9: Full Automation Testing (CAREFUL!)

### **⚠️ ONLY ON PLAY MONEY TABLES**

### **Test 1: Single Hand Automation**

```cmd
python poker_bot.py --execution auto --hands 1
```

**What happens:**
1. Bot waits for turn
2. Analyzes state
3. **CLICKS the button**
4. Executes action

**Watch carefully:** Make sure it clicks correctly!

### **Test 2: Verify Click Accuracy**

- Does it click the right button?
- Does it type amounts correctly?
- Does it confirm raises?

### **Test 3: Multi-Hand Automation**

```cmd
python poker_bot.py --execution auto --hands 3
```

**Monitor:**
- Timing between actions
- Decision quality
- No errors or crashes

---

## Troubleshooting Guide

### **Problem: "Cannot connect to server"**

**Solutions:**
1. Check server is running: `curl http://localhost:5000/health`
2. Check firewall: `sudo ufw allow 5000`
3. Verify API key matches in both .env files
4. Check server IP in client .env

### **Problem: "OCR returns 0 for everything"**

**Solutions:**
1. Install Tesseract: Download from GitHub
2. Add to PATH: `set PATH=%PATH%;C:\Program Files\Tesseract-OCR`
3. Verify table is visible: Check TABLE_REGION coordinates
4. Test manually: `pytesseract.image_to_string(image)`

### **Problem: "Bot doesn't detect turn"**

**Solutions:**
1. Check button OCR: `reader.get_action_buttons()`
2. Adjust BUTTON_REGIONS in config.py
3. Verify PokerStars theme (use default theme)
4. Check is_hero_turn() logic

### **Problem: "Kiro CLI timeout"**

**Solutions:**
1. Test Kiro CLI: `echo "test" | kiro-cli chat`
2. Increase timeout in poker_strategy.py
3. Simplify prompts
4. Check Kiro CLI installation

### **Problem: "Wrong button clicked"**

**Solutions:**
1. Recalibrate BUTTON_REGIONS
2. Add delays: Increase ACTION_DELAY
3. Verify screen resolution hasn't changed
4. Test with pyautogui.click() manually

---

## Success Criteria

### **Phase 1-2: Setup** ✅
- [ ] Server starts without errors
- [ ] Client connects to server
- [ ] Kiro CLI responds to prompts

### **Phase 3-4: Calibration** ✅
- [ ] OCR reads pot correctly (±10%)
- [ ] OCR reads stacks correctly (±10%)
- [ ] Turn detection works reliably

### **Phase 5: Analysis Mode** ✅
- [ ] Bot detects turns correctly
- [ ] Decisions are reasonable
- [ ] No crashes over 10+ hands
- [ ] Response time < 10 seconds

### **Phase 6: Decision Quality** ✅
- [ ] Strong hands → Raise
- [ ] Weak hands → Fold
- [ ] Reasonable sizing
- [ ] Consistent logic

### **Phase 7: Performance** ✅
- [ ] OCR < 2 seconds
- [ ] Server response < 5 seconds
- [ ] Total cycle < 10 seconds

### **Phase 8: Error Handling** ✅
- [ ] Handles disconnects gracefully
- [ ] Recovers from OCR failures
- [ ] Timeouts don't crash bot

### **Phase 9: Automation** ✅
- [ ] Clicks correct buttons
- [ ] Types amounts correctly
- [ ] Completes hands successfully

---

## Next Steps After Testing

1. **Improve OCR**: Add card template matching
2. **Optimize Prompts**: Refine Kiro CLI prompts for better decisions
3. **Add Logging**: Comprehensive decision logging
4. **Performance Tuning**: Optimize for speed
5. **Multi-table**: Support multiple tables

---

## Safety Reminders

⚠️ **ALWAYS:**
- Test on play money tables first
- Start with analysis mode
- Monitor the bot closely
- Have emergency stop ready (Ctrl+C)

⚠️ **NEVER:**
- Use on real money without extensive testing
- Leave bot unattended
- Use on sites that prohibit bots
- Ignore terms of service

---

**Ready to test! Start with Phase 1 and work through each phase systematically.** 🧪✅
