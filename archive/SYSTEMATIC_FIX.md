# Systematic Fix Plan - December 31, 2025

## CRITICAL ISSUES TO FIX

### 1. MODEL CONFIGURATION
**Problem**: Model name hardcoded as "gpt-5-mini" everywhere
**Fix**: Create MODEL constant, use everywhere
**Files**: vision_detector.py, all display strings

### 2. OVERLAY NOT UPDATING
**Problem**: Threading breaks overlay updates
**Fix**: Use root.after() for thread-safe GUI updates

### 3. CONSOLE LOGS STILL PRESENT
**Problem**: print() statements in vision_detector.py, poker_reader.py
**Fix**: Remove ALL print(), use logger only

### 4. PERFORMANCE LOGS SPAM
**Problem**: [PERF] logs clutter output
**Fix**: Make performance logging optional/debug-only

### 5. MD FILES OUT OF DATE
**Problem**: AmazonQ.md says "GPT-4o" but code uses "gpt-5-mini"
**Fix**: Update all MD files to reflect current state

## IMPLEMENTATION PLAN

### Step 1: Model Configuration (5 min)
- Add MODEL = "gpt-5-mini" constant in vision_detector.py
- Use MODEL everywhere instead of hardcoded string
- Update all display strings to use MODEL variable

### Step 2: Fix Overlay Updates (10 min)
- Ensure all overlay updates use root.after() from thread
- Test overlay responsiveness

### Step 3: Remove Console Logs (5 min)
- Remove all print() from vision_detector.py
- Remove all print() from poker_reader.py
- Keep only logger calls

### Step 4: Clean Performance Logs (5 min)
- Make [PERF] logs conditional on debug flag
- Keep only essential timing info

### Step 5: Update MD Files (10 min)
- Update AmazonQ.md with current status
- Update AGENTS.md with lessons learned
- Mark outdated MD files for archive

## TESTING CHECKLIST
- [ ] F9 updates overlay immediately
- [ ] No console spam (only [API] line)
- [ ] Model name shows correctly in logs
- [ ] GUI doesn't freeze
- [ ] MD files reflect reality
