#!/usr/bin/env python3
"""
Comprehensive strategy evaluation on real PokerStars hand histories.
Shows what each strategy would do differently and the impact.
"""

import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poker_logic import preflop_action, postflop_action, STRATEGIES, analyze_hand

ALL_STRATEGIES = ['kiro_lord', 'kiro_optimal', 'sonnet', 'value_lord', 'fish', 'nit', 'tag', 'lag', 'maniac']

def hand_to_str(cards):
    """Convert ['Ah', 'Kd'] to 'AKo'"""
    if len(cards) != 2:
        return None
    c1, c2 = cards[0], cards[1]
    r1, s1 = c1[0], c1[1]
    r2, s2 = c2[0], c2[1]
    rank_order = '23456789TJQKA'
    if rank_order.index(r1) < rank_order.index(r2):
        r1, r2 = r2, r1
        s1, s2 = s2, s1
    if r1 == r2:
        return r1 + r2
    elif s1 == s2:
        return r1 + r2 + 's'
    else:
        return r1 + r2 + 'o'

def parse_all_hands(hh_dir):
    """Parse all hand histories."""
    all_hands = []
    
    for filename in os.listdir(hh_dir):
        if not filename.endswith('.txt'):
            continue
        
        if '€0.02-€0.05' in filename:
            bb = 0.05
        elif '€0.05-€0.10' in filename:
            bb = 0.10
        elif '€0.10-€0.25' in filename:
            bb = 0.25
        else:
            continue
        
        filepath = os.path.join(hh_dir, filename)
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        for hand_text in re.split(r'\n\n\n+', content):
            hand = parse_hand(hand_text, bb)
            if hand:
                all_hands.append(hand)
    
    return all_hands

