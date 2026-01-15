# Strategy Evaluation Report - Session 43 Part 19

**Date**: January 15, 2026
**Hands Analyzed**: 1,819 real hands from session logs
**Change**: Added pot_pct based bet-size decisions to kiro/sonnet/gpt strategies

## Executive Summary

| Rank | Strategy | Est BB/100 | Bad Decisions | Profile | Best For |
|------|----------|------------|---------------|---------|----------|
| 1 | **value_lord** | +21.8 | 0 | LAG | 2NL (fish-heavy) |
| 2 | **value_maniac** | +21.5 | 0 | LAG | 2NL (fish-heavy) |
| 3 | optimal_stats | +19.9 | 9 | TAG | 5NL+ (better opponents) |
| 4 | kiro_v2 | +19.6 | 11 | TAG | Balanced play |
| 5 | sonnet_max | +19.4 | 7 | TAG | Balanced play |
| 6 | value_max | +18.0 | 15 | TAG | Equity-based |

## Key Findings

### 1. value_lord/value_maniac: Best for 2NL
- **0 bad folds, 0 bad calls** - perfect decision quality
- High aggression (AF 5.33/4.87) extracts max value from fish
- Wide ranges (VPIP 31.8%) exploit passive opponents
- C-bet 89%/84% - fish fold too much

### 2. optimal_stats: Best Stats, Not Best Profit
- **7/10 stats in target range** (closest to GTO)
- But makes $0.69 LESS than value_lord per 100 hands
- Why? Fish call too much - aggressive betting wins more at 2NL
- **Recommended for 5NL+** where opponents fold appropriately

### 3. kiro/sonnet/gpt: Now Use pot_pct
- Replaced binary `is_facing_raise` with granular `pot_pct` thresholds
- TPGK: call flop, call turn ≤60% pot, call river ≤40-45% pot
- Overpair: call flop, call turn/river ≤50% pot
- Two pair: fold to >75% pot on river
- More nuanced than "fold one pair to raises"

## Detailed Stats Comparison

### Preflop Stats
```
Strategy        VPIP    PFR    Gap   3bet   4bet   Steal   BB Def
TARGET           21%    18%     3%     8%    25%     35%     40%
----------------------------------------------------------------
optimal_stats  19.1%  15.6%   3.5%   5.9%  15.0%   34.1%   28.4%  ← Best Gap
value_lord     31.8%  21.7%  10.1%   5.9%   8.3%   46.7%   44.4%  ← Best BB Def
value_maniac   31.8%  21.7%  10.1%   5.9%   8.3%   46.7%   44.4%
sonnet         18.6%  13.4%   5.3%   3.0%   7.6%   31.6%   29.0%
gpt4           19.5%  13.6%   5.9%   3.0%  13.8%   32.3%   33.7%
kiro_v2        18.0%  12.8%   5.2%   3.0%   8.1%   30.0%   28.4%
```

### Postflop Stats
```
Strategy        AF     C-bet   Flop AF  Turn AF  River AF
TARGET         2.5      75%      3.0      2.5       2.0
---------------------------------------------------------
optimal_stats  3.42   53.7%     4.09     3.39      2.53  ← Best AF
value_lord     5.33   89.4%     3.90     9.20      9.85  ← Best C-bet
value_maniac   4.87   83.6%     3.66     6.38      9.69
sonnet         3.32   37.1%     2.71     3.67      4.07
gpt4           4.08   61.2%     4.43     3.38      4.13
kiro_v2        2.90   37.1%     2.51     3.19      3.24  ← Closest to target
```

## Bad Decision Analysis

### value_lord / value_maniac: 0 Bad Decisions ✅
Perfect decision quality - no bad folds or bad calls.

### optimal_stats: 9 Bad Calls
All are extreme edge cases (all-ins with TPGK):
- KsJh on K92 flop: $14.55 into $0.35 pot (41x pot)
- AdKd on A48 flop: $7.46 into $0.19 pot (39x pot)

### kiro_v2: 11 Bad Calls
Mostly calling all-ins with marginal hands:
- 55 on AAK flop: $4.40 into $0.63 (7x pot)
- KsJc on 33QJ turn: $5.09 into $0.77 (6.6x pot)

## pot_pct Thresholds (New)

### kiro/sonnet strategies:
| Hand Type | Flop | Turn | River |
|-----------|------|------|-------|
| TPGK | call any | call ≤60% | call ≤40-45% |
| TPWK | call ≤50% | fold | fold |
| Overpair | call any | call ≤50% | call ≤50% |
| Middle pair | call ≤40% | fold | fold |
| Two pair | call any | call any | fold >75% |

### gpt strategies:
| Hand Type | Flop | Turn | River |
|-----------|------|------|-------|
| TPGK | call any | call ≤50% | fold |
| TPWK | call ≤50% | fold | fold |
| Overpair | call any | call ≤40% | call ≤40% |
| Middle pair | call ≤40% | fold | fold |

## Recommendations

### For 2NL (fish-heavy tables):
**Use value_lord** - aggressive betting extracts max value from calling stations.

### For 5NL+ (better opponents):
**Use optimal_stats** - GTO-inspired play works when opponents fold appropriately.

### For balanced play:
**Use kiro_v2** - closest to target AF (2.90 vs 2.5 target), good decision quality.

## Changes Made This Session

1. **Removed `is_facing_raise` binary flag** - was too crude (>80% pot = raise)
2. **Added `pot_pct` calculations** to kiro/sonnet/gpt strategies
3. **Granular thresholds** for each hand type and street
4. **Updated audit test** - 80% pot turn bet now expects fold for TPTK (big bet = fold)

## Test Results

- audit_strategies.py: **43/43 PASS** ✅
- eval_strategies.py: All strategies evaluated
- value_lord: 0 bad folds, 0 bad calls
