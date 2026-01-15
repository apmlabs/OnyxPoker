# Comprehensive Strategy Report
**Generated**: January 15, 2026

## Executive Summary

| Metric | optimal_stats | value_lord | value_maniac | sonnet | gpt4 |
|--------|---------------|------------|--------------|--------|------|
| **Profile** | TAG ⭐ | LAG | LAG | TAG | TAG |
| **Sim BB/100** | +9.25 | +11.09 | +12.17 | N/A | N/A |
| **Real Hands Score** | N/A | +21.8 | +21.4 | N/A | N/A |
| **VPIP** | 19.1% ✅ | 31.8% ⚠️ | 31.8% ⚠️ | 18.6% ✅ | 19.5% ✅ |
| **PFR** | 15.6% ✅ | 21.7% | 21.7% | 13.4% | 13.6% |
| **Gap** | 3.5% ⭐ | 10.1% ❌ | 10.1% ❌ | 5.3% | 5.9% |
| **3-bet%** | 5.9% ⭐ | 5.9% | 5.9% | 3.0% ❌ | 3.0% ❌ |
| **4-bet%** | 15.0% ⭐ | 8.3% ❌ | 8.3% ❌ | 7.6% ❌ | 13.8% |
| **AF** | 3.46 ✅ | 5.38 ⚠️ | 4.76 ⚠️ | 2.57 ✅ | 3.04 ✅ |
| **C-bet%** | 55.2% | 89.4% ✅ | 80.5% ✅ | 37.1% ❌ | 58.9% |

**Legend**: ✅ Good | ⭐ Best | ⚠️ High/Exploitable | ❌ Low/Leak

---

## 1. Simulation Results (100k hands × 3 trials)

Table composition: 60% fish, 25% nit, 15% tag (realistic 2NL)

| Rank | Strategy | BB/100 | StdDev | Notes |
|------|----------|--------|--------|-------|
| 1 | value_max | +17.77 | 10.84 | Equity-based decisions |
| 2 | kiro_v2 | +14.03 | 6.61 | Balanced approach |
| 3 | value_maniac | +12.17 | 1.71 | Low variance ⭐ |
| 4 | value_lord | +11.09 | 5.06 | C-bet discipline |
| 5 | **optimal_stats** | +9.25 | 7.70 | TAG profile |
| 6 | sonnet_max | +9.11 | 4.45 | Sonnet preflop + fixes |

**Key Insight**: At 2NL, LAG strategies (value_*) outperform TAG strategies because fish call too much. optimal_stats' tighter ranges miss value from loose callers.

---

## 2. Real Hand Evaluation (eval_strategies.py)

Tested on 1150+ real hands from session logs.

| Rank | Strategy | Score | Est BB/100 | Bad Folds | Bad Calls |
|------|----------|-------|------------|-----------|-----------|
| 1 | value_lord | +792.0 | +21.8 | 0 | 0 |
| 2 | value_maniac | +778.5 | +21.4 | 0 | 0 |
| 3 | kiro_v2 | +722.5 | +19.9 | 0 | 9 |
| 4 | sonnet_max | +706.5 | +19.4 | 1 | 6 |
| 5 | value_max | +654.0 | +18.0 | 10 | 5 |

**Note**: optimal_stats not yet in eval_strategies.py default list.

---

## 3. Deep Evaluation (eval_deep.py)

### Industry Targets vs Actual

| Stat | TARGET | optimal_stats | value_lord | sonnet | Rating |
|------|--------|---------------|------------|--------|--------|
| VPIP | 21% | 19.1% | 31.8% | 18.6% | optimal_stats closest |
| PFR | 18% | 15.6% | 21.7% | 13.4% | optimal_stats closest |
| Gap | 3% | 3.5% | 10.1% | 5.3% | **optimal_stats BEST** |
| 3-bet | 8% | 5.9% | 5.9% | 3.0% | **optimal_stats BEST** |
| 4-bet | 25% | 15.0% | 8.3% | 7.6% | **optimal_stats BEST** |
| Fold to 3bet | 60% | 70.0% | 80.2% | 82.2% | optimal_stats closest |
| AF | 2.5 | 3.46 | 5.38 | 2.57 | sonnet closest |
| C-bet | 80% | 55.2% | 89.4% | 37.1% | value_lord closest |

### Player Type Classification

