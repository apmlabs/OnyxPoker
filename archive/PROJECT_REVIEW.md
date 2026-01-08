# OnyxPoker - Comprehensive Project Review
**Date**: December 29, 2025 20:33 UTC  
**Review Type**: Architecture, Goals, and Direction Assessment

---

## Executive Summary

**Current State**: We have a sophisticated calibration system with computer vision, but **the core poker bot functionality is incomplete**.

**Original Goal**: AI-powered poker bot that reads tables and makes decisions  
**Current Reality**: Advanced calibration tool with minimal poker automation

**Gap**: We focused heavily on calibration UX but haven't implemented the actual poker playing logic.

---

## Project Architecture

### Backend (Linux Server)

**Location**: `/home/ubuntu/mcpprojects/onyxpoker-server/`  
**Main File**: `server/app.py` (~200 lines)

**What It Does**:
```python
Flask API Server
├── GET /health - Health check
├── POST /analyze-poker - Poker decision endpoint
│   └── Calls Kiro CLI with poker prompt
│   └── Returns: {action, amount, reasoning}
└── POST /detect-elements - Vision-based detection (non-functional)
    └── Attempted Kiro CLI vision (doesn't work)
```

**AI Integration**:
- Uses Kiro CLI subprocess calls
- Builds poker-specific prompts
- Parses text responses for decisions
- **Status**: Basic implementation, untested on real poker

**Dependencies**:
- Flask (web framework)
- subprocess (Kiro CLI calls)
- python-dotenv (config)
- Pillow (image handling)

---

### Frontend (Windows Client)

**Location**: `/home/ubuntu/mcpprojects/onyxpoker/client/`

#### Core Files

**1. poker_gui.py** (~1,400 lines) - Main GUI
```
4 Tabs:
├── Control Panel - Bot controls, game state, decisions
├── Calibration - F7/F8 workflow, preview, save
├── Debug - OCR testing, validation
└── Help - Setup guide, hotkeys
```

**2. hotkey_manager.py** (~200 lines) - Global hotkeys
```
F5: Test OCR (debug)
F6: Toggle overlay
F7: Open calibration tab
F8: Capture & detect (single-step)
F9: Analyze with Kiro
F10: Start/stop bot
F11: Emergency stop
F12: Toggle main window
```

**3. window_detector.py** (~200 lines) - Computer vision
```
Smart OCR Detection:
├── Looks for button text (Fold/Call/Raise)
├── Buttons must be in bottom 20%
├── Pot = largest number in center
└── Uses relative positioning
```

**4. poker_reader.py** (~150 lines) - OCR
```
Reads:
├── Pot amount (from POT_REGION)
├── Stack amounts (from STACK_REGIONS)
├── Available actions (from BUTTON_REGIONS)
└── Cards (placeholder '??' - NOT IMPLEMENTED)
```

**5. automation_client.py** (~200 lines) - HTTP client
```
Endpoints:
├── POST /analyze-poker - Get decision
└── POST /validate-state - Validate with Kiro
```

**6. poker_bot.py** (~100 lines) - Bot orchestrator
```
Main Loop:
├── Wait for turn
├── Parse game state
├── Get decision from server
└── Execute action (NOT IMPLEMENTED)
```

**7. mini_overlay.py** (~250 lines) - Always-on-top panel
```
Shows:
├── Game state (pot, cards, stack)
├── AI decision
└── Next step instructions
```

**8. system_tray.py** (~100 lines) - System tray icon

---

## Data Flow

### Current Workflow

```
1. CALIBRATION (F7 → F8 → Save)
   User clicks poker window
   ↓
   F8: Capture active window
   ↓
   window_detector.py: Smart OCR detection
   ↓
   Finds buttons (text-based) and pot (largest number)
   ↓
   Shows preview with colored boxes
   ↓
   User saves → writes config.py

2. OCR TESTING (F5)
   F5: Capture screenshot
   ↓
   poker_reader.py: Read regions from config.py
   ↓
   pytesseract OCR on each region
   ↓
   Shows results in Debug tab

3. ANALYSIS (F9)
   F9: Capture screenshot
   ↓
   poker_reader.py: Parse game state
   ↓
   automation_client.py: HTTP POST to server
   ↓
   server/app.py: Build poker prompt
   ↓
   Kiro CLI subprocess
   ↓
   Parse response → return decision
   ↓
   Update overlay with decision
```

