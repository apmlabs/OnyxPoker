#!/usr/bin/env python3
"""
Evaluate strategies on session logs (server/uploads/*.jsonl).
Consolidates: eval_strategies.py, replay_logs.py, compare_strategies_on_session.py

Usage:
    python eval_session_logs.py              # Full stats + replay
    python eval_session_logs.py --stats      # Stats only (VPIP/PFR/CBet)
    python eval_session_logs.py --replay     # Replay disagreements only
    python eval_session_logs.py --compare    # Compare strategies on same hands
"""
import argparse
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poker_logic import STRATEGIES, preflop_action, postflop_action, analyze_hand, calculate_equity

STRATEGY_NAMES = ['the_lord', 'value_lord', 'kiro_lord', 'kiro_optimal', 'sonnet']
POSITIONS = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']

def parse_hand(cards_list):
    """Convert ['As', '3c'] to 'A3o' format."""
    if not cards_list or len(cards_list) != 2:
        return None
    c1, c2 = cards_list[0], cards_list[1]
    r1, s1 = c1[0].upper(), c1[-1].lower()
    r2, s2 = c2[0].upper(), c2[-1].lower()
    if len(c1) == 3: r1 = 'T'
    if len(c2) == 3: r2 = 'T'
    rank_order = '23456789TJQKA'
    if rank_order.index(r1) < rank_order.index(r2):
        r1, r2 = r2, r1
    suited = 's' if s1 == s2 else 'o'
    if r1 == r2:
        return f"{r1}{r2}"
    return f"{r1}{r2}{suited}"

def parse_hole(cards_list):
    """Convert ['As', '3c'] to [(rank, suit), ...]."""
    result = []
    for card in cards_list:
        r = card[0].upper()
        if len(card) == 3: r = 'T'
        s = card[-1].lower()
        result.append((r, s))
    return result

def parse_board(board_list):
    """Convert ['Ah', 'Kd', '5c'] to [(rank, suit), ...]."""
    if not board_list:
        return []
    return parse_hole(board_list)

def get_street(board):
    if len(board) == 0: return 'preflop'
    if len(board) == 3: return 'flop'
    if len(board) == 4: return 'turn'
    return 'river'

def get_strategy_action(strat_name, hand, hole_cards, board, pot, to_call, position='BTN'):
    """Get what a strategy would do."""
    strategy = STRATEGIES.get(strat_name)
    if not strategy:
        return None, 0, None
    
    street = get_street(board)
    
    if street == 'preflop':
        if to_call <= 0.03:
            facing = 'none'
        elif to_call <= 0.15:
            facing = 'open'
        else:
            facing = '3bet'
        action, reason = preflop_action(hand, position, strategy, facing, opener_pos='CO')
        sizing = 0.07 if action == 'raise' and facing == 'none' else to_call * 3 if action == 'raise' else 0
        return action, sizing, reason
    else:
        action, sizing, reason = postflop_action(
            hole_cards, board, pot, to_call, street,
            is_ip=True, is_aggressor=True, strategy=strat_name, num_opponents=1
        )
        return action, sizing, reason

def load_session_logs(log_dir='../server/uploads'):
    """Load all hands from session logs."""
    all_hands = []
    for fname in sorted(os.listdir(log_dir)):
        if fname.startswith('session_') and fname.endswith('.jsonl'):
            with open(os.path.join(log_dir, fname)) as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        if d.get('hero_cards'):
                            all_hands.append(d)
                    except:
                        pass
    return all_hands

