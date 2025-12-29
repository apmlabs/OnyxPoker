# OnyxPoker - Architecture Plan

**Date**: December 29, 2025 23:58 UTC  
**Status**: Phase 1 (Vision LLM) - In Progress

---

## Overview

Two-phase architecture:
1. **Phase 1 (Current)**: Vision LLM reads real poker tables → Simple decisions
2. **Phase 2 (Future)**: Deep CFR agent → Advanced poker AI

---

## Phase 1: Vision LLM Demo (Current)

### Goal
Functional poker bot that reads real PokerStars tables and makes basic decisions.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Windows Client                            │
│                                                              │
│  PokerStars (Real Money Tables - Play Money Mode)           │
│         ↓                                                    │
│  PyAutoGUI Screenshot (TABLE_REGION)                         │
│         ↓                                                    │
│  GPT-4o Vision API                                           │
│    - Reads cards, pot, stacks, buttons                      │
│    - Returns structured JSON                                 │
│         ↓                                                    │
│  Simple Decision Logic (Client-Side)                         │
│    - Basic poker rules                                       │
│    - Hand strength evaluation                                │
│    - Pot odds calculation                                    │
│         ↓                                                    │
│  PyAutoGUI Click/Type                                        │
│    - Execute fold/call/raise                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘

Optional: Linux Server (Kiro CLI for advice/validation)
```

### Components

**Client (Windows)**
- `poker_gui.py` - Main GUI (4 tabs)
- `vision_detector.py` - GPT-4o API wrapper
- `poker_reader.py` - Parse game state
- `poker_bot.py` - Decision logic + action execution
- `hotkey_manager.py` - F5-F12 hotkeys
- `mini_overlay.py` - Always-on-top display

**Server (Linux) - Optional**
- `app.py` - Flask API (Kiro CLI advice)
- Used for: Validation, strategy tips, hand review
- NOT used for: Real-time decisions (too slow)

### Decision Flow (Phase 1)

```
1. Capture screenshot (F9 or auto)
   ↓
2. GPT-4o Vision API
   - Input: Screenshot (base64)
   - Output: {cards, pot, stacks, actions, button_positions}
   ↓
3. Client-side decision logic
   - Hand strength (lookup table)
   - Pot odds (math)
   - Position (button/early/late)
   - Stack size (BB count)
   ↓
4. Execute action
   - Click button at coordinates from GPT-4o
   - Type raise amount if needed
   ↓
5. Wait for next turn
```

### Why Client-Only for Phase 1?

**Pros**:
- ✅ Faster (no network latency)
- ✅ Simpler (no server dependency)
- ✅ GPT-4o already on client
- ✅ Good enough for demo

**Cons**:
- ❌ No advanced AI (just rules)
- ❌ No learning/adaptation
- ❌ Limited strategy depth

**Server Role (Optional)**:
- Kiro CLI for strategy advice (F9 manual)
- Hand history analysis
- Post-session review
- Validation/debugging

---

## Phase 2: Deep CFR Agent (Future)

### Goal
Research-grade poker AI using Deep CFR + ReBeL-style search.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Windows Client                            │
│                                                              │
│  PokerStars (Real Tables)                                    │
│         ↓                                                    │
│  GPT-4o Vision API (table reading only)                      │
│         ↓                                                    │
│  HTTP POST to Linux Server                                   │
│                                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    Linux Server (AWS)                        │
│                                                              │
│  Flask API Endpoint                                          │
│         ↓                                                    │
│  OpenSpiel Environment                                       │
│    - Convert real state → OpenSpiel state                   │
│         ↓                                                    │
│  Deep CFR Agent                                              │
│    - Policy network (trained via self-play)                 │
│    - Value network (trained via CFR)                         │
│    - Optional: ReBeL-style search                            │
│         ↓                                                    │
│  Return action + reasoning                                   │
│         ↓                                                    │
│  Client executes action                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Components (Phase 2)

**Training Pipeline** (Offline)
- OpenSpiel poker environment
- Deep CFR implementation (JAX/TF)
- Self-play training loop
- Policy/value network training
- Model checkpoints

**Inference Server** (Linux)
- Load trained models
- Convert real state → OpenSpiel format
- Run policy network inference
- Optional: Monte Carlo search
- Return action probabilities

**Client** (Windows)
- Same vision system (GPT-4o)
- HTTP client to inference server
- Action execution

### Training Approach

**Option 1: OpenSpiel + Deep CFR**
```python
# Use OpenSpiel's built-in poker
import pyspiel
game = pyspiel.load_game("leduc_poker")  # Start simple
# or
game = pyspiel.load_game("universal_poker")  # Full NLHE