---

## What Works vs What Doesn't

### ✅ What Works

1. **Calibration System**
   - F8 captures active window
   - Smart OCR finds buttons by text
   - Finds pot by looking for largest number in center
   - Saves config.py with regions
   - Preview shows detection results

2. **OCR Testing**
   - F5 captures screenshot
   - Reads pot/stacks from configured regions
   - Shows results in Debug tab

3. **Server Communication**
   - Client connects to server
   - Server receives requests
   - Kiro CLI responds with poker advice

4. **UI/UX**
   - Global hotkeys work
   - Mini overlay shows status
   - Main GUI has 4 organized tabs
   - Activity log tracks everything

### ❌ What Doesn't Work

1. **Card Recognition**
   - Shows '??' for all cards
   - No template matching implemented
   - No real card detection

2. **Action Execution**
   - Bot doesn't click buttons
   - No mouse automation for poker actions
   - poker_bot.py has empty execute_action()

3. **Turn Detection**
   - No logic to detect when it's your turn
   - is_hero_turn() not implemented
   - Bot can't know when to act

4. **Game State Parsing**
   - Doesn't read community cards
   - Doesn't read opponent stacks
   - Doesn't detect available actions

5. **Bot Loop**
   - Main bot loop not functional
   - No continuous monitoring
   - No hand-by-hand automation

---

## AI Usage Analysis

### Where AI Is Used

**1. Poker Decision Making** (server/app.py)
```python
# Build prompt with game state
prompt = f"""You are playing poker.
Your cards: {state['hero_cards']}
Pot: ${state['pot']}
Stack: ${state['hero_stack']}
To call: ${state['to_call']}

What should you do?"""

# Call Kiro CLI
result = subprocess.run(['kiro-cli', 'chat', prompt], ...)

# Parse response
# Expected: "fold" or "call" or "raise 100"
```

**Status**: Basic implementation, untested

**2. Element Detection** (server/app.py - /detect-elements)
```python
# Attempted to use Kiro CLI vision
# Doesn't work - CLI has no --image flag
# Reverted to OpenCV detection
```

**Status**: Failed attempt, not functional

### Where AI Could Be Used

**1. Card Recognition** ⭐ HIGH IMPACT
```
Current: Shows '??'
Potential: Kiro CLI vision to identify cards
Challenge: CLI doesn't support image input via command line
Alternative: Use OpenCV template matching (no AI needed)
```

**2. Table Layout Detection** ⭐ MEDIUM IMPACT
```
Current: Smart OCR with hardcoded logic
Potential: Kiro CLI describes table layout
Challenge: Same CLI limitation
Alternative: Current approach works well enough
```

**3. Opponent Modeling** ⭐ LOW IMPACT
```
Current: Not implemented
Potential: Kiro CLI analyzes opponent patterns
Benefit: Better decisions based on player history
```

**4. Strategy Adaptation** ⭐ MEDIUM IMPACT
```
Current: Single prompt for all situations
Potential: Kiro CLI adjusts strategy based on:
- Stack sizes
- Position
- Table dynamics
- Tournament vs cash game
```

---

## Original Goals vs Current State

### Original Vision (from INTEGRATION_PLAN.md)

**Goal**: Unified poker bot that:
- ✅ Uses poker-specific OCR
- ⚠️ Leverages Kiro CLI for decisions (basic implementation)
- ❌ Supports local and remote modes (only remote works)
- ❌ Provides analysis-only mode (not functional)
- ❌ Can play automatically (not implemented)

### What We Built Instead