def parse_hand(text, bb):
    """Parse a single hand."""
    if 'Dealt to idealistslp' not in text:
        return None
    
    lines = text.strip().split('\n')
    
    hand = {
        'bb': bb,
        'hero_cards': None,
        'hero_position': None,
        'board': [],
        'preflop_actions': [],
        'postflop_actions': [],
        'hero_invested': 0,
        'hero_won': 0,
        'hero_preflop_action': None,
    }
    
    current_street = 'preflop'
    hero_seat = None
    button_seat = None
    seats = {}
    
    for line in lines:
        # Button
        m = re.match(r"Table.*Seat #(\d+) is the button", line)
        if m:
            button_seat = int(m.group(1))
            continue
        
        # Seats
        m = re.match(r'Seat (\d+): (\S+)', line)
        if m:
            seat_num = int(m.group(1))
            player = m.group(2)
            seats[seat_num] = player
            if player == 'idealistslp':
                hero_seat = seat_num
            continue
        
        # Hero cards
        m = re.match(r'Dealt to idealistslp \[(\w\w) (\w\w)\]', line)
        if m:
            hand['hero_cards'] = [m.group(1), m.group(2)]
            continue
        
        # Streets
        if '*** FLOP ***' in line:
            current_street = 'flop'
            m = re.search(r'\[(\w\w) (\w\w) (\w\w)\]', line)
            if m:
                hand['board'] = [m.group(1), m.group(2), m.group(3)]
        elif '*** TURN ***' in line:
            current_street = 'turn'
            m = re.search(r'\] \[(\w\w)\]', line)
            if m:
                hand['board'].append(m.group(1))
        elif '*** RIVER ***' in line:
            current_street = 'river'
            m = re.search(r'\] \[(\w\w)\]', line)
            if m:
                hand['board'].append(m.group(1))
        
        # Hero actions
        if line.startswith('idealistslp:'):
            m = re.search(r'€([\d.]+)', line)
            if m:
                hand['hero_invested'] += float(m.group(1))
            
            action = None
            if ': folds' in line:
                action = 'fold'
            elif ': checks' in line:
                action = 'check'
            elif ': calls' in line:
                action = 'call'
            elif ': bets' in line:
                action = 'bet'
            elif ': raises' in line:
                action = 'raise'
            
            if action and current_street == 'preflop' and hand['hero_preflop_action'] is None:
                hand['hero_preflop_action'] = action
            
            if action and current_street != 'preflop':
                hand['postflop_actions'].append({
                    'street': current_street,
                    'action': action,
                    'amount': float(m.group(1)) if m else 0
                })
        
        # Villain actions (for facing detection)
        for player in seats.values():
            if player != 'idealistslp' and line.startswith(f'{player}:'):
                if ': raises' in line:
                    m = re.search(r'to €([\d.]+)', line)
                    amt = float(m.group(1)) if m else 0
                    if current_street == 'preflop':
                        hand['preflop_actions'].append({'action': 'raise', 'amount': amt})
                    else:
                        hand['postflop_actions'].append({
                            'street': current_street,
                            'action': 'villain_raise',
                            'amount': amt
                        })
                elif ': bets' in line:
                    m = re.search(r'€([\d.]+)', line)
                    amt = float(m.group(1)) if m else 0
                    if current_street != 'preflop':
                        hand['postflop_actions'].append({
                            'street': current_street,
                            'action': 'villain_bet',
                            'amount': amt
                        })
        
        # Won - only count 'from pot' to avoid double-counting with summary line
        if 'idealistslp collected €' in line and 'from pot' in line:
            m = re.search(r'€([\d.]+)', line)
            if m:
                hand['hero_won'] += float(m.group(1))
    
    # Calculate position
    if hero_seat and button_seat and seats:
        active_seats = sorted(seats.keys())
        n = len(active_seats)
        btn_idx = active_seats.index(button_seat) if button_seat in active_seats else 0
        hero_idx = active_seats.index(hero_seat) if hero_seat in active_seats else 0
        rel_pos = (hero_idx - btn_idx) % n
        
        positions = ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO'][:n] if n <= 6 else ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO']
        hand['hero_position'] = positions[rel_pos] if rel_pos < len(positions) else 'BTN'
    
    hand['hero_profit'] = hand['hero_won'] - hand['hero_invested']
    hand['profit_bb'] = hand['hero_profit'] / bb
    hand['hand_str'] = hand_to_str(hand['hero_cards'])
    
    if hand['hero_cards']:
        return hand
    return None

def get_preflop_facing(hand):
    """Determine what hero faces preflop."""
    facing = 'none'
    to_call = hand['bb']
    
    for action in hand['preflop_actions']:
        if action['action'] == 'raise':
            if facing == 'none':
                facing = 'open'
            elif facing == 'open':
                facing = '3bet'
            elif facing == '3bet':
                facing = '4bet'
            to_call = action['amount']
    
    # Adjust for blinds
    if hand['hero_position'] == 'SB':
        to_call = max(0, to_call - hand['bb']/2)
    elif hand['hero_position'] == 'BB':
        if facing == 'none':
            to_call = 0
        else:
            to_call = max(0, to_call - hand['bb'])
    
    return facing, to_call

def evaluate_preflop(hand, strategy_name):
    """Get strategy's preflop decision."""
    strategy = STRATEGIES.get(strategy_name)
    if not strategy or not hand['hand_str'] or not hand['hero_position']:
        return None, None
    
    facing, to_call = get_preflop_facing(hand)
    
    try:
        action, reason = preflop_action(
            hand['hand_str'],
            hand['hero_position'],
            strategy,
            facing,
            'MP'  # Default opener position
        )
        return action, reason
    except:
        return None, None