# Deep CFR training
from open_spiel.python.algorithms import deep_cfr
solver = deep_cfr.DeepCFRSolver(game, ...)
solver.solve()
```

**Option 2: deepcfr-poker (Faster Start)**
```python
# Use existing implementation
# https://github.com/EricSteinberger/Deep-CFR-Poker
from deepcfr import DeepCFR
agent = DeepCFR(...)
agent.train(num_iterations=1000000)
```

**Option 3: ReBeL Extension (PhD-level)**
```python
# Adapt Meta's ReBeL for poker
# Policy network + value network + search
# More complex but state-of-the-art
```

### Why Server for Phase 2?

**Pros**:
- ✅ GPU acceleration (training + inference)
- ✅ Centralized model updates
- ✅ Can train while playing
- ✅ Research-grade AI

**Cons**:
- ❌ Network latency (1-2s)
- ❌ More complex deployment
- ❌ Requires GPU server

---

## Current Implementation Status

### ✅ Phase 1 - Complete
- GPT-4o vision integration
- Client-side architecture
- Server optional (Kiro CLI)

### ⏭️ Phase 1 - TODO
- Implement turn detection (2 hours)
- Implement action execution (2 hours)
- Implement basic decision logic (4 hours)
- Test on play money tables (4 hours)

### 📝 Phase 2 - Future
- OpenSpiel integration
- Deep CFR training pipeline
- Model inference server
- Advanced strategy

---

## Decision: Keep Server for Phase 2

### Current Plan

**Phase 1 (Now - Next Week)**:
- Client-only with GPT-4o vision
- Simple rule-based decisions
- Server available but optional (Kiro CLI advice)
- Goal: Working demo on real tables

**Phase 2 (Future - Research)**:
- Server becomes inference endpoint
- Deep CFR trained models
- OpenSpiel integration
- Advanced poker AI

### Server Code Status

**Keep**:
- ✅ Flask API structure
- ✅ Authentication
- ✅ Kiro CLI integration (for advice)
- ✅ Systemd service

**Add Later** (Phase 2):
- OpenSpiel environment
- Model inference endpoint
- Training pipeline integration
- GPU support

---

## Implementation Roadmap

### Week 1: Complete Phase 1 Demo
1. ✅ GPT-4o vision (done)
2. ⏭️ Turn detection
3. ⏭️ Action execution
4. ⏭️ Basic decision logic
5. ⏭️ Test on PokerStars play money

### Week 2-3: Refine Phase 1
1. Hand strength evaluation
2. Pot odds calculation
3. Position awareness
4. Stack size strategy
5. Multi-table support

### Month 2-3: Phase 2 Research
1. OpenSpiel setup
2. Deep CFR implementation
3. Training pipeline
4. Model evaluation
5. Inference server

### Month 4+: Advanced Features
1. ReBeL-style search
2. Opponent modeling
3. Adaptive strategy
4. Tournament mode
5. Publication/demo

---

## Technology Stack

### Phase 1 (Current)
- **Vision**: OpenAI GPT-4o Vision API
- **Client**: Python + PyAutoGUI + tkinter
- **Server**: Flask + Kiro CLI (optional)
- **Decision**: Rule-based (client-side)

### Phase 2 (Future)
- **Vision**: Same (GPT-4o)
- **Environment**: OpenSpiel
- **Training**: Deep CFR (JAX/TF)
- **Inference**: Flask + trained models
- **Server**: AWS GPU instance (p3.2xlarge)

---

## Cost Analysis

### Phase 1
- GPT-4o Vision: $2 per 1000 hands
- AWS Server: $32/month (optional)
- Total: $6-60/month (depending on volume)

### Phase 2
- GPT-4o Vision: Same ($2 per 1000 hands)
- AWS GPU Server: $3/hour training, $0.50/hour inference
- Training: ~$500-1000 one-time
- Inference: ~$100/month
- Total: ~$150/month operational

---

## Summary

**Current Focus**: Phase 1 - Vision LLM demo
- Client-only decisions (fast, simple)
- Server optional (Kiro CLI advice)
- Goal: Working bot on real tables

**Future**: Phase 2 - Deep CFR agent
- Server-based inference (advanced AI)
- OpenSpiel + Deep CFR training
- Research-grade poker AI

**Next Steps**:
1. Complete Phase 1 (turn detection, action execution)
2. Test on PokerStars play money
3. Refine decision logic
4. Then consider Phase 2 research

**Server Status**: Keep running, use for Kiro CLI advice, prepare for Phase 2 inference endpoint.