**Reality**: Advanced calibration tool that:
- ✅ Detects poker windows
- ✅ Uses computer vision to find buttons
- ✅ Smart OCR with spatial reasoning
- ✅ Beautiful GUI with 4 tabs
- ✅ Global hotkeys (8 hotkeys)
- ✅ Mini overlay
- ✅ System tray
- ❌ Doesn't play poker

---

## The Calibration Rabbit Hole

### How We Got Here

**Session 1-3**: Core implementation (server, client, OCR)  
**Session 4-5**: Hotkeys and mini overlay (single monitor support)  
**Session 6**: Calibration flow fixes (F7-F12 hotkeys)  
**Session 7**: UI improvements (Help tab, active window capture)  
**Session 8**: Calibration simplification (F8 single-step, smart OCR)

**Pattern**: Each session focused on making calibration easier, not on poker functionality.

### Why This Happened

1. **User Constraint**: Single monitor setup
2. **UX Focus**: Making calibration "perfect"
3. **Scope Creep**: Added features (overlay, tray, 8 hotkeys)
4. **Lost Sight**: Forgot the goal is to play poker

---

## Critical Missing Pieces

### 1. Card Recognition (BLOCKER)

**Current**: Shows '??'  
**Impact**: Can't make informed decisions without cards  
**Solution Options**:
- Template matching (2-3 hours)
- Real card capture (1 day)
- ML model (1 week)

**Recommendation**: Template matching first

### 2. Turn Detection (BLOCKER)

**Current**: No logic to detect your turn  
**Impact**: Bot doesn't know when to act  
**Solution**:
```python
def is_hero_turn():
    # Look for action buttons visible
    # Check if timer is running
    # Detect if buttons are clickable
    return buttons_visible and timer_active
```

**Effort**: 2-3 hours

### 3. Action Execution (BLOCKER)

**Current**: Empty execute_action() method  
**Impact**: Bot can't click buttons  
**Solution**:
```python
def execute_action(decision):
    action = decision['action']
    if action == 'fold':
        pyautogui.click(BUTTON_REGIONS['fold'])
    elif action == 'call':
        pyautogui.click(BUTTON_REGIONS['call'])
    elif action == 'raise':
        pyautogui.click(BUTTON_REGIONS['raise'])
        pyautogui.typewrite(str(decision['amount']))
        pyautogui.press('enter')
```

**Effort**: 1-2 hours

### 4. Game State Parsing (CRITICAL)

**Current**: Only reads pot and stacks  
**Missing**:
- Community cards (board)
- Opponent stacks
- Available actions (fold/call/raise amounts)
- Position
- Blinds

**Effort**: 4-6 hours

### 5. Bot Main Loop (CRITICAL)

**Current**: Skeleton implementation  
**Needed**:
```python
while True:
    if not is_hero_turn():
        time.sleep(0.5)
        continue
    
    state = parse_game_state()
    decision = get_decision(state)
    execute_action(decision)
    
    wait_for_action_complete()
```

**Effort**: 2-3 hours

---

## Recommended Path Forward

### Option 1: Complete the Bot (2-3 days)

**Priority Order**:
1. **Card Recognition** (3 hours) - Template matching
2. **Turn Detection** (2 hours) - Button visibility check
3. **Action Execution** (2 hours) - Click automation
4. **Game State Parsing** (6 hours) - Read everything
5. **Bot Main Loop** (3 hours) - Tie it all together
6. **Testing** (8 hours) - Play money tables

**Total**: ~24 hours of focused work

**Result**: Functional poker bot

### Option 2: Simplify and Focus (1 day)

**Strip Down**:
- Remove mini overlay (not essential)
- Remove system tray (not essential)
- Remove Help tab (not essential)
- Keep only: Control Panel, Calibration, Debug

**Focus On**:
1. Card recognition
2. Turn detection
3. Action execution
4. Basic bot loop

**Total**: ~8 hours

**Result**: Minimal viable poker bot

### Option 3: Pivot to Analysis Tool (1 day)