def get_postflop_situations(hand):
    """Get postflop decision points where hero faced a bet."""
    situations = []
    
    is_aggressor = hand['hero_preflop_action'] == 'raise'
    
    for street in ['flop', 'turn', 'river']:
        board_len = {'flop': 3, 'turn': 4, 'river': 5}[street]
        if len(hand['board']) < board_len:
            continue
        
        board = hand['board'][:board_len]
        pot = 0
        to_call = 0
        hero_action_on_street = None
        
        # Calculate pot and find hero's decision
        for action in hand['postflop_actions']:
            if action['street'] != street:
                if action['street'] in ['flop', 'turn', 'river']:
                    # Previous street
                    if action['action'] in ['call', 'bet', 'raise', 'villain_bet', 'villain_raise']:
                        pot += action.get('amount', 0)
                continue
            
            if action['action'] in ['villain_bet', 'villain_raise']:
                to_call = action['amount']
                pot += action['amount']
            elif action['action'] in ['fold', 'check', 'call', 'bet', 'raise']:
                hero_action_on_street = action['action']
                break
        
        if to_call > 0 and hero_action_on_street:
            situations.append({
                'street': street,
                'board': board,
                'pot': pot,
                'to_call': to_call,
                'is_aggressor': is_aggressor,
                'hero_action': hero_action_on_street
            })
    
    return situations

def evaluate_postflop(hand, situation, strategy_name):
    """Get strategy's postflop decision."""
    try:
        action, size, reason = postflop_action(
            hand['hero_cards'],
            situation['board'],
            situation['pot'],
            situation['to_call'],
            street=situation['street'],
            is_ip=True,
            is_aggressor=situation['is_aggressor'],
            strategy=strategy_name
        )
        return action, reason
    except:
        return None, None

