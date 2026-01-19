#!/usr/bin/env python3
"""
Test strategy_engine.py - the glue between vision and poker_logic.
This tests the LIVE code path that helper_bar.py uses.
"""

from strategy_engine import StrategyEngine

def test_preflop():
    """Test preflop facing detection and action selection."""
    
    engine = StrategyEngine('value_lord')
    print(f"\n=== Testing VALUE_LORD preflop ===")
    
    tests = [
        # === FIRST TO ACT (to_call=0) ===
        # Should use OPEN ranges regardless of facing_raise flag
        (['Ah', 'Ah'], 0.07, 0, False, 'UTG', 'raise', 'AA opens UTG'),
        (['Kh', 'Kh'], 0.07, 0, False, 'MP', 'raise', 'KK opens MP'),
        (['Kh', '8h'], 0.07, 0, False, 'BTN', 'raise', 'K8s opens BTN'),
        (['Kh', '8h'], 0.07, 0, True, 'BTN', 'raise', 'K8s opens BTN (buggy vision)'),
        (['Jh', '7h'], 0.07, 0, False, 'BTN', 'raise', 'J7s opens BTN'),
        (['Jh', '7h'], 0.07, 0, True, 'BTN', 'raise', 'J7s opens BTN (buggy vision)'),
        (['7h', '2h'], 0.07, 0, False, 'BTN', 'fold', '72s folds BTN'),
        (['Ah', '5h'], 0.07, 0, False, 'CO', 'raise', 'A5s opens CO'),
        (['Ah', '5h'], 0.07, 0, False, 'UTG', 'raise', 'A5s opens UTG (value_lord is wide)'),
        
        # === FACING OPEN (to_call=0.05-0.15) ===
        # Should use call_open_ip / 3bet ranges
        (['Ah', 'Kh'], 0.17, 0.10, True, 'BTN', 'raise', 'AKs 3-bets'),
        (['Qh', 'Qh'], 0.17, 0.10, True, 'BTN', 'raise', 'QQ 3-bets'),
        (['Th', 'Th'], 0.17, 0.10, True, 'BTN', 'raise', 'TT 3-bets'),
        (['9h', '8h'], 0.17, 0.10, True, 'BTN', 'call', '98s calls open IP'),
        (['Qh', 'Jc'], 0.17, 0.10, True, 'BTN', 'call', 'QJo calls open IP'),
        (['Ah', 'Qc'], 0.17, 0.10, True, 'BTN', 'raise', 'AQo 3-bets'),
        (['Kh', '8h'], 0.17, 0.10, True, 'BTN', 'fold', 'K8s folds vs open'),
        (['Jh', '7h'], 0.17, 0.10, True, 'BTN', 'fold', 'J7s folds vs open'),
        (['7h', '6h'], 0.17, 0.10, True, 'BTN', 'call', '76s calls open IP'),
        
        # === BB DEFENSE ===
        (['Kh', '8h'], 0.17, 0.10, True, 'BB', 'call', 'K8s BB defends'),
        (['Jh', '7h'], 0.17, 0.10, True, 'BB', 'call', 'J7s BB defends'),
        (['9h', '4h'], 0.17, 0.10, True, 'BB', 'fold', '94s not in BB defend'),
        (['Kh', '5h'], 0.17, 0.10, True, 'BB', 'call', 'K5s BB defends'),
        (['7h', '2c'], 0.17, 0.10, True, 'BB', 'fold', '72o folds BB'),
        
        # === FACING 3BET (to_call=0.30-0.80) ===
        (['Ah', 'Ah'], 0.50, 0.35, True, 'BTN', 'raise', 'AA 4-bets'),
        (['Kh', 'Kh'], 0.50, 0.35, True, 'BTN', 'raise', 'KK 4-bets'),
        (['Ah', 'Kh'], 0.50, 0.35, True, 'BTN', 'raise', 'AKs 4-bets'),
        (['Qh', 'Qh'], 0.50, 0.35, True, 'BTN', 'raise', 'QQ 4-bets'),
        (['Th', 'Th'], 0.50, 0.35, True, 'BTN', 'call', 'TT calls 3bet'),
        (['9h', '9h'], 0.50, 0.35, True, 'BTN', 'call', '99 calls 3bet'),
        (['8h', '8h'], 0.50, 0.35, True, 'BTN', 'fold', '88 folds to 3bet'),
        
        # === EDGE CASES ===
        (['Ah', 'Ah'], 0.07, 0.02, False, 'BB', 'raise', 'AA raises from BB vs limp'),
        (['2h', '2h'], 0.07, 0, False, 'BTN', 'raise', '22 opens BTN'),
        (['Ah', '2h'], 0.07, 0, False, 'BTN', 'raise', 'A2s opens BTN'),
        (['Ah', '2h'], 0.07, 0, False, 'UTG', 'raise', 'A2s opens UTG (value_lord wide)'),
    ]
    
    passed = 0
    failed = []
    
    for cards, pot, to_call, facing_raise, pos, expected, desc in tests:
        table_data = {
            'hero_cards': cards,
            'community_cards': [],
            'pot': pot,
            'to_call': to_call,
            'facing_raise': facing_raise,
            'position': pos
        }
        result = engine.get_action(table_data)
        actual = result['action']
        
        if actual == expected:
            passed += 1
        else:
            failed.append((desc, actual, expected, result.get('reasoning', '')))
    
    print(f"Passed: {passed}/{len(tests)}")
    if failed:
        print(f"Failed {len(failed)} tests:")
        for desc, actual, expected, reason in failed:
            print(f"  {desc}: got {actual}, expected {expected}")
    
    return passed, len(tests), failed


