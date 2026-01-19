#!/usr/bin/env python3
"""Replay real session logs through all strategies and compare decisions."""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poker_logic import STRATEGIES, preflop_action, postflop_action

STRATEGY_NAMES = ['kiro_lord', 'kiro_optimal', 'sonnet', 'value_lord']

def parse_hand(cards_list):
    """Convert ['As', '3c'] to 'A3o' format"""
    if not cards_list or len(cards_list) != 2:
        return None
    c1, c2 = cards_list[0], cards_list[1]
    r1, s1 = c1[0].upper(), c1[-1].lower()
    r2, s2 = c2[0].upper(), c2[-1].lower()
    # Handle 10
    if len(c1) == 3: r1 = 'T'
    if len(c2) == 3: r2 = 'T'
    suited = 's' if s1 == s2 else 'o'
    rank_order = '23456789TJQKA'
    if rank_order.index(r1) < rank_order.index(r2):
        r1, r2 = r2, r1
    if r1 == r2:
        return f"{r1}{r2}"
    return f"{r1}{r2}{suited}"

def parse_board_for_postflop(board_list):
    """Convert ['Ah', 'Kd', '5c'] to list of (rank, suit) tuples"""
    if not board_list:
        return []
    result = []
    for card in board_list:
        r = card[0].upper()
        if len(card) == 3: r = 'T'  # Handle 10
        s = card[-1].lower()
        result.append((r, s))
    return result

def parse_hole_for_postflop(cards_list):
    """Convert ['As', '3c'] to list of (rank, suit) tuples"""
    if not cards_list or len(cards_list) != 2:
        return []
    result = []
    for card in cards_list:
        r = card[0].upper()
        if len(card) == 3: r = 'T'
        s = card[-1].lower()
        result.append((r, s))
    return result

def get_street(board):
    """Determine street from board length"""
    if len(board) == 0: return 'preflop'
    if len(board) == 3: return 'flop'
    if len(board) == 4: return 'turn'
    return 'river'

def get_strategy_action(strat_name, hand, hole_cards, board, pot, to_call, position='BTN'):
    """Get what a strategy would do in this spot"""
    strategy = STRATEGIES.get(strat_name)
    if not strategy:
        return None, None
    
    street = get_street(board)
    
    if street == 'preflop':
        # Determine facing situation
        if to_call <= 0.03:
            facing = 'none'  # RFI opportunity
        elif to_call <= 0.15:
            facing = 'open'  # Facing single raise
        else:
            facing = '3bet'  # Facing 3bet
        
        action, reason = preflop_action(hand, position, strategy, facing, opener_pos='CO')
        return action, reason
    else:
        # Postflop
        facing_bet = to_call > 0
        action, sizing, reason = postflop_action(
            hole_cards, board, pot, to_call, street,
            is_ip=True, is_aggressor=True,
            archetype=None, strategy=strat_name,
            num_opponents=1
        )
        return action, reason

