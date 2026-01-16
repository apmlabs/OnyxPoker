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
    
    # ========== KIRO_LORD TESTS ==========
    print("\n--- KIRO_LORD STRATEGY ---")
    print("kiro_optimal preflop + 5 postflop improvements")
    
    # Preflop - tight ranges (same as kiro_optimal)
    results.append(test_preflop('kiro_lord', 'AKs', 'UTG', 'none', 'raise', 'AKs open UTG'))
    results.append(test_preflop('kiro_lord', 'JTs', 'BTN', 'none', 'raise', 'JTs open BTN'))
    results.append(test_preflop('kiro_lord', '72o', 'BTN', 'none', 'fold', '72o fold BTN'))
    
    # Postflop - pocket_under_board FOLD (improvement #1)
    results.append(test_postflop('kiro_lord', [('6','s'),('6','d')], [('J','h'),('J','d'),('8','c')], 1.0, 0.3, 'flop', 'fold', '66 on JJ8 - fold pocket_under_board'))
    
    # Postflop - pocket_over_board river vs 100%+ FOLD (improvement #2)
    results.append(test_postflop('kiro_lord', [('K','s'),('K','d')], [('J','h'),('J','d'),('2','c'),('5','s'),('3','h')], 1.0, 0.55, 'river', 'fold', 'KK on JJ river vs 100%+ - fold'))
    
    # Postflop - underpair vs 50% flop CALL once (improvement #3)
    results.append(test_postflop('kiro_lord', [('J','s'),('J','d')], [('Q','h'),('4','d'),('7','c')], 1.0, 0.35, 'flop', 'call', 'JJ underpair vs 50% flop - call once'))
    
    # Postflop - TPGK vs 75%+ turn FOLD (improvement #4)
    results.append(test_postflop('kiro_lord', [('A','s'),('K','d')], [('A','h'),('7','c'),('2','d'),('5','s')], 1.0, 0.5, 'turn', 'fold', 'TPGK vs 75%+ turn - fold'))
    
    # ========== KIRO_OPTIMAL TESTS ==========
    print("\n--- KIRO_OPTIMAL STRATEGY ---")
    print("Tight preflop, sonnet-style postflop")
    
    # Preflop - tight ranges
    results.append(test_preflop('kiro_optimal', 'AKs', 'UTG', 'none', 'raise', 'AKs open UTG'))
    results.append(test_preflop('kiro_optimal', 'JTs', 'BTN', 'none', 'raise', 'JTs open BTN'))
    results.append(test_preflop('kiro_optimal', '72o', 'BTN', 'none', 'fold', '72o fold BTN'))
    
    # Postflop - overpair value betting
    results.append(test_postflop('kiro_optimal', [('Q','s'),('Q','d')], [('J','h'),('8','d'),('5','c')], 1.0, 0, 'flop', 'bet', 'QQ overpair - value bet'))
    results.append(test_postflop('kiro_optimal', [('A','s'),('K','d')], [('A','h'),('7','c'),('2','d')], 1.0, 0, 'flop', 'bet', 'TPGK flop - bet'))
    
    # Facing bets
    results.append(test_postflop('kiro_optimal', [('K','s'),('K','d')], [('A','h'),('7','d'),('2','c')], 1.0, 0.5, 'flop', 'call', 'KK underpair to ace - call'))
    
    # ========== SONNET TESTS ==========
    print("\n--- SONNET STRATEGY ---")
    print("Big value bets (75-85%), specific sizing per street")
    
    # Overpair value betting
    results.append(test_postflop('sonnet', [('Q','s'),('Q','d')], [('J','h'),('8','d'),('5','c')], 1.0, 0, 'flop', 'bet', 'QQ overpair - value bet'))
    results.append(test_postflop('sonnet', [('K','s'),('K','d')], [('A','h'),('7','d'),('2','c')], 1.0, 0.5, 'flop', 'call', 'KK underpair to ace - call'))
    
    # TPTK: bet all 3 streets (75/70/60)
    results.append(test_postflop('sonnet', [('A','s'),('K','d')], [('A','h'),('7','c'),('2','d')], 1.0, 0, 'flop', 'bet', 'TPTK flop - bet 75%'))
    results.append(test_postflop('sonnet', [('A','s'),('K','d')], [('A','h'),('7','c'),('2','d'),('5','s')], 1.0, 0, 'turn', 'bet', 'TPTK turn - bet 70%'))
    results.append(test_postflop('sonnet', [('A','s'),('K','d')], [('A','h'),('7','c'),('2','d'),('5','s'),('3','h')], 1.0, 0, 'river', 'bet', 'TPTK river - bet 60%'))
    
    # TPWK: bet flop only, check-call turn/river
    results.append(test_postflop('sonnet', [('K','s'),('7','d')], [('K','h'),('8','c'),('2','d')], 1.0, 0, 'flop', 'bet', 'TPWK flop - bet 65%'))
    results.append(test_postflop('sonnet', [('K','s'),('7','d')], [('K','h'),('8','c'),('2','d'),('5','s')], 1.0, 0, 'turn', 'check', 'TPWK turn - check'))
    
    # Facing aggression: "Turn raises: fold one pair"
    # 80% pot is a big bet - treat like a raise, fold TPTK
    results.append(test_postflop('sonnet', [('A','s'),('K','d')], [('A','h'),('7','c'),('2','d'),('5','s')], 1.0, 0.8, 'turn', 'fold', 'TPTK facing 80% pot turn - fold (big bet)'))
    results.append(test_postflop('sonnet', [('K','s'),('7','d')], [('K','h'),('8','c'),('2','d'),('5','s')], 1.0, 0.5, 'turn', 'fold', 'TPWK facing turn bet - fold'))
    
    # Middle pair: check-call once, fold turn
    results.append(test_postflop('sonnet', [('T','s'),('9','d')], [('K','h'),('T','c'),('4','d')], 1.0, 0.4, 'flop', 'call', 'Middle pair flop - call once'))
    results.append(test_postflop('sonnet', [('T','s'),('9','d')], [('K','h'),('T','c'),('4','d'),('2','s')], 1.0, 0.5, 'turn', 'fold', 'Middle pair turn - fold'))
    
    # Bottom pair: check-fold
    results.append(test_postflop('sonnet', [('4','s'),('3','d')], [('K','h'),('T','c'),('4','d')], 1.0, 0.3, 'flop', 'fold', 'Bottom pair facing bet - fold'))
    
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
