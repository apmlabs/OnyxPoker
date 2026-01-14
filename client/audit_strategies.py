#!/usr/bin/env python3
"""
Audit strategies: Compare strategy files vs hardcoded logic.
Tests specific scenarios to verify code matches strategy file descriptions.
"""
import sys
sys.path.insert(0, '.')
from poker_logic import (STRATEGIES, preflop_action, postflop_action, 
                         expand_range, analyze_hand)

def test_preflop(strategy_name, hand, position, facing, expected_action, desc):
    """Test a preflop scenario."""
    strategy = STRATEGIES.get(strategy_name)
    if not strategy:
        return f"MISSING: {strategy_name}"
    
    action, _ = preflop_action(hand, position, strategy, facing, opener_pos='CO')
    status = "PASS" if action == expected_action else "FAIL"
    return f"{status}: {strategy_name} {hand} {position} facing={facing} -> {action} (expected {expected_action}) [{desc}]"

def test_postflop(strategy_name, hole, board, pot, to_call, street, expected_action, desc):
    """Test a postflop scenario."""
    hole_cards = [(c[0], c[1]) for c in hole]
    board_cards = [(c[0], c[1]) for c in board]
    
    action, sizing, reason = postflop_action(
        hole_cards, board_cards, pot, to_call, street,
        is_ip=True, is_aggressor=True,
        strategy=strategy_name, num_opponents=1
    )
    
    status = "PASS" if action == expected_action else "FAIL"
    return f"{status}: {strategy_name} {hole} on {board} pot={pot} to_call={to_call} -> {action} (expected {expected_action}) [{desc}] reason={reason}"