def test_postflop():
    """Test postflop action selection through strategy_engine."""
    
    engine = StrategyEngine('value_lord')
    print(f"\n=== Testing VALUE_LORD postflop ===")
    
    tests = [
        # === MONSTERS - should raise/bet big ===
        (['Ah', 'Ah'], ['As', 'Ad', '5c'], 1.0, 0, 'BTN', 'bet', 'Quads bets'),
        (['Kh', 'Kh'], ['Ks', 'Kd', '5c'], 1.0, 0.5, 'BTN', 'raise', 'Quads raises'),
        (['Ah', 'Kh'], ['Ah', 'Ah', 'Kc'], 1.0, 0, 'BTN', 'bet', 'Full house bets'),
        
        # === SETS - should bet/raise ===
        (['8h', '8c'], ['8s', '5d', '2c'], 0.5, 0, 'BTN', 'bet', 'Set bets flop'),
        (['8h', '8c'], ['8s', '5d', '2c'], 0.5, 0.25, 'BTN', 'raise', 'Set raises flop'),
        
        # === TWO PAIR - depends on board pair ===
        (['Kh', 'Kc'], ['Jh', 'Jd', '5c'], 1.0, 0, 'BTN', 'bet', 'KK on JJ - HIGH pair, small bet'),
        (['Kh', 'Kc'], ['6h', '6d', '5c'], 1.0, 0, 'BTN', 'bet', 'KK on 66 - LOW pair, bet big'),
        (['Ah', 'Ah'], ['9h', 'Td', 'Qc', '7s', '9d'], 1.0, 0, 'BTN', 'bet', 'AA on 9TQ79 - LOW pair'),
        
        # === TOP PAIR ===
        (['Ah', 'Kh'], ['Ah', '7d', '2c'], 0.5, 0, 'BTN', 'bet', 'TPTK bets'),
        (['Ah', 'Kh'], ['Ah', '7d', '2c'], 0.5, 0.25, 'BTN', 'call', 'TPTK calls bet'),
        
        # === DRAWS ===
        (['Ah', 'Kh'], ['Qh', '7h', '2c'], 0.5, 0, 'BTN', 'bet', 'Flush draw bets'),
        (['Jh', 'Th'], ['9h', '8d', '2c'], 0.5, 0, 'BTN', 'bet', 'OESD bets'),
        
        # === WEAK HANDS ===
        (['Ah', 'Kh'], ['Qc', '7d', '2c'], 0.5, 0.25, 'BTN', 'call', 'AK overcards calls'),
        (['7h', '2h'], ['Ac', 'Kd', 'Qc'], 0.5, 0.25, 'BTN', 'fold', 'Suited air folds (no backdoor)'),
        (['7h', '2c'], ['Ac', 'Kd', 'Qc'], 0.5, 0.25, 'BTN', 'fold', 'Offsuit air folds'),
    ]
    
    passed = 0
    failed = []
    
    for cards, board, pot, to_call, pos, expected, desc in tests:
        table_data = {
            'hero_cards': cards,
            'community_cards': board,
            'pot': pot,
            'to_call': to_call,
            'facing_raise': to_call > 0,
            'position': pos
        }
        result = engine.get_action(table_data)
        actual = result['action']
        
        if actual == expected:
            passed += 1
        else:
            failed.append((desc, actual, expected, result.get('reasoning', '')))
    
    print(f"Passed: {passed}/{len(tests)}")
    if failed:
        print(f"Failed {len(failed)} tests:")
        for desc, actual, expected, reason in failed:
            print(f"  {desc}: got {actual}, expected {expected}")
    
    return passed, len(tests), failed


