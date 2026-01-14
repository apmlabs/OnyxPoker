#!/usr/bin/env python3
"""
Compare how value_maniac vs value_lord would have played a session.
"""
import json
import sys
from poker_logic import preflop_action, postflop_action, evaluate_hand

def analyze_session(log_file, strategy_name):
    """Replay session with given strategy and track differences."""
    
    hands = []
    with open(log_file, 'r') as f:
        for line in f:
            if line.strip():
                hands.append(json.loads(line))
    
    differences = []
    c_bet_bluffs = 0
    pocket_checks = 0
    overbets = 0
    high_card_bets = 0
    
    for i, h in enumerate(hands, 1):
        hole = h.get('hole_cards')
        board = h.get('board', [])
        pot = h.get('pot', 0)
        to_call = h.get('to_call', 0)
        position = h.get('position', 'BTN')
        actual_action = h.get('action')
        actual_amount = h.get('amount', 0)
        hand_desc = h.get('hand_desc', '')
        
        if not hole or not isinstance(hole, list) or len(hole) != 2:
            continue
            
        # Determine what strategy would do
        if not board or len(board) == 0:
            # Preflop - both strategies use same ranges
            continue
        else:
            # Postflop
            strength, desc = evaluate_hand(hole, board)
            action, amount, reasoning = postflop_action(
                hole, board, pot, to_call, 
                position=position,
                is_aggressor=True,  # Assume we opened
                strategy=strategy_name
            )
        
        # Track specific patterns
        if 'high card' in desc.lower() and action == 'bet':
            high_card_bets += 1
        if 'pocket' in desc.lower() and action == 'check':
            pocket_checks += 1
        if amount > pot * 0.8:
            overbets += 1
        
        # Check if different from actual
        if action != actual_action or abs(amount - actual_amount) > 0.05:
            differences.append({
                'hand_num': i,
                'hole': hole,
                'board': board,
                'hand_desc': desc,
                'actual': f"{actual_action} ${actual_amount:.2f}",
                'strategy': f"{action} ${amount:.2f}",
                'reasoning': reasoning[:100]
            })
    
    return {
        'total_hands': len(hands),
        'differences': differences,
        'high_card_bets': high_card_bets,
        'pocket_checks': pocket_checks,
        'overbets': overbets
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 compare_strategies_on_session.py <log_file>")
        sys.exit(1)
    
    log_file = sys.argv[1]
    
    print(f"=== COMPARING STRATEGIES ON: {log_file.split('/')[-1]} ===\n")
    
    # Analyze with both strategies
    maniac_results = analyze_session(log_file, 'value_maniac')
    lord_results = analyze_session(log_file, 'value_lord')
    
    print(f"Total postflop hands: {maniac_results['total_hands']}")
    print()
    
    print("=== value_maniac (what you played) ===")
    print(f"  High card c-bets: {maniac_results['high_card_bets']}")
    print(f"  Pocket pair checks: {maniac_results['pocket_checks']}")
    print(f"  Overbets: {maniac_results['overbets']}")
    print()
    
    print("=== value_lord (new strategy) ===")
    print(f"  High card c-bets: {lord_results['high_card_bets']}")
    print(f"  Pocket pair checks: {lord_results['pocket_checks']}")
    print(f"  Overbets: {lord_results['overbets']}")
    print()
    
    # Show key differences
    print("=== KEY DIFFERENCES (value_lord would play differently) ===")
    if lord_results['differences']:
        for diff in lord_results['differences'][:15]:
            print(f"\nHand #{diff['hand_num']}")
            print(f"  Cards: {diff['hole']} | Board: {diff['board']}")
            print(f"  Hand: {diff['hand_desc']}")
            print(f"  You did: {diff['actual']}")
            print(f"  value_lord: {diff['strategy']}")
            print(f"  Why: {diff['reasoning']}")
    else:
        print("No differences - both strategies would play identically!")