def main():
    log_dir = '../server/uploads'
    
    # Load all hands
    all_hands = []
    for fname in sorted(os.listdir(log_dir)):
        if fname.startswith('session_') and fname.endswith('.jsonl'):
            fpath = os.path.join(log_dir, fname)
            with open(fpath) as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        if d.get('hero_cards'):
                            all_hands.append(d)
                    except:
                        pass
    
    print(f"Loaded {len(all_hands)} actionable hands from session logs\n")
    
    # Track results
    results = {s: {'agree': 0, 'disagree': 0, 'details': []} for s in STRATEGY_NAMES}
    
    for hand_data in all_hands:
        hand = parse_hand(hand_data['hero_cards'])
        hole_cards = parse_hole_for_postflop(hand_data['hero_cards'])
        board = parse_board_for_postflop(hand_data.get('board', []))
        pot = float(hand_data.get('pot') or 0)
        to_call = float(hand_data.get('to_call') or 0)
        actual_action = hand_data.get('action', '').lower()
        
        if not hand or not actual_action:
            continue
        
        for strat_name in STRATEGY_NAMES:
            try:
                strat_action, reason = get_strategy_action(
                    strat_name, hand, hole_cards, board, pot, to_call
                )
                if not strat_action:
                    continue
                    
                strat_action = strat_action.lower()
                
                # Normalize for comparison
                actual_norm = actual_action
                if actual_norm == 'raise': actual_norm = 'bet'
                strat_norm = strat_action
                if strat_norm == 'raise': strat_norm = 'bet'
                
                agrees = (actual_norm == strat_norm)
                
                if agrees:
                    results[strat_name]['agree'] += 1
                else:
                    results[strat_name]['disagree'] += 1
                    board_str = ''.join([f"{r}{s}" for r,s in board]) if board else 'preflop'
                    results[strat_name]['details'].append({
                        'hand': hand,
                        'board': board_str,
                        'pot': pot,
                        'to_call': to_call,
                        'actual': actual_action,
                        'strategy': strat_action,
                        'reason': reason[:50] if reason else ''
                    })
            except Exception as e:
                pass
    
    # Print summary
    print("=" * 70)
    print("STRATEGY AGREEMENT WITH ACTUAL DECISIONS")
    print("=" * 70)
    print(f"\n{'Strategy':<15} {'Agree':<10} {'Disagree':<10} {'Agreement %':<12}")
    print("-" * 50)
    
    sorted_strats = sorted(STRATEGY_NAMES, 
                          key=lambda s: results[s]['agree'] / max(1, results[s]['agree'] + results[s]['disagree']),
                          reverse=True)
    
    for strat_name in sorted_strats:
        agree = results[strat_name]['agree']
        disagree = results[strat_name]['disagree']
        total = agree + disagree
        pct = (agree / total * 100) if total > 0 else 0
        print(f"{strat_name:<15} {agree:<10} {disagree:<10} {pct:.1f}%")
    
    # Show disagreements for top strategy
    best = sorted_strats[0]
    print(f"\n{'=' * 70}")
    print(f"DISAGREEMENTS: {best} vs actual (first 30)")
    print("=" * 70)
    
    for d in results[best]['details'][:30]:
        print(f"{d['hand']:<6} {d['board']:<15} pot={d['pot']:.2f} call={d['to_call']:.2f} | actual={d['actual']:<6} strat={d['strategy']:<6} | {d['reason']}")
    
    # Show what each strategy would do differently
    print(f"\n{'=' * 70}")
    print("STRATEGY DIFFERENCES ON SAME HANDS")
    print("=" * 70)
    
    # Find hands where strategies disagree with each other
    sample_hands = all_hands[:50]
    for hand_data in sample_hands:
        hand = parse_hand(hand_data['hero_cards'])
        hole_cards = parse_hole_for_postflop(hand_data['hero_cards'])
        board = parse_board_for_postflop(hand_data.get('board', []))
        pot = float(hand_data.get('pot') or 0)
        to_call = float(hand_data.get('to_call') or 0)
        actual = hand_data.get('action', '').lower()
        
        if not hand:
            continue
        
        actions = {}
        for strat_name in STRATEGY_NAMES:
            try:
                action, _ = get_strategy_action(strat_name, hand, hole_cards, board, pot, to_call)
                if action:
                    actions[strat_name] = action.lower()
            except:
                pass
        
        # Only show if strategies disagree
        if len(set(actions.values())) > 1:
            board_str = ''.join([f"{r}{s}" for r,s in board]) if board else 'preflop'
            print(f"\n{hand} on {board_str} (pot={pot:.2f}, call={to_call:.2f}) actual={actual}")
            for s, a in sorted(actions.items()):
                marker = "✓" if a == actual else " "
                print(f"  {marker} {s:<12}: {a}")

if __name__ == '__main__':
    main()