def test_vision_edge_cases():
    """Test handling of weird/missing vision data."""
    engine = StrategyEngine('value_lord')
    
    tests = [
        # Missing/None values
        ({'hero_cards': None, 'community_cards': [], 'pot': 0.5, 'to_call': 0, 'position': 'BTN'},
         'fold', 'No cards -> fold'),
        ({'hero_cards': [], 'community_cards': [], 'pot': 0.5, 'to_call': 0, 'position': 'BTN'},
         'fold', 'Empty cards -> fold'),
        ({'hero_cards': ['Ah', 'Kh'], 'community_cards': [], 'pot': None, 'to_call': 0, 'position': 'BTN'},
         'raise', 'None pot -> still works'),
        ({'hero_cards': ['Ah', 'Kh'], 'community_cards': [], 'pot': 0.07, 'to_call': None, 'position': 'BTN'},
         'raise', 'None to_call -> treat as 0'),
        
        # Invalid position
        ({'hero_cards': ['Ah', 'Kh'], 'community_cards': [], 'pot': 0.07, 'to_call': 0, 'position': 'INVALID'},
         'raise', 'Invalid position -> defaults to BTN'),
        ({'hero_cards': ['Ah', 'Kh'], 'community_cards': [], 'pot': 0.07, 'to_call': 0, 'position': None},
         'raise', 'None position -> defaults to BTN'),
    ]
    
    passed = 0
    failed = []
    
    for table_data, expected, desc in tests:
        result = engine.get_action(table_data)
        actual = result['action']
        
        if actual == expected:
            passed += 1
        else:
            failed.append((desc, actual, expected, result.get('reasoning', '')))
    
    return passed, len(tests), failed


if __name__ == '__main__':
    print('=' * 60)
    print('STRATEGY ENGINE TESTS')
    print('=' * 60)
    
    total_passed = 0
    total_tests = 0
    all_failed = []
    
    # Preflop tests
    print('\n--- PREFLOP TESTS ---')
    passed, total, failed = test_preflop()
    total_passed += passed
    total_tests += total
    all_failed.extend(failed)
    print(f'Passed: {passed}/{total}')
    
    # Postflop tests
    print('\n--- POSTFLOP TESTS ---')
    passed, total, failed = test_postflop()
    total_passed += passed
    total_tests += total
    all_failed.extend(failed)
    print(f'Passed: {passed}/{total}')
    
    # Edge case tests
    print('\n--- VISION EDGE CASES ---')
    passed, total, failed = test_vision_edge_cases()
    total_passed += passed
    total_tests += total
    all_failed.extend(failed)
    print(f'Passed: {passed}/{total}')
    
    # Summary
    print('\n' + '=' * 60)
    print(f'TOTAL: {total_passed}/{total_tests} tests passed')
    print('=' * 60)
    
    if all_failed:
        print('\nFAILED TESTS:')
        for desc, actual, expected, reason in all_failed:
            print(f'  {desc}')
            print(f'    Got: {actual}, Expected: {expected}')
            print(f'    Reason: {reason}')