def main():
    hh_dir = '/home/ubuntu/mcpprojects/onyxpoker/idealistslp_extracted'
    all_hands = parse_all_hands(hh_dir)
    
    print("=" * 130)
    print("COMPREHENSIVE STRATEGY EVALUATION ON REAL POKERSTARS HANDS")
    print("=" * 130)
    print()
    
    # Basic stats
    print(f"Total hands parsed: {len(all_hands)}")
    
    total_profit = sum(h['hero_profit'] for h in all_hands)
    total_bb = sum(h['profit_bb'] for h in all_hands)
    
    print(f"Actual results: €{total_profit:.2f} ({total_bb:.1f} BB, {total_bb/len(all_hands)*100:.1f} BB/100)")
    print()
    
    # By stakes
    for stakes, bb_val in [('5NL', 0.05), ('10NL', 0.10), ('25NL', 0.25)]:
        hands = [h for h in all_hands if h['bb'] == bb_val]
        if hands:
            profit = sum(h['hero_profit'] for h in hands)
            profit_bb = sum(h['profit_bb'] for h in hands)
            print(f"  {stakes}: {len(hands)} hands, €{profit:.2f} ({profit_bb:.1f} BB, {profit_bb/len(hands)*100:.1f} BB/100)")
    print()
    
    # Hands played vs folded
    played = [h for h in all_hands if h['hero_preflop_action'] and h['hero_preflop_action'] != 'fold']
    folded = [h for h in all_hands if h['hero_preflop_action'] == 'fold' or h['hero_preflop_action'] is None]
    
    print(f"Hands played: {len(played)} ({len(played)/len(all_hands)*100:.1f}%)")
    print(f"Hands folded preflop: {len(folded)} ({len(folded)/len(all_hands)*100:.1f}%)")
    print()
    
    # Evaluate strategies
    results = {}
    for strategy in ALL_STRATEGIES:
        results[strategy] = {
            'pf_would_fold': [],  # Hands where strategy would fold but hero played
            'pf_would_play': [],  # Hands where strategy would play but hero folded
            'post_would_fold': [],  # Postflop spots where strategy would fold
        }
    
    for hand in all_hands:
        if not hand['hero_position'] or not hand['hand_str']:
            continue
        
        for strategy in ALL_STRATEGIES:
            strat_action, _ = evaluate_preflop(hand, strategy)
            
            if strat_action == 'fold' and hand['hero_preflop_action'] and hand['hero_preflop_action'] != 'fold':
                # Strategy would fold, hero played
                results[strategy]['pf_would_fold'].append(hand)
            elif strat_action and strat_action != 'fold' and (hand['hero_preflop_action'] == 'fold' or hand['hero_preflop_action'] is None):
                # Strategy would play, hero folded
                results[strategy]['pf_would_play'].append(hand)
        
        # Postflop evaluation - only for hands strategy would PLAY preflop
        # (if strategy folds preflop, it never sees postflop)
        if hand['hero_preflop_action'] and hand['hero_preflop_action'] != 'fold':
            situations = get_postflop_situations(hand)
            for strategy in ALL_STRATEGIES:
                # Skip if strategy would fold preflop (already counted above)
                strat_pf_action, _ = evaluate_preflop(hand, strategy)
                if strat_pf_action == 'fold':
                    continue
                
                # Only count FIRST postflop fold (if fold flop, won't see turn)
                for sit in situations:
                    strat_action, _ = evaluate_postflop(hand, sit, strategy)
                    if strat_action == 'fold' and sit['hero_action'] != 'fold':
                        results[strategy]['post_would_fold'].append({
                            'hand': hand,
                            'situation': sit
                        })
                        break  # Only count first fold per hand
    
    # Calculate impact
    print("=" * 100)
    print("STRATEGY IMPACT ANALYSIS (No Double-Counting)")
    print("=" * 100)
    print()
    print("This shows what would happen if you followed each strategy instead of actual play:")
    print()
    print(f"{'Strategy':<15} {'PF Folds':>8} {'PF Save€':>10} {'PF Miss€':>10} {'Post Folds':>10} {'Post Save€':>10} {'Post Miss€':>10} {'NET €':>10}")
    print("-" * 100)
    
    ranked = []
    for strategy in ALL_STRATEGIES:
        r = results[strategy]
        
        # Preflop: hands strategy would fold that hero played
        pf_saved = sum(abs(h['hero_profit']) for h in r['pf_would_fold'] if h['hero_profit'] < 0)
        pf_missed = sum(h['hero_profit'] for h in r['pf_would_fold'] if h['hero_profit'] > 0)
        
        # Postflop: spots strategy would fold (already filtered for no overlap)
        post_saved = sum(abs(h['hand']['hero_profit']) for h in r['post_would_fold'] if h['hand']['hero_profit'] < 0)
        post_missed = sum(h['hand']['hero_profit'] for h in r['post_would_fold'] if h['hand']['hero_profit'] > 0)
        
        net = (pf_saved - pf_missed) + (post_saved - post_missed)
        
        ranked.append({
            'strategy': strategy,
            'pf_folds': len(r['pf_would_fold']),
            'pf_saved': pf_saved,
            'pf_missed': pf_missed,
            'post_folds': len(r['post_would_fold']),
            'post_saved': post_saved,
            'post_missed': post_missed,
            'net': net
        })
    
    ranked.sort(key=lambda x: x['net'], reverse=True)
    
    for r in ranked:
        print(f"{r['strategy']:<15} {r['pf_folds']:>8} {r['pf_saved']:>10.2f} {r['pf_missed']:>10.2f} "
              f"{r['post_folds']:>10} {r['post_saved']:>10.2f} {r['post_missed']:>10.2f} {r['net']:>+10.2f}")
    
    # Top strategy details
    top = ranked[0]['strategy']
    print()
    print("=" * 130)
    print(f"TOP STRATEGY DETAILS: {top}")
    print("=" * 130)
    
    # Preflop folds that saved money
    pf_folds = results[top]['pf_would_fold']
    saves = sorted([h for h in pf_folds if h['profit_bb'] < 0], key=lambda x: x['profit_bb'])
    misses = sorted([h for h in pf_folds if h['profit_bb'] > 0], key=lambda x: -x['profit_bb'])
    
    print(f"\nPREFLOP: Would fold {len(pf_folds)} hands that hero played")
    print(f"  Saves: {len(saves)} hands, {sum(abs(h['profit_bb']) for h in saves):.1f} BB")
    print(f"  Misses: {len(misses)} hands, {sum(h['profit_bb'] for h in misses):.1f} BB")
    
    print(f"\n  BIGGEST SAVES:")
    for h in saves[:10]:
        facing, _ = get_preflop_facing(h)
        print(f"    {h['hand_str']:<6} {h['hero_position']:<3} facing {facing:<5} -> saved {abs(h['profit_bb']):.1f} BB")
    
    print(f"\n  BIGGEST MISSES:")
    for h in misses[:10]:
        facing, _ = get_preflop_facing(h)
        print(f"    {h['hand_str']:<6} {h['hero_position']:<3} facing {facing:<5} -> missed {h['profit_bb']:.1f} BB")
    
    # Postflop folds
    post_folds = results[top]['post_would_fold']
    post_saves = [p for p in post_folds if p['hand']['profit_bb'] < 0]
    post_misses = [p for p in post_folds if p['hand']['profit_bb'] > 0]
    
    print(f"\nPOSTFLOP: Would fold {len(post_folds)} spots where hero called/raised")
    print(f"  Saves: {len(post_saves)} spots, {sum(abs(p['hand']['profit_bb']) for p in post_saves):.1f} BB")
    print(f"  Misses: {len(post_misses)} spots, {sum(p['hand']['profit_bb'] for p in post_misses):.1f} BB")
    
    post_saves.sort(key=lambda x: x['hand']['profit_bb'])
    print(f"\n  BIGGEST POSTFLOP SAVES:")
    for p in post_saves[:10]:
        h = p['hand']
        s = p['situation']
        board = ' '.join(s['board'])
        print(f"    {h['hand_str']:<6} on {board:<15} {s['street']:<5} pot={s['pot']:.2f} call={s['to_call']:.2f} -> saved {abs(h['profit_bb']):.1f} BB")
    
    # Strategy comparison on key hands
    print()
    print("=" * 130)
    print("STRATEGY DISAGREEMENTS ON HIGH-IMPACT HANDS")
    print("=" * 130)
    
    # Find hands where strategies disagree
    disagreements = []
    for hand in all_hands:
        if not hand['hero_position'] or not hand['hand_str']:
            continue
        
        actions = {}
        for strategy in ALL_STRATEGIES:
            action, _ = evaluate_preflop(hand, strategy)
            if action:
                actions[strategy] = action
        
        unique = set(actions.values())
        if len(unique) > 1:
            folds = [s for s, a in actions.items() if a == 'fold']
            plays = [s for s, a in actions.items() if a != 'fold']
            
            disagreements.append({
                'hand': hand,
                'folds': folds,
                'plays': plays
            })
    
    disagreements.sort(key=lambda x: abs(x['hand']['profit_bb']), reverse=True)
    
    print(f"\n{len(disagreements)} hands where strategies disagree")
    print(f"\n{'Hand':<6} {'Pos':<4} {'Facing':<6} {'Hero':<6} {'Profit':>8} | Strategies")
    print("-" * 100)
    
    for d in disagreements[:20]:
        h = d['hand']
        facing, _ = get_preflop_facing(h)
        hero_action = h['hero_preflop_action'] or 'fold'
        
        print(f"{h['hand_str']:<6} {h['hero_position']:<4} {facing:<6} {hero_action:<6} {h['profit_bb']:>+8.1f} | "
              f"FOLD:{len(d['folds'])} PLAY:{len(d['plays'])}")
        
        if len(d['folds']) <= 4:
            print(f"       FOLD: {', '.join(d['folds'])}")
        if len(d['plays']) <= 4:
            print(f"       PLAY: {', '.join(d['plays'])}")

if __name__ == '__main__':
    main()
