# OnyxPoker Integration Plan

**Date**: December 29, 2025  
**Status**: Planning Phase  
**Goal**: Merge GitHub skeleton with local Kiro CLI integration

---

## Project Overview

### Two Components to Merge

**1. GitHub Skeleton** (https://github.com/apmlabs/OnyxPoker/)
- Poker-specific screen reading (OCR for cards, bets, stacks)
- Template matching for card recognition
- Turn detection logic
- Action execution (fold, call, raise)
- Modular frontend/backend architecture

**2. Local Project** (Current Folder)
- Flask API server (Linux)
- Kiro CLI integration framework
- Windows automation client (PyAutoGUI)
- HTTP bridge for cross-platform communication
- Authentication and security

### Integration Goal

Create a **unified poker bot** that:
- Uses poker-specific OCR from GitHub skeleton
- Leverages Kiro CLI (you) for decision-making instead of GPT API
- Supports both local (Windows-only) and distributed (Windows + Linux) modes
- Provides analysis-only mode for research/learning

---

## Architecture Comparison

### GitHub Skeleton Architecture
```
Windows Machine (All-in-One)
    ↓ PyAutoGUI Screenshot
    ↓ OCR/Template Matching (Tesseract + OpenCV)
    ↓ Parse Poker State
    ↓ GPT API Call (OpenAI)
    ↓ Parse Decision
    ↓ PyAutoGUI Click/Type
```

### Current Local Architecture
```
Windows Client
    ↓ Screenshot
    ↓ Base64 Encode
    ↓ HTTP POST
Linux Server
    ↓ Kiro CLI Analysis
    ↓ JSON Response
Windows Client
    ↓ Action Execution
```

### Proposed Unified Architecture
```
Windows Machine
    ↓ PyAutoGUI Screenshot
    ↓ Poker-Specific OCR (cards, bets, stacks)
    ↓ Parse Poker State
    ↓ [MODE SELECTION]
    ├─ LOCAL MODE: Kiro CLI subprocess (if installed locally)
    └─ REMOTE MODE: HTTP POST to Linux server
    ↓ Kiro CLI Decision
    ↓ Parse Action
    ↓ [EXECUTION MODE]
    ├─ AUTO: PyAutoGUI Click/Type
    └─ ANALYSIS: Display only (no action)
```

---

## Integration Steps

### Phase 1: Code Merge (Week 1)

#### 1.1 Import GitHub Skeleton
- [ ] Clone poker-specific modules from GitHub
- [ ] Import `frontend/screen_reader.py` (OCR logic)
- [ ] Import `backend/strategy_gpt.py` (as reference)
- [ ] Import `config.py` (screen regions)
- [ ] Import `utils.py` (card encoding)
- [ ] Import `templates/` (card images for matching)

#### 1.2 Create Unified Structure
```
onyxpoker/
├── client/                      # Windows client (merged)
│   ├── poker_reader.py          # From GitHub: OCR + parsing
│   ├── automation_client.py     # Current: HTTP client
│   ├── poker_bot.py             # NEW: Main bot orchestrator
│   ├── config.py                # From GitHub: screen regions
│   ├── utils.py                 # From GitHub: helpers
│   ├── requirements.txt         # Merged dependencies
│   └── setup.bat                # Current: setup script
├── server/                      # Linux server (current)
│   ├── app.py                   # Current: Flask API
│   ├── poker_strategy.py        # NEW: Kiro CLI poker strategy
│   ├── requirements.txt         # Current: dependencies
│   └── setup.sh                 # Current: setup script
├── templates/                   # From GitHub: card images
│   ├── ranks/                   # Card rank templates
│   └── suits/                   # Card suit templates
├── docs/                        # Documentation
│   ├── API.md                   # Current: API docs
│   ├── DEPLOYMENT.md            # Current: deployment
│   └── POKER_STRATEGY.md        # NEW: poker strategy guide
└── [existing files...]
```

#### 1.3 Merge Dependencies
**Client requirements.txt**:
```python
# Current dependencies
pyautogui==0.9.54
requests==2.31.0
pillow==10.0.1
python-dotenv==1.0.0

# Add from GitHub skeleton
pytesseract==0.3.10
opencv-python==4.8.1.78
imagehash==4.3.1
```

**Server requirements.txt** (no changes needed):
```python
flask==2.3.3
flask-cors==4.0.0
requests==2.31.0
pillow==10.0.1
python-dotenv==1.0.0
```

### Phase 2: Backend Integration (Week 1-2)

#### 2.1 Create Kiro CLI Poker Strategy Module
**File**: `server/poker_strategy.py`

```python
"""
Poker-specific strategy using Kiro CLI
Replaces GPT API calls with Kiro CLI subprocess
"""

import subprocess
import json
import tempfile
from typing import Dict, Any

def analyze_poker_state(state: Dict[str, Any], screenshot_path: str = None) -> Dict[str, Any]:
    """
    Analyze poker game state using Kiro CLI
    
    Args:
        state: Parsed poker state (cards, bets, stacks, etc.)
        screenshot_path: Optional path to screenshot for visual analysis
    
    Returns:
        Decision dict with action, amount, reasoning
    """
    # Build poker-specific prompt
    prompt = build_poker_prompt(state)
    
    # Call Kiro CLI with prompt and optional screenshot
    if screenshot_path:
        result = subprocess.run(
            ['kiro-cli', 'analyze', '--image', screenshot_path, '--prompt', prompt],
            capture_output=True,
            text=True,
            timeout=10
        )
    else:
        result = subprocess.run(
            ['kiro-cli', 'chat', prompt],
            capture_output=True,
            text=True,
            timeout=10
        )
    
    # Parse Kiro CLI response
    response = result.stdout.strip()
    decision = parse_poker_decision(response, state)
    
    return decision

def build_poker_prompt(state: Dict[str, Any]) -> str:
    """Build structured prompt for Kiro CLI"""
    prompt = f"""You are playing 6-max No-Limit Texas Hold'em poker.

CURRENT SITUATION:
- Your cards: {state.get('hero_cards', 'Unknown')}
- Board: {state.get('community_cards', [])}
- Pot: ${state.get('pot', 0)}
- Your stack: ${state.get('hero_stack', 0)}
- To call: ${state.get('to_call', 0)}
- Min raise: ${state.get('min_raise', 0)}

OPPONENTS:
{format_opponents(state.get('opponents', []))}

AVAILABLE ACTIONS: {', '.join(state.get('actions', []))}

Analyze this poker situation and recommend the best action.
Respond with: fold, call, or raise <amount>
Include brief reasoning."""
    
    return prompt

def format_opponents(opponents: list) -> str:
    """Format opponent information"""
    lines = []
    for opp in opponents:
        if opp.get('active'):
            lines.append(f"  Seat {opp['seat']}: ${opp['stack']} (bet: ${opp.get('current_bet', 0)})")
    return '\n'.join(lines) if lines else "  No active opponents"

def parse_poker_decision(response: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Kiro CLI response into action dict"""
    response_lower = response.lower()
    
    # Extract action
    if 'fold' in response_lower:
        return {'action': 'fold', 'amount': 0, 'reasoning': response}
    elif 'call' in response_lower or 'check' in response_lower:
        return {'action': 'call', 'amount': state.get('to_call', 0), 'reasoning': response}
    elif 'raise' in response_lower or 'bet' in response_lower:
        # Try to extract amount
        import re
        amount_match = re.search(r'\$?(\d+)', response_lower)
        amount = int(amount_match.group(1)) if amount_match else state.get('min_raise', 0)
        return {'action': 'raise', 'amount': amount, 'reasoning': response}
    else:
        # Default to fold if unclear
        return {'action': 'fold', 'amount': 0, 'reasoning': 'Unclear response, defaulting to fold'}
```

#### 2.2 Update Flask API for Poker
**Modify**: `server/app.py`

Add poker-specific endpoint:
```python
@app.route('/analyze-poker', methods=['POST'])
def analyze_poker():
    """Poker-specific analysis endpoint"""
    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        
        # Get poker state
        state = data.get('state', {})
        
        # Optional: get screenshot for visual analysis
        screenshot_data = data.get('image')
        screenshot_path = None
        
        if screenshot_data:
            image_data = base64.b64decode(screenshot_data)
            with tempfile.NamedTemporaryFile(suffix='.png', dir=TEMP_DIR, delete=False) as f:
                f.write(image_data)
                screenshot_path = f.name
        
        # Analyze with Kiro CLI
        from poker_strategy import analyze_poker_state
        decision = analyze_poker_state(state, screenshot_path)
        
        # Cleanup
        if screenshot_path and os.path.exists(screenshot_path):
            os.unlink(screenshot_path)
        
        return jsonify(decision)
        
    except Exception as e:
        logger.error(f"Poker analysis error: {str(e)}")
        return jsonify({"error": str(e)}), 500
```

### Phase 3: Frontend Integration (Week 2)

#### 3.1 Create Unified Poker Bot
**File**: `client/poker_bot.py`

```python
"""
Unified OnyxPoker Bot
Combines poker-specific OCR with Kiro CLI decision-making
"""

import time
from typing import Dict, Any, Optional
from poker_reader import PokerScreenReader
from automation_client import OnyxPokerClient
import pyautogui

class OnyxPokerBot:
    def __init__(self, mode='remote', execution='auto'):
        """
        Initialize poker bot
        
        Args:
            mode: 'local' (Kiro CLI subprocess) or 'remote' (HTTP to server)
            execution: 'auto' (click actions) or 'analysis' (display only)
        """
        self.mode = mode
        self.execution = execution
        self.reader = PokerScreenReader()
        
        if mode == 'remote':
            self.client = OnyxPokerClient()
        
        print(f"OnyxPoker Bot initialized: mode={mode}, execution={execution}")
    
    def run(self, max_hands: Optional[int] = None):
        """Main bot loop"""
        hands_played = 0
        
        try:
            while max_hands is None or hands_played < max_hands:
                # Wait for hero's turn
                if not self.reader.is_hero_turn():
                    time.sleep(0.5)
                    continue
                
                # Parse poker state
                state = self.reader.parse_game_state()
                print(f"\n=== Hand {hands_played + 1} ===")
                print(f"State: {state}")
                
                # Get decision
                decision = self.get_decision(state)
                print(f"Decision: {decision}")
                
                # Execute or display
                if self.execution == 'auto':
                    self.execute_action(decision)
                else:
                    print(f"[ANALYSIS MODE] Would execute: {decision['action']}")
                
                hands_played += 1
                time.sleep(2)  # Wait before next hand
                
        except KeyboardInterrupt:
            print(f"\nBot stopped. Hands played: {hands_played}")
    
    def get_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get decision from Kiro CLI (local or remote)"""
        if self.mode == 'local':
            # Local Kiro CLI subprocess
            from poker_strategy import analyze_poker_state
            return analyze_poker_state(state)
        else:
            # Remote HTTP call
            screenshot = self.reader.capture_screenshot()
            return self.client.analyze_poker(state, screenshot)
    
    def execute_action(self, decision: Dict[str, Any]):
        """Execute poker action"""
        action = decision.get('action')
        amount = decision.get('amount', 0)
        
        if action == 'fold':
            self.click_button('fold')
        elif action == 'call':
            self.click_button('call')
        elif action == 'raise':
            self.click_button('raise')
            if amount > 0:
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.typewrite(str(amount))
                pyautogui.press('enter')
    
    def click_button(self, button_name: str):
        """Click poker action button"""
        # Use coordinates from config
        from config import BUTTON_REGIONS, TABLE_REGION
        x, y, w, h = BUTTON_REGIONS[button_name]
        pyautogui.click(
            TABLE_REGION[0] + x + w // 2,
            TABLE_REGION[1] + y + h // 2
        )
        print(f"Clicked {button_name}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['local', 'remote'], default='remote')
    parser.add_argument('--execution', choices=['auto', 'analysis'], default='analysis')
    parser.add_argument('--hands', type=int, help='Max hands to play')
    args = parser.parse_args()
    
    bot = OnyxPokerBot(mode=args.mode, execution=args.execution)
    bot.run(max_hands=args.hands)
```

#### 3.2 Import Poker Screen Reader
**File**: `client/poker_reader.py`

Import and adapt `screen_reader.py` from GitHub:
- Keep OCR logic for cards, bets, stacks
- Keep turn detection
- Keep template matching
- Add screenshot capture method
- Integrate with current architecture

### Phase 4: Testing & Validation (Week 2-3)

#### 4.1 Unit Tests
- [ ] Test poker state parsing (OCR accuracy)
- [ ] Test Kiro CLI integration (prompt → decision)
- [ ] Test action execution (button clicks)
- [ ] Test both local and remote modes

#### 4.2 Integration Tests
- [ ] End-to-end: screenshot → parse → decide → execute
- [ ] Test with PokerStars play money tables
- [ ] Validate timing (< 10 seconds per decision)
- [ ] Test error handling and recovery

#### 4.3 Performance Benchmarks
- [ ] OCR speed (target: < 2 seconds)
- [ ] Kiro CLI response time (target: < 5 seconds)
- [ ] Total cycle time (target: < 10 seconds)
- [ ] Memory usage monitoring

### Phase 5: Documentation & Deployment (Week 3)

#### 5.1 Documentation Updates
- [ ] Update README with poker bot usage
- [ ] Create POKER_STRATEGY.md guide
- [ ] Document screen region calibration
- [ ] Add troubleshooting guide
- [ ] Create video tutorial

#### 5.2 Configuration Tools
- [ ] Screen region calibration tool
- [ ] Card template generator
- [ ] OCR accuracy tester
- [ ] Decision logging analyzer

#### 5.3 Deployment
- [ ] Package for Windows distribution
- [ ] Create installer script
- [ ] Deploy Linux server (if using remote mode)
- [ ] Set up monitoring and logging

---

## Key Design Decisions

### 1. Dual Mode Support

**Local Mode** (Windows-only):
- Pros: Faster (no network), simpler setup
- Cons: Requires Kiro CLI on Windows, less flexible
- Use case: Single-machine research, testing

**Remote Mode** (Windows + Linux):
- Pros: Centralized AI, easier updates, better security
- Cons: Network latency, more complex setup
- Use case: Production, multiple clients, cloud deployment

### 2. Execution Modes

**Auto Mode**:
- Full automation (click buttons)
- For actual gameplay
- Requires careful testing

**Analysis Mode**:
- Display decisions only
- For learning and research
- Safe for testing

### 3. Kiro CLI Integration

**Why Kiro CLI over GPT API:**
- ✅ More control over prompts
- ✅ Can use local models
- ✅ Better for research/experimentation
- ✅ No API costs
- ✅ Can leverage your poker knowledge

**Prompt Engineering:**
- Structured poker state format
- Clear action format (fold/call/raise)
- Include reasoning for learning
- Optimize for speed (< 5 seconds)

---

## Risk Assessment

### Technical Risks

**High Priority** 🔴:
- OCR accuracy on different PokerStars themes
- Timing constraints (10-second window)
- Kiro CLI response variability

**Medium Priority** 🟡:
- Network latency (remote mode)
- Screen resolution differences
- Card template matching failures

**Low Priority** 🟢:
- Button click precision
- Configuration management
- Logging overhead

### Mitigation Strategies

1. **OCR Accuracy**:
   - Multiple OCR attempts with preprocessing
   - Template matching fallback
   - Manual calibration tool

2. **Timing**:
   - Optimize OCR (parallel processing)
   - Cache static elements
   - Timeout with safe defaults (fold)

3. **Reliability**:
   - Comprehensive error handling
   - Automatic retry logic
   - Detailed logging for debugging

---

## Success Metrics

### Phase 1 (Code Merge)
- ✅ All modules imported and integrated
- ✅ No merge conflicts
- ✅ Dependencies resolved
- ✅ Project structure clean

### Phase 2 (Backend)
- ✅ Kiro CLI integration working
- ✅ Poker prompts optimized
- ✅ Decision parsing accurate
- ✅ Response time < 5 seconds

### Phase 3 (Frontend)
- ✅ OCR accuracy > 95%
- ✅ Turn detection reliable
- ✅ Action execution precise
- ✅ Both modes functional

### Phase 4 (Testing)
- ✅ 100 hands played successfully
- ✅ No crashes or timeouts
- ✅ Decision quality validated
- ✅ Performance benchmarks met

### Phase 5 (Deployment)
- ✅ Documentation complete
- ✅ Easy setup process
- ✅ Monitoring in place
- ✅ Ready for research use

---

## Timeline

**Week 1**: Code merge + Backend integration  
**Week 2**: Frontend integration + Initial testing  
**Week 3**: Full testing + Documentation + Deployment  

**Total**: 3 weeks to production-ready poker bot

---

## Next Immediate Steps

1. **Review this plan** - Confirm approach and priorities
2. **Clone GitHub repo** - Import poker-specific modules
3. **Create poker_strategy.py** - Kiro CLI integration
4. **Test OCR** - Validate card/bet reading
5. **Build poker_bot.py** - Unified orchestrator

---

## Questions to Resolve

1. **Kiro CLI Installation**: Will Kiro CLI be available on Windows for local mode?
2. **PokerStars Theme**: Which theme/skin will we target for OCR?
3. **Screen Resolution**: What resolution will the poker table run at?
4. **Execution Mode**: Start with analysis-only or full automation?
5. **Testing Environment**: Play money tables or simulation?

---

**Status**: Ready to begin Phase 1 - Code Merge

**Next Action**: Import GitHub skeleton modules into local project