def run_stats(all_hands):
    """Calculate VPIP/PFR/CBet stats for each strategy."""
    preflop_hands = [h for h in all_hands if not h.get('board')]
    postflop_hands = [h for h in all_hands if h.get('board')]
    
    print(f"Preflop: {len(preflop_hands)}, Postflop: {len(postflop_hands)}\n")
    
    results = {s: {
        'pf_fold': 0, 'pf_call': 0, 'pf_raise': 0,
        'post_fold': 0, 'post_check': 0, 'post_call': 0, 'post_bet': 0,
        'cbet': 0, 'cbet_opp': 0,
        'good_folds': 0, 'bad_folds': 0, 'good_calls': 0, 'bad_calls': 0,
    } for s in STRATEGY_NAMES}
    
    # Preflop
    for i, hd in enumerate(preflop_hands):
        hand = parse_hand(hd['hero_cards'])
        if not hand:
            continue
        pos = POSITIONS[i % 6]
        to_call = float(hd.get('to_call') or 0)
        
        for strat in STRATEGY_NAMES:
            try:
                action, _, _ = get_strategy_action(strat, hand, [], [], 0, to_call, pos)
                if not action:
                    continue
                action = action.lower()
                if action == 'fold':
                    results[strat]['pf_fold'] += 1
                elif action == 'call':
                    results[strat]['pf_call'] += 1
                elif action in ['raise', 'bet']:
                    results[strat]['pf_raise'] += 1
            except:
                pass
    
    # Postflop
    for hd in postflop_hands:
        hand = parse_hand(hd['hero_cards'])
        hole = parse_hole(hd['hero_cards'])
        board = parse_board(hd['board'])
        pot = float(hd.get('pot') or 0)
        to_call = float(hd.get('to_call') or 0)
        
        if not hand:
            continue
        
        street = get_street(board)
        hand_info = analyze_hand(hole, board)
        strength = hand_info.get('strength', 1) if hand_info else 1
        
        for strat in STRATEGY_NAMES:
            try:
                action, _, _ = get_strategy_action(strat, hand, hole, board, pot, to_call)
                if not action:
                    continue
                action = action.lower()
                
                pot_pct = to_call / pot if pot > 0 else 0
                
                if action == 'fold':
                    results[strat]['post_fold'] += 1
                    # Bad fold = strong hand vs small bet
                    if strength >= 4 and pot_pct < 0.5:
                        results[strat]['bad_folds'] += 1
                    elif strength == 3 and pot_pct < 0.33:
                        results[strat]['bad_folds'] += 1
                    else:
                        results[strat]['good_folds'] += 1
                elif action == 'check':
                    results[strat]['post_check'] += 1
                elif action == 'call':
                    results[strat]['post_call'] += 1
                    pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0
                    equity = calculate_equity(hole, board, num_opponents=1, simulations=200) / 100.0
                    if equity >= pot_odds:
                        results[strat]['good_calls'] += 1
                    else:
                        results[strat]['bad_calls'] += 1
                elif action in ['raise', 'bet']:
                    results[strat]['post_bet'] += 1
                
                # C-bet tracking
                if street == 'flop' and to_call == 0:
                    results[strat]['cbet_opp'] += 1
                    if action in ['bet', 'raise']:
                        results[strat]['cbet'] += 1
            except:
                pass
    
    # Print stats
    print(f"{'Strategy':<14} {'VPIP%':<8} {'PFR%':<8} {'CBet%':<8} {'Fold%':<8}")
    print("-" * 50)
    
    for strat in STRATEGY_NAMES:
        r = results[strat]
        pre_total = r['pf_fold'] + r['pf_call'] + r['pf_raise']
        vpip = (r['pf_call'] + r['pf_raise']) / pre_total * 100 if pre_total > 0 else 0
        pfr = r['pf_raise'] / pre_total * 100 if pre_total > 0 else 0
        post_total = r['post_fold'] + r['post_check'] + r['post_call'] + r['post_bet']
        fold_pct = r['post_fold'] / post_total * 100 if post_total > 0 else 0
        cbet = r['cbet'] / r['cbet_opp'] * 100 if r['cbet_opp'] > 0 else 0
        print(f"{strat:<14} {vpip:>5.1f}%   {pfr:>5.1f}%   {cbet:>5.1f}%   {fold_pct:>5.1f}%")
    
    print(f"\n{'Strategy':<14} {'GoodFold':<10} {'BadFold':<10} {'GoodCall':<10} {'BadCall':<10}")
    print("-" * 55)
    for strat in STRATEGY_NAMES:
        r = results[strat]
        print(f"{strat:<14} {r['good_folds']:<10} {r['bad_folds']:<10} {r['good_calls']:<10} {r['bad_calls']:<10}")