def main():
    print("=" * 80)
    print("STRATEGY AUDIT: Comparing strategy files vs hardcoded logic")
    print("=" * 80)
    
    results = []
    
    # ========== VALUE_LORD TESTS ==========
    print("\n--- VALUE_LORD STRATEGY ---")
    print("value_maniac + Session 41 fixes (c-bet discipline, overpair aggression, weak pair caution)")
    
    # Preflop - same wide ranges as value_maniac
    results.append(test_preflop('value_lord', 'A5s', 'BTN', 'none', 'raise', 'Wide open BTN'))
    results.append(test_preflop('value_lord', 'K8s', 'BTN', 'none', 'raise', 'K8s open BTN'))
    
    # Postflop - overpairs always bet (Session 41 fix)
    results.append(test_postflop('value_lord', [('Q','s'),('Q','d')], [('J','h'),('7','d'),('2','c')], 1.0, 0, 'flop', 'bet', 'QQ overpair - always bet'))
    
    # Paired board protection (same as value_maniac)
    results.append(test_postflop('value_lord', [('K','s'),('K','d')], [('J','h'),('J','d'),('2','c')], 1.0, 0, 'flop', 'bet', 'KK on JJ - value bet'))
    results.append(test_postflop('value_lord', [('6','s'),('6','d')], [('J','h'),('J','d'),('8','c')], 1.0, 0.5, 'flop', 'fold', '66 on JJ8 facing 50% - fold'))
    
    # ========== VALUE_MANIAC TESTS ==========
    print("\n--- VALUE_MANIAC STRATEGY ---")
    print("Wide ranges, overbets, paired board protection")
    
    # Preflop - wide ranges
    results.append(test_preflop('value_maniac', 'A5s', 'BTN', 'none', 'raise', 'Wide open BTN'))
    results.append(test_preflop('value_maniac', '43s', 'BTN', 'none', 'raise', 'Very wide BTN'))
    results.append(test_preflop('value_maniac', 'K8s', 'BTN', 'none', 'raise', 'K8s open BTN'))
    results.append(test_preflop('value_maniac', 'J7s', 'BTN', 'none', 'raise', 'J7s open BTN'))
    
    # Postflop - value betting
    results.append(test_postflop('value_maniac', [('A','s'),('A','d')], [('K','h'),('7','d'),('2','c')], 1.0, 0, 'flop', 'bet', 'AA overpair - value bet'))
    results.append(test_postflop('value_maniac', [('K','s'),('Q','d')], [('K','h'),('7','d'),('2','c')], 1.0, 0, 'flop', 'bet', 'Top pair - value bet'))
    
    # Paired board - KK on JJ (KK > JJ = strong)
    results.append(test_postflop('value_maniac', [('K','s'),('K','d')], [('J','h'),('J','d'),('2','c')], 1.0, 0, 'flop', 'bet', 'KK on JJ - value bet (KK > JJ)'))
    results.append(test_postflop('value_maniac', [('K','s'),('K','d')], [('J','h'),('J','d'),('2','c')], 1.0, 0.5, 'flop', 'fold', 'KK on JJ facing bet - fold (vulnerable to trips)'))
    
    # Paired board - 66 on JJ (66 < JJ = weak)
    results.append(test_postflop('value_maniac', [('6','s'),('6','d')], [('J','h'),('J','d'),('8','c')], 1.0, 0.5, 'flop', 'fold', '66 on JJ8 facing 50% - fold (66 < JJ)'))
    results.append(test_postflop('value_maniac', [('6','s'),('6','d')], [('J','h'),('J','d'),('8','c')], 1.0, 0.3, 'flop', 'call', '66 on JJ8 facing 30% - call small'))
    
    # Two pair (both cards hit)
    results.append(test_postflop('value_maniac', [('A','s'),('7','d')], [('A','h'),('7','c'),('2','c')], 1.0, 0, 'flop', 'bet', 'A7 on A72 - value bet two pair'))
    
    # Facing bet - call pairs
    results.append(test_postflop('value_maniac', [('K','s'),('K','d')], [('A','h'),('7','d'),('2','c')], 1.0, 0.5, 'flop', 'call', 'KK underpair to ace - call'))
    results.append(test_postflop('value_maniac', [('5','s'),('5','d')], [('A','h'),('K','d'),('Q','c')], 1.0, 0.5, 'flop', 'call', '55 pocket pair - call'))
    
    # ========== VALUE_MAX TESTS ==========
    print("\n--- VALUE_MAX STRATEGY ---")
    print("Smart aggression with pot odds, two pair strength matters")
    
    # Two pair strength tests
    results.append(test_postflop('value_max', [('T','s'),('T','d')], [('9','h'),('4','c'),('4','d')], 1.0, 0, 'flop', 'bet', 'TT on 944 - strong (TT > 44)'))
    results.append(test_postflop('value_max', [('2','s'),('2','d')], [('9','h'),('9','c'),('4','d')], 1.0, 0, 'flop', 'bet', '22 on 994 - weak (22 < 99)'))
    results.append(test_postflop('value_max', [('J','s'),('7','d')], [('7','h'),('6','c'),('J','d')], 1.0, 0, 'flop', 'bet', 'J7 on 76J - two pair (no board pair)'))
    
    # Top pair facing bets
    results.append(test_postflop('value_max', [('A','s'),('K','d')], [('A','h'),('7','c'),('2','d')], 1.0, 0.5, 'flop', 'call', 'TPGK facing 50% pot - call'))
    
    # ========== GPT4 TESTS ==========
    print("\n--- GPT4 STRATEGY ---")
    print("Board texture aware, smaller c-bets")
    
    results.append(test_postflop('gpt4', [('A','s'),('A','d')], [('K','h'),('7','d'),('2','c')], 1.0, 0, 'flop', 'bet', 'AA on K72 - value bet'))
    results.append(test_postflop('gpt4', [('K','s'),('K','d')], [('A','h'),('7','d'),('2','c')], 1.0, 0.5, 'flop', 'call', 'KK underpair to ace - call'))
    
    # ========== SONNET TESTS ==========
    print("\n--- SONNET STRATEGY ---")
    print("Big value bets (75-85%), overpair logic")
    
    results.append(test_postflop('sonnet', [('Q','s'),('Q','d')], [('J','h'),('8','d'),('5','c')], 1.0, 0, 'flop', 'bet', 'QQ overpair - value bet'))
    results.append(test_postflop('sonnet', [('K','s'),('K','d')], [('A','h'),('7','d'),('2','c')], 1.0, 0.5, 'flop', 'call', 'KK underpair to ace - call'))
    
    # Print results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    passes = 0
    fails = 0
    for r in results:
        print(r)
        if r.startswith("PASS"):
            passes += 1
        elif r.startswith("FAIL"):
            fails += 1
    
    print(f"\nTotal: {passes} PASS, {fails} FAIL")
    
    if fails > 0:
        print("\n[!] FAILURES indicate code doesn't match strategy file!")
    else:
        print("\n[OK] All tests pass - code matches strategy files")

if __name__ == '__main__':
    main()