| Strategy | VPIP | PFR | Gap | AF | Profile |
|----------|------|-----|-----|-----|---------|
| **TARGET (TAG)** | 21% | 18% | 3% | 2.5 | Tight-Aggressive |
| optimal_stats | 19.1% | 15.6% | 3.5% | 3.46 | **TAG** ⭐ |
| sonnet | 18.6% | 13.4% | 5.3% | 2.57 | TAG |
| gpt4 | 19.5% | 13.6% | 5.9% | 3.04 | TAG |
| value_lord | 31.8% | 21.7% | 10.1% | 5.38 | LAG |
| value_maniac | 31.8% | 21.7% | 10.1% | 4.76 | LAG |
| value_max | 31.1% | 21.7% | 9.4% | 2.95 | LAG |

---

## 4. Strategy Profiles

### optimal_stats (NEW)
**Profile**: Tight-Aggressive (TAG) - Winning player profile!

**Strengths**:
- ⭐ Best Gap (3.5%) - raises instead of calling
- ⭐ Best 3-bet% (5.9%) - more re-raising
- ⭐ Best 4-bet% (15.0%) - defends opens better
- ✅ Balanced AF (3.46) - not overaggressive
- ✅ VPIP/PFR closest to winning player targets

**Weaknesses**:
- ❌ C-bet only 55% (target 70-80%)
- ❌ BB Defend only 28% (target 35-45%)
- ❌ Lower sim BB/100 at 2NL (fish call too much)

**Best For**: Higher stakes (5NL+) where opponents fold more.

---

### value_lord / value_maniac
**Profile**: Loose-Aggressive (LAG)

**Strengths**:
- ✅ High C-bet (80-89%) - extracts value
- ✅ Zero bad folds/calls on real hands
- ✅ Profitable at 2NL (+11-12 BB/100 sim, +21 BB/100 real)

**Weaknesses**:
- ❌ High Gap (10.1%) - calls too much preflop
- ❌ Low 4-bet% (8.3%) - folds to 3-bets too often
- ❌ High AF (4.7-5.4) - exploitable at higher stakes

**Best For**: 2NL where fish call everything.

---

### sonnet
**Profile**: Tight-Aggressive (TAG)

**Strengths**:
- ✅ Perfect AF (2.57) - matches winning player target
- ✅ Good VPIP (18.6%)

**Weaknesses**:
- ❌ Very low C-bet (37%) - missing value
- ❌ Low 3-bet% (3.0%) - not aggressive enough
- ❌ High fold to 3-bet (82%)

**Best For**: Passive tables where you don't need to c-bet.

---

## 5. Recommendations

### For 2NL (Current Play)
**Use: value_lord or value_maniac**
- Fish call too much → wide ranges + overbets = profit
- +21 BB/100 on real hands validates this approach
- Low variance (StdDev 1.7-5.0)

### For 5NL+ (Future)
**Use: optimal_stats**
- Opponents fold more → tight ranges + 3-betting = profit
- TAG profile matches winning players at higher stakes
- Need to improve C-bet% (currently 55%, target 70%+)

### Improvements Needed for optimal_stats
1. **Increase C-bet%**: Currently 55%, should be 70-80%
2. **Increase BB Defend%**: Currently 28%, should be 35-45%
3. **Increase 3-bet%**: Currently 5.9%, target 8%

---

## 6. Key Takeaways

1. **optimal_stats achieves best preflop metrics** - lowest Gap, highest 3-bet/4-bet
2. **But loses to LAG strategies at 2NL** - fish call too much, tight ranges miss value
3. **value_lord/maniac dominate real hands** - +21 BB/100 with zero bad decisions
4. **Profile matters by stakes**:
   - 2NL: LAG wins (exploit loose callers)
   - 5NL+: TAG wins (exploit folders)

---

## Appendix: Full Stats Comparison

```
Strategy         VPIP    PFR   3bet   4bet  Steal    AF   Cbet
--------------------------------------------------------------------
TARGET            21%    18%     8%    25%    35%   2.5    80%
--------------------------------------------------------------------
optimal_stats   19.1%  15.6%   5.9%  15.0%  34.1%  3.46  55.2%
value_lord      31.8%  21.7%   5.9%   8.3%  46.7%  5.38  89.4%
value_maniac    31.8%  21.7%   5.9%   8.3%  46.7%  4.76  80.5%
sonnet          18.6%  13.4%   3.0%   7.6%  31.6%  2.57  37.1%
gpt4            19.5%  13.6%   3.0%  13.8%  32.3%  3.04  58.9%
value_max       31.1%  21.7%   5.9%   8.3%  46.7%  2.95  54.9%
```