**Accept Reality**: This is a poker analysis tool, not a bot

**Enhance**:
- Better Kiro CLI prompts
- Hand history logging
- Decision explanations
- Strategy recommendations
- Manual play with AI advice

**Total**: ~8 hours

**Result**: Poker coach, not poker player

---

## Architecture Improvements

### Current Issues

1. **Complexity**: 2,000+ lines for calibration, 100 lines for poker
2. **Separation**: Server and client in different directories
3. **Config**: Generated config.py is fragile
4. **Testing**: No unit tests, no integration tests
5. **Documentation**: 9 markdown files, some outdated

### Recommended Changes

**1. Simplify File Structure**
```
onyxpoker/
├── bot/
│   ├── poker_bot.py        # Main bot
│   ├── poker_reader.py     # OCR
│   ├── card_detector.py    # Card recognition
│   └── action_executor.py  # Click automation
├── gui/
│   ├── main_window.py      # Simple GUI
│   └── calibration.py      # Calibration only
├── server/
│   └── app.py              # Flask API
└── config/
    └── settings.json       # JSON config (not Python)
```

**2. Reduce Hotkeys**
```
Current: 8 hotkeys (F5-F12)
Needed: 3 hotkeys
- F9: Analyze (get advice)
- F10: Start/stop bot
- F11: Emergency stop
```

**3. Simplify Calibration**
```
Current: F7 → F8 → Save (3 steps)
Better: Click table → Auto-detect → Save (2 steps)
```

**4. Focus on Core**
```
Essential:
- Card recognition
- Turn detection
- Action execution
- Bot loop

Nice-to-have:
- Mini overlay
- System tray
- Help tab
```

---

## AI Integration Opportunities

### Current AI Usage: 20%

**What's Using AI**:
- Poker decision making (basic prompts)

**What's Not**:
- Card recognition (shows '??')
- Table detection (OpenCV)
- Turn detection (not implemented)
- Strategy adaptation (single prompt)

### Potential AI Usage: 80%

**1. Enhanced Decision Making** ⭐⭐⭐
```python
# Current: Basic prompt
prompt = f"Cards: {cards}, Pot: {pot}, What to do?"

# Better: Rich context
prompt = f"""
GAME CONTEXT:
- Position: {position} (early/middle/late)
- Stack: {stack} ({stack/big_blind} BB)
- Pot: {pot} ({pot_odds}% pot odds)
- Board: {board} (texture: {board_texture})
- Opponents: {num_opponents} active

YOUR HAND:
- Cards: {cards}
- Hand strength: {hand_strength}
- Equity: {equity}%

HISTORY:
- Preflop action: {preflop_action}
- Your image: {player_image}
- Opponent tendencies: {opponent_stats}

DECISION FACTORS:
- Stack-to-pot ratio: {spr}
- Implied odds: {implied_odds}
- Fold equity: {fold_equity}

What's the optimal play?
"""
```

**2. Opponent Modeling** ⭐⭐
```python
# Track opponent patterns
opponent_history = {
    'vpip': 0.25,  # Voluntarily put $ in pot
    'pfr': 0.18,   # Preflop raise
    'aggression': 2.5,
    'showdowns': [...]
}

# Ask Kiro to analyze
prompt = f"Opponent stats: {opponent_history}. How should I adjust?"
```

**3. Strategy Adaptation** ⭐⭐
```python
# Different prompts for different situations
if stack < 20 * big_blind:
    strategy = "short_stack"  # Push/fold
elif tournament:
    strategy = "tournament"   # ICM considerations
else:
    strategy = "cash_game"    # Chip EV

prompt = load_prompt(strategy)
```

**4. Hand Review** ⭐
```python
# After session, review hands
for hand in hand_history:
    prompt = f"""
    Review this hand:
    {hand}
    
    What could I have done better?
    """
    review = kiro_cli(prompt)
```

---

## Performance Analysis

### Current Performance

