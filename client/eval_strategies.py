#!/usr/bin/env python3
"""
Evaluate strategies on real session hands.
Tracks key stats and estimates win rate based on poker fundamentals.
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poker_logic import (STRATEGIES, preflop_action, postflop_action, 
                         calculate_equity, evaluate_hand)

STRATEGY_NAMES = ['value_maniac', 'value_max', 'sonnet_max', 'sonnet', 'gpt4', 'gpt3', 
                  'kiro_optimal', 'kiro5', 'kiro_v2', '2nl_exploit', 'aggressive']

def parse_hand(cards_list):
    if not cards_list or len(cards_list) != 2:
        return None
    c1, c2 = cards_list[0], cards_list[1]
    r1, s1 = c1[0].upper(), c1[-1].lower()
    r2, s2 = c2[0].upper(), c2[-1].lower()
    if len(c1) == 3: r1 = 'T'
    if len(c2) == 3: r2 = 'T'
    suited = 's' if s1 == s2 else 'o'
    rank_order = '23456789TJQKA'
    if rank_order.index(r1) < rank_order.index(r2):
        r1, r2 = r2, r1
    if r1 == r2:
        return f"{r1}{r2}"
    return f"{r1}{r2}{suited}"

def parse_board(board_list):
    if not board_list:
        return []
    result = []
    for card in board_list:
        r = card[0].upper()
        if len(card) == 3: r = 'T'
        s = card[-1].lower()
        result.append((r, s))
    return result

def parse_hole(cards_list):
    result = []
    for card in cards_list:
        r = card[0].upper()
        if len(card) == 3: r = 'T'
        s = card[-1].lower()
        result.append((r, s))
    return result

def get_street(board):
    if len(board) == 0: return 'preflop'
    if len(board) == 3: return 'flop'
    if len(board) == 4: return 'turn'
    return 'river'

def get_strategy_action(strat_name, hand, hole_cards, board, pot, to_call, position='BTN'):
    strategy = STRATEGIES.get(strat_name)
    if not strategy:
        return None, 0
    
    street = get_street(board)
    
    if street == 'preflop':
        if to_call <= 0.03:
            facing = 'none'
        elif to_call <= 0.15:
            facing = 'open'
        else:
            facing = '3bet'
        
        action, _ = preflop_action(hand, position, strategy, facing, opener_pos='CO')
        sizing = 0.07 if action == 'raise' and facing == 'none' else to_call * 3 if action == 'raise' else 0
        return action, sizing
    else:
        action, sizing, _ = postflop_action(
            hole_cards, board, pot, to_call, street,
            is_ip=True, is_aggressor=True,
            strategy=strat_name, num_opponents=1
        )
        return action, sizing

def main():
    log_dir = '../server/uploads'
    
    all_hands = []
    for fname in sorted(os.listdir(log_dir)):
        if fname.startswith('session_') and fname.endswith('.jsonl'):
            with open(os.path.join(log_dir, fname)) as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        if d.get('hero_cards') and d.get('is_hero_turn'):
                            all_hands.append(d)
                    except:
                        pass
    
    print(f"Evaluating {len(all_hands)} real hands from session logs\n")
    
    # Separate preflop and postflop
    preflop_hands = [h for h in all_hands if not h.get('board')]
    postflop_hands = [h for h in all_hands if h.get('board')]
    
    print(f"Preflop: {len(preflop_hands)}, Postflop: {len(postflop_hands)}\n")
    
    # Track detailed stats
    results = {s: {
        'preflop_fold': 0, 'preflop_call': 0, 'preflop_raise': 0,
        'postflop_fold': 0, 'postflop_check': 0, 'postflop_call': 0, 'postflop_bet': 0, 'postflop_raise': 0,
        'cbet': 0, 'cbet_opp': 0,
        'value_bet': 0, 'bluff': 0,
        'good_folds': 0, 'bad_folds': 0,  # Fold with <30% equity = good, >50% = bad
        'good_calls': 0, 'bad_calls': 0,  # Call with >pot_odds equity = good
        'value_raises': 0,  # Raises with strong hands
    } for s in STRATEGY_NAMES}
    
    BB = 0.02
    
    # Process preflop
    for hd in preflop_hands:
        hand = parse_hand(hd['hero_cards'])
        if not hand:
            continue
        
        for strat in STRATEGY_NAMES:
            try:
                action, _ = get_strategy_action(strat, hand, [], [], 0, 
                                                float(hd.get('to_call') or 0))
                if not action:
                    continue
                action = action.lower()
                if action == 'fold':
                    results[strat]['preflop_fold'] += 1
                elif action == 'call':
                    results[strat]['preflop_call'] += 1
                elif action in ['raise', 'bet']:
                    results[strat]['preflop_raise'] += 1
            except:
                pass
    
    # Process postflop
    for hd in postflop_hands:
        hand = parse_hand(hd['hero_cards'])
        hole = parse_hole(hd['hero_cards'])
        board = parse_board(hd['board'])
        pot = float(hd.get('pot') or 0)
        to_call = float(hd.get('to_call') or 0)
        
        if not hand:
            continue
        
        street = get_street(board)
        
        # Calculate equity
        equity = calculate_equity(hole, board, num_opponents=1, simulations=300) / 100.0
        
        # Evaluate hand strength
        hand_eval = evaluate_hand(hole, board)
        hand_strength = hand_eval[0] if hand_eval else 'high card'
        
        # Is this a value hand? (pair or better)
        is_value_hand = hand_strength not in ['high card']
        
        for strat in STRATEGY_NAMES:
            try:
                action, sizing = get_strategy_action(strat, hand, hole, board, pot, to_call)
                if not action:
                    continue
                action = action.lower()
                
                # Track actions
                if action == 'fold':
                    results[strat]['postflop_fold'] += 1
                    if equity < 0.30:
                        results[strat]['good_folds'] += 1
                    elif equity > 0.50:
                        results[strat]['bad_folds'] += 1
                elif action == 'check':
                    results[strat]['postflop_check'] += 1
                elif action == 'call':
                    results[strat]['postflop_call'] += 1
                    pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0
                    if equity >= pot_odds:
                        results[strat]['good_calls'] += 1
                    else:
                        results[strat]['bad_calls'] += 1
                elif action in ['raise', 'bet']:
                    if to_call > 0:  # Facing bet = raise
                        results[strat]['postflop_raise'] += 1
                        if is_value_hand:
                            results[strat]['value_raises'] += 1
                    else:  # No bet = bet
                        results[strat]['postflop_bet'] += 1
                    if is_value_hand:
                        results[strat]['value_bet'] += 1
                    else:
                        results[strat]['bluff'] += 1
                
                # C-bet tracking (flop, no bet to call)
                if street == 'flop' and to_call == 0:
                    results[strat]['cbet_opp'] += 1
                    if action in ['bet', 'raise']:
                        results[strat]['cbet'] += 1
                        
            except:
                pass
    
    # Calculate derived stats and print
    print("=" * 90)
    print("STRATEGY STATS ON REAL 2NL HANDS")
    print("=" * 90)
    
    print(f"\n{'Strategy':<14} {'VPIP%':<8} {'PFR%':<8} {'CBet%':<8} {'Fold%':<8} {'Agg%':<8}")
    print("-" * 60)
    
    for strat in STRATEGY_NAMES:
        r = results[strat]
        
        # Preflop stats
        pre_total = r['preflop_fold'] + r['preflop_call'] + r['preflop_raise']
        vpip = (r['preflop_call'] + r['preflop_raise']) / pre_total * 100 if pre_total > 0 else 0
        pfr = r['preflop_raise'] / pre_total * 100 if pre_total > 0 else 0
        
        # Postflop stats
        post_total = r['postflop_fold'] + r['postflop_check'] + r['postflop_call'] + r['postflop_bet']
        fold_pct = r['postflop_fold'] / post_total * 100 if post_total > 0 else 0
        agg = r['postflop_bet'] / (r['postflop_bet'] + r['postflop_call'] + r['postflop_check']) * 100 if (r['postflop_bet'] + r['postflop_call'] + r['postflop_check']) > 0 else 0
        
        # C-bet
        cbet = r['cbet'] / r['cbet_opp'] * 100 if r['cbet_opp'] > 0 else 0
        
        print(f"{strat:<14} {vpip:>5.1f}%   {pfr:>5.1f}%   {cbet:>5.1f}%   {fold_pct:>5.1f}%   {agg:>5.1f}%")
    
    # Quality metrics
    print(f"\n{'Strategy':<14} {'GoodFold':<10} {'BadFold':<10} {'GoodCall':<10} {'BadCall':<10} {'ValBet':<8} {'Raises':<8}")
    print("-" * 80)
    
    for strat in STRATEGY_NAMES:
        r = results[strat]
        print(f"{strat:<14} {r['good_folds']:<10} {r['bad_folds']:<10} {r['good_calls']:<10} {r['bad_calls']:<10} {r['value_bet']:<8} {r['value_raises']:<8}")
    
    # Score calculation
    print("\n" + "=" * 90)
    print("STRATEGY SCORES (higher = better)")
    print("=" * 90)
    
    scores = {}
    for strat in STRATEGY_NAMES:
        r = results[strat]
        
        # Score components:
        # +2 for each good fold, -3 for each bad fold
        # +2 for each good call, -2 for each bad call  
        # +1 for each value bet, -0.5 for each bluff (bluffs are risky)
        # +0.5 for each preflop raise (aggression is good)
        
        score = (
            r['good_folds'] * 2 - r['bad_folds'] * 3 +
            r['good_calls'] * 2 - r['bad_calls'] * 2 +
            r['value_bet'] * 1 - r['bluff'] * 0.5 +
            r['preflop_raise'] * 0.5
        )
        scores[strat] = score
    
    print(f"\n{'Rank':<6} {'Strategy':<14} {'Score':<10} {'Est BB/100':<12}")
    print("-" * 45)
    
    sorted_strats = sorted(STRATEGY_NAMES, key=lambda s: scores[s], reverse=True)
    
    for i, strat in enumerate(sorted_strats, 1):
        score = scores[strat]
        # Rough BB/100 estimate: score / hands * scaling factor
        total_hands = len(all_hands)
        bb_100_est = score / total_hands * 100 * 0.5  # Scale factor
        print(f"{i:<6} {strat:<14} {score:>+8.1f}   {bb_100_est:>+8.1f}")

if __name__ == '__main__':
    main()
