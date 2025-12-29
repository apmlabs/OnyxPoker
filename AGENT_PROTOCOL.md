# Agent Context Maintenance Protocol

## Why This Matters

As an AI agent working on this project, I don't have persistent memory between sessions. **Context files are my only memory.** Without proper maintenance, I:
- Lose track of what was done
- Repeat mistakes
- Forget important decisions
- Break continuity
- Waste time rediscovering solutions

## Mandatory Update Checklist

### After EVERY coding session:

**1. Update AmazonQ.md**
- [ ] Current timestamp
- [ ] Status summary (what's complete, in progress, not started)
- [ ] New features added
- [ ] Known issues discovered
- [ ] Next immediate steps

**2. Update AGENTS.md**
- [ ] New learnings (what worked, what didn't)
- [ ] Technical insights
- [ ] Architecture decisions
- [ ] Patterns discovered
- [ ] Challenges overcome

**3. Update README.md (if user-facing changes)**
- [ ] New features
- [ ] Installation steps
- [ ] Usage examples
- [ ] Requirements

**4. Commit to GitHub**
- [ ] Clear, descriptive commit message
- [ ] List all files changed
- [ ] Explain why changes were made
- [ ] Push to remote

### Before STARTING new work:

**1. Review Context**
- [ ] Read AmazonQ.md for current status
- [ ] Read AGENTS.md for past learnings
- [ ] Check recent commits for changes
- [ ] Understand what was tried before

**2. Plan Based on Context**
- [ ] Don't repeat failed approaches
- [ ] Build on what works
- [ ] Follow established patterns
- [ ] Respect documented decisions

## What to Document

### In AmazonQ.md (Status Tracking):
- Current development phase
- Completed features (with ✅)
- In-progress work (with 🔄)
- Not started items (with 📝)
- Known bugs/issues
- Performance metrics
- Deployment status
- Next steps

### In AGENTS.md (Learning & Patterns):
- **What Worked**: Successful approaches, patterns, solutions
- **What Didn't Work**: Failed attempts, dead ends, mistakes
- **Why**: Reasoning behind decisions
- **Key Insights**: Important discoveries
- **Architecture Decisions**: Why certain designs were chosen
- **Security Considerations**: Important security rules
- **Performance Lessons**: Optimization insights

### In Commit Messages:
```
Brief summary (50 chars or less)

Detailed explanation:
- What was changed
- Why it was changed
- How it solves the problem
- Any side effects or considerations

New files:
- file1.py: Purpose
- file2.py: Purpose

Updated:
- file3.py: What changed and why
```

## Example: Good vs Bad

### ❌ Bad (No Context):
```
Agent: "I'll create a calibration tool"
*creates standalone tool*
*doesn't update any docs*
*doesn't commit*
```
**Result**: Next session, I don't know this exists or why it was made.

### ✅ Good (With Context):
```
Agent: "I'll create a calibration tool"
*creates tool*
*updates AmazonQ.md: "Added auto-calibration system"*
*updates AGENTS.md: "Learned: Users prefer integrated UI over separate tools"*
*commits with clear message*
*updates README with usage*
```
**Result**: Next session, I know exactly what exists, why, and how to use it.

## Red Flags (When I'm Failing):

- ⚠️ User asks "did you update the docs?" → I forgot
- ⚠️ I suggest something already tried → I didn't read context
- ⚠️ I don't know what's complete → AmazonQ.md is stale
- ⚠️ I repeat a mistake → AGENTS.md wasn't updated
- ⚠️ Git is out of sync → I didn't commit

## Recovery Protocol

If I realize I've been neglecting context:

1. **STOP** current work
2. **UPDATE** all context files immediately
3. **COMMIT** everything to GitHub
4. **REVIEW** what was missed
5. **RESUME** with proper context

## Success Metrics

I'm doing well when:
- ✅ Every session starts with context review
- ✅ Every session ends with context update
- ✅ GitHub is always in sync
- ✅ User never has to remind me to update docs
- ✅ I can explain what was done and why
- ✅ I build on previous work instead of redoing it

## This is Not Optional

Context maintenance is **part of the work**, not extra work. A feature isn't complete until:
1. Code is written
2. Code is tested
3. Docs are updated
4. Context is updated
5. Changes are committed

**Without context, I'm starting from scratch every time.**