def run_replay(all_hands):
    """Replay hands and show disagreements with actual decisions."""
    results = {s: {'agree': 0, 'disagree': 0, 'details': []} for s in STRATEGY_NAMES}
    
    for hand_data in all_hands:
        hand = parse_hand(hand_data['hero_cards'])
        hole = parse_hole(hand_data['hero_cards'])
        board = parse_board(hand_data.get('board', []))
        pot = float(hand_data.get('pot') or 0)
        to_call = float(hand_data.get('to_call') or 0)
        actual = hand_data.get('action', '').lower()
        
        if not hand or not actual:
            continue
        
        for strat in STRATEGY_NAMES:
            try:
                action, _, reason = get_strategy_action(strat, hand, hole, board, pot, to_call)
                if not action:
                    continue
                action = action.lower()
                
                # Normalize
                actual_n = 'bet' if actual == 'raise' else actual
                action_n = 'bet' if action == 'raise' else action
                
                if actual_n == action_n:
                    results[strat]['agree'] += 1
                else:
                    results[strat]['disagree'] += 1
                    board_str = ''.join([f"{r}{s}" for r,s in board]) if board else 'preflop'
                    results[strat]['details'].append({
                        'hand': hand, 'board': board_str, 'pot': pot, 'to_call': to_call,
                        'actual': actual, 'strategy': action, 'reason': (reason or '')[:50]
                    })
            except:
                pass
    
    print(f"{'Strategy':<14} {'Agree':<10} {'Disagree':<10} {'Agreement%':<12}")
    print("-" * 50)
    
    sorted_strats = sorted(STRATEGY_NAMES, 
        key=lambda s: results[s]['agree'] / max(1, results[s]['agree'] + results[s]['disagree']), reverse=True)
    
    for strat in sorted_strats:
        agree = results[strat]['agree']
        disagree = results[strat]['disagree']
        total = agree + disagree
        pct = (agree / total * 100) if total > 0 else 0
        print(f"{strat:<14} {agree:<10} {disagree:<10} {pct:.1f}%")
    
    # Show disagreements for best strategy
    best = sorted_strats[0]
    print(f"\nDISAGREEMENTS: {best} vs actual (first 20)")
    print("-" * 80)
    for d in results[best]['details'][:20]:
        print(f"{d['hand']:<6} {d['board']:<15} pot={d['pot']:.2f} call={d['to_call']:.2f} | actual={d['actual']:<6} strat={d['strategy']:<6}")

def run_compare(all_hands):
    """Compare strategies on same hands where they disagree."""
    print("HANDS WHERE STRATEGIES DISAGREE")
    print("-" * 80)
    
    count = 0
    for hand_data in all_hands:
        if count >= 30:
            break
        
        hand = parse_hand(hand_data['hero_cards'])
        hole = parse_hole(hand_data['hero_cards'])
        board = parse_board(hand_data.get('board', []))
        pot = float(hand_data.get('pot') or 0)
        to_call = float(hand_data.get('to_call') or 0)
        actual = hand_data.get('action', '').lower()
        
        if not hand:
            continue
        
        actions = {}
        for strat in STRATEGY_NAMES:
            try:
                action, _, _ = get_strategy_action(strat, hand, hole, board, pot, to_call)
                if action:
                    actions[strat] = action.lower()
            except:
                pass
        
        if len(set(actions.values())) > 1:
            board_str = ''.join([f"{r}{s}" for r,s in board]) if board else 'preflop'
            print(f"\n{hand} on {board_str} (pot={pot:.2f}, call={to_call:.2f}) actual={actual}")
            for s, a in sorted(actions.items()):
                marker = "*" if a == actual else " "
                print(f"  {marker} {s:<14}: {a}")
            count += 1

def main():
    parser = argparse.ArgumentParser(description='Evaluate strategies on session logs')
    parser.add_argument('--stats', action='store_true', help='Stats only (VPIP/PFR/CBet)')
    parser.add_argument('--replay', action='store_true', help='Replay disagreements only')
    parser.add_argument('--compare', action='store_true', help='Compare strategies on same hands')
    args = parser.parse_args()
    
    all_hands = load_session_logs()
    print(f"Loaded {len(all_hands)} hands from session logs\n")
    
    if not all_hands:
        print("No session logs found in ../server/uploads/")
        return
    
    if args.stats:
        run_stats(all_hands)
    elif args.replay:
        run_replay(all_hands)
    elif args.compare:
        run_compare(all_hands)
    else:
        # Full report
        print("=" * 70)
        print("STRATEGY STATS")
        print("=" * 70)
        run_stats(all_hands)
        print("\n" + "=" * 70)
        print("REPLAY AGREEMENT")
        print("=" * 70)
        run_replay(all_hands)

if __name__ == '__main__':
    main()