**Calibration**: ~2-3 seconds (fast)  
**OCR**: ~1-2 seconds (acceptable)  
**Kiro CLI**: ~5-15 seconds (SLOW)  
**Total F9 cycle**: ~8-20 seconds (TOO SLOW)

### Bottlenecks

1. **Kiro CLI Startup**: 15 seconds first call
2. **Kiro CLI Response**: 2-5 seconds per call
3. **Network Latency**: Variable (remote mode)

### Optimization Strategies

**1. Keep Kiro Warm**
```python
# Start Kiro CLI as persistent process
kiro_process = subprocess.Popen(
    ['kiro-cli', 'chat', '--interactive'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE
)

# Send prompts to stdin, read from stdout
# Eliminates 15-second startup
```

**2. Parallel Processing**
```python
# While waiting for Kiro, do other work
with ThreadPoolExecutor() as executor:
    ocr_future = executor.submit(parse_game_state)
    decision_future = executor.submit(get_kiro_decision, state)
    
    state = ocr_future.result()
    decision = decision_future.result()
```

**3. Cache Decisions**
```python
# Similar situations → similar decisions
decision_cache = {}
state_hash = hash_game_state(state)

if state_hash in decision_cache:
    return decision_cache[state_hash]
```

**4. Precompute**
```python
# Calculate hand strength, pot odds, equity
# before calling Kiro
# Reduces Kiro's work
```

---

## Testing Status

### What's Tested

- ✅ Server health endpoint
- ✅ Server authentication
- ✅ Kiro CLI integration (basic)
- ✅ Client-server communication

### What's Not Tested

- ❌ Card recognition (not implemented)
- ❌ Turn detection (not implemented)
- ❌ Action execution (not implemented)
- ❌ Bot main loop (not implemented)
- ❌ OCR accuracy on real tables
- ❌ Kiro decision quality
- ❌ End-to-end workflow

### Testing Needed

**1. OCR Accuracy Test**
```
Test on 100 hands:
- Pot reading accuracy
- Stack reading accuracy
- Card reading accuracy
- Action detection accuracy
```

**2. Kiro Decision Quality Test**
```
Test on 50 hands:
- Strong hands → Raise/Call
- Weak hands → Fold
- Drawing hands → Pot odds consideration
- Reasoning quality
```

**3. Bot Reliability Test**
```
Run for 1 hour:
- No crashes
- Correct turn detection
- Accurate action execution
- Reasonable decisions
```

---

## Conclusion

### Where We Are

**Built**: Sophisticated calibration system with computer vision, smart OCR, 8 hotkeys, mini overlay, system tray, and beautiful GUI.

**Missing**: The actual poker bot - card recognition, turn detection, action execution, and main loop.

### The Gap

**Effort Spent**: 80% on calibration/UX, 20% on poker functionality  
**Effort Needed**: 20% on calibration/UX, 80% on poker functionality

### Recommendation

**Option 1**: Complete the bot (2-3 days focused work)
- Implement card recognition
- Implement turn detection
- Implement action execution
- Test on play money tables

**Option 2**: Pivot to analysis tool (1 day)
- Accept it's not a bot
- Enhance AI advice quality
- Add hand history and review
- Manual play with AI coaching

**Option 3**: Start over with minimal approach (1 day)
- Strip out all the calibration complexity
- Focus only on poker functionality
- Simple GUI, simple workflow
- Get it working first, polish later

### My Assessment

We got distracted by making calibration perfect and lost sight of the goal: **playing poker with AI**.

The calibration system is impressive, but it's 80% of the codebase for 20% of the value.

**Next session should focus exclusively on**:
1. Card recognition (template matching)
2. Turn detection (button visibility)
3. Action execution (click automation)
4. Bot loop (tie it together)

No more calibration improvements. No more UX polish. Just make it play poker.

---

**Review Complete**: December 29, 2025 20:33 UTC  
**Verdict**: Overengineered calibration, underengineered poker bot  
**Path Forward**: Focus on core poker functionality, ignore UX for now
