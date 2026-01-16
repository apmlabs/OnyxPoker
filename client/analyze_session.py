#!/usr/bin/env python3
"""Analyze a single session hand by hand with multiple strategies."""
import re
import sys
sys.path.insert(0, '.')
from poker_logic import preflop_action, postflop_action, STRATEGIES, analyze_hand

def parse_cards(s):
    return s.strip().split()

def get_position(seat_num, button_seat, seats):
    active = sorted(seats)
    btn_idx = active.index(button_seat)
    my_idx = active.index(seat_num)
    dist = (my_idx - btn_idx) % len(active)
    
    if len(active) == 6:
        positions = ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO']
    elif len(active) == 5:
        positions = ['BTN', 'SB', 'BB', 'UTG', 'CO']
    elif len(active) == 4:
        positions = ['BTN', 'SB', 'BB', 'CO']
    else:
        positions = ['BTN', 'SB', 'BB']
    
    return positions[dist % len(positions)]

def hand_to_str(cards):
    if len(cards) != 2:
        return '??'
    r1, s1 = cards[0][0], cards[0][1]
    r2, s2 = cards[1][0], cards[1][1]
    
    rank_order = '23456789TJQKA'
    if rank_order.index(r1) < rank_order.index(r2):
        r1, r2 = r2, r1
        s1, s2 = s2, s1
    
    suited = 's' if s1 == s2 else 'o'
    if r1 == r2:
        return f'{r1}{r2}'
    return f'{r1}{r2}{suited}'

def get_strategy_action(strat_name, hand_str, hole_cards, board, pot, to_call, position, bb=0.05):
    strategy = STRATEGIES.get(strat_name)
    if not strategy:
        return 'unknown', 'no strategy'
    
    if not board:
        if to_call <= bb:
            facing = 'none'
        elif to_call <= 4 * bb:
            facing = 'open'
        else:
            facing = '3bet'
        
        action, reason = preflop_action(hand_str, position, strategy, facing, opener_pos='CO')
        return action, reason
    else:
        street = 'flop' if len(board) == 3 else ('turn' if len(board) == 4 else 'river')
        action, size, reason = postflop_action(
            hole_cards, board, pot, to_call, 
            street=street, is_ip=True, is_aggressor=True, strategy=strat_name, num_opponents=1
        )
        return action, reason

def main():
    hh_file = '/home/ubuntu/mcpprojects/onyxpoker/idealistslp_extracted/HH20260116 Asterope #2 - \u20ac0.02-\u20ac0.05 - EUR No Limit Hold\'em.txt'
    
    with open(hh_file, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    hands = content.split('\n\n\n')
    bb = 0.05
    strategies = ['kiro_lord', 'kiro_optimal', 'value_lord']
    
    print(f"{'#':>3} {'Hand':<6} {'Pos':<4} {'Board':<15} {'Pot':>5} {'Call':>5} {'Hero':<6} {'Result':>7} | {'kiro_lord':<12} {'kiro_optimal':<12} {'value_lord':<12}")
    print("-" * 120)
    
    hand_num = 0
    totals = {s: 0.0 for s in strategies}
    
    for hand_text in hands:
        if 'Dealt to idealistslp' not in hand_text:
            continue
        
        hand_num += 1
        
        m = re.search(r'Dealt to idealistslp \[(\w\w) (\w\w)\]', hand_text)
        if not m:
            continue
        hole_cards = [m.group(1), m.group(2)]
        hand_str = hand_to_str(hole_cards)
        
        m = re.search(r"Seat #(\d) is the button", hand_text)
        button_seat = int(m.group(1)) if m else 1
        
        m = re.search(r"Seat (\d): idealistslp", hand_text)
        hero_seat = int(m.group(1)) if m else 1
        
        seats = list(set([int(x) for x in re.findall(r"Seat (\d):", hand_text)]))
        position = get_position(hero_seat, button_seat, seats)
        
        board = []
        flop_m = re.search(r'\*\*\* FLOP \*\*\* \[(\w\w) (\w\w) (\w\w)\]', hand_text)
        if flop_m:
            board = [flop_m.group(1), flop_m.group(2), flop_m.group(3)]
        turn_m = re.search(r'\*\*\* TURN \*\*\* \[\w\w \w\w \w\w\] \[(\w\w)\]', hand_text)
        if turn_m:
            board.append(turn_m.group(1))
        river_m = re.search(r'\*\*\* RIVER \*\*\* \[\w\w \w\w \w\w \w\w\] \[(\w\w)\]', hand_text)
        if river_m:
            board.append(river_m.group(1))
        
        hero_action = 'fold'
        if 'idealistslp: raises' in hand_text or 'idealistslp: bets' in hand_text:
            hero_action = 'raise'
        elif 'idealistslp: calls' in hand_text:
            hero_action = 'call'
        elif 'idealistslp: checks' in hand_text:
            hero_action = 'check'
        
        result = 0.0
        m = re.search(r'idealistslp collected \(?€?([\d.]+)\)?', hand_text)
        if m:
            result = float(m.group(1))
        
        invested = 0.0
        for m in re.finditer(r'idealistslp: calls €?([\d.]+)', hand_text):
            invested += float(m.group(1))
        for m in re.finditer(r'idealistslp: bets €?([\d.]+)', hand_text):
            invested += float(m.group(1))
        for m in re.finditer(r'idealistslp: raises €?[\d.]+ to €?([\d.]+)', hand_text):
            invested += float(m.group(1))
        if 'idealistslp: posts small blind' in hand_text:
            invested += 0.02
        if 'idealistslp: posts big blind' in hand_text:
            invested += 0.05
        
        m = re.search(r'Uncalled bet \(€?([\d.]+)\) returned to idealistslp', hand_text)
        if m:
            invested -= float(m.group(1))
        
        profit = result - invested
        profit_bb = profit / bb
        
        pot = 0.07
        to_call = 0.0
        
        lines = hand_text.split('\n')
        for line in lines:
            if 'idealistslp:' in line and any(x in line for x in ['raises', 'calls', 'folds', 'checks']):
                break
            if 'raises' in line and 'idealistslp' not in line:
                m = re.search(r'raises €?[\d.]+ to €?([\d.]+)', line)
                if m:
                    to_call = float(m.group(1))
                    pot = to_call + 0.07
        
        strat_actions = {}
        for strat in strategies:
            action, reason = get_strategy_action(strat, hand_str, hole_cards, board, pot, to_call, position)
            strat_actions[strat] = action
        
        board_str = ' '.join(board) if board else '--'
        
        print(f"{hand_num:>3} {hand_str:<6} {position:<4} {board_str:<15} {pot:>5.2f} {to_call:>5.2f} {hero_action:<6} {profit_bb:>+7.1f} | {strat_actions['kiro_lord']:<12} {strat_actions['kiro_optimal']:<12} {strat_actions['value_lord']:<12}")
    
    print("-" * 120)
    print(f"Total hands: {hand_num}")
    
    # Calculate what each strategy would have made
    print("\n" + "=" * 80)
    print("STRATEGY PERFORMANCE SUMMARY")
    print("=" * 80)
    
    # Re-run to calculate totals
    strat_results = {s: {'played': 0, 'folded': 0, 'profit': 0.0, 'agree': 0, 'disagree': 0} for s in strategies}
    
    hand_num = 0
    for hand_text in hands:
        if 'Dealt to idealistslp' not in hand_text:
            continue
        
        hand_num += 1
        
        m = re.search(r'Dealt to idealistslp \[(\w\w) (\w\w)\]', hand_text)
        if not m:
            continue
        hole_cards = [m.group(1), m.group(2)]
        hand_str = hand_to_str(hole_cards)
        
        m = re.search(r"Seat #(\d) is the button", hand_text)
        button_seat = int(m.group(1)) if m else 1
        
        m = re.search(r"Seat (\d): idealistslp", hand_text)
        hero_seat = int(m.group(1)) if m else 1
        
        seats = list(set([int(x) for x in re.findall(r"Seat (\d):", hand_text)]))
        position = get_position(hero_seat, button_seat, seats)
        
        board = []
        flop_m = re.search(r'\*\*\* FLOP \*\*\* \[(\w\w) (\w\w) (\w\w)\]', hand_text)
        if flop_m:
            board = [flop_m.group(1), flop_m.group(2), flop_m.group(3)]
        
        hero_action = 'fold'
        if 'idealistslp: raises' in hand_text or 'idealistslp: bets' in hand_text:
            hero_action = 'raise'
        elif 'idealistslp: calls' in hand_text:
            hero_action = 'call'
        elif 'idealistslp: checks' in hand_text:
            hero_action = 'check'
        
        result = 0.0
        m = re.search(r'idealistslp collected \(?€?([\d.]+)\)?', hand_text)
        if m:
            result = float(m.group(1))
        
        invested = 0.0
        for m in re.finditer(r'idealistslp: calls €?([\d.]+)', hand_text):
            invested += float(m.group(1))
        for m in re.finditer(r'idealistslp: bets €?([\d.]+)', hand_text):
            invested += float(m.group(1))
        for m in re.finditer(r'idealistslp: raises €?[\d.]+ to €?([\d.]+)', hand_text):
            invested += float(m.group(1))
        if 'idealistslp: posts small blind' in hand_text:
            invested += 0.02
        if 'idealistslp: posts big blind' in hand_text:
            invested += 0.05
        
        m = re.search(r'Uncalled bet \(€?([\d.]+)\) returned to idealistslp', hand_text)
        if m:
            invested -= float(m.group(1))
        
        profit = result - invested
        profit_bb = profit / bb
        
        pot = 0.07
        to_call = 0.0
        
        lines = hand_text.split('\n')
        for line in lines:
            if 'idealistslp:' in line and any(x in line for x in ['raises', 'calls', 'folds', 'checks']):
                break
            if 'raises' in line and 'idealistslp' not in line:
                m = re.search(r'raises €?[\d.]+ to €?([\d.]+)', line)
                if m:
                    to_call = float(m.group(1))
                    pot = to_call + 0.07
        
        hero_played = hero_action in ['raise', 'call', 'check']
        
        for strat in strategies:
            action, reason = get_strategy_action(strat, hand_str, hole_cards, board, pot, to_call, position)
            strat_played = action in ['raise', 'call', 'bet', 'check']
            
            if strat_played == hero_played:
                strat_results[strat]['agree'] += 1
                strat_results[strat]['profit'] += profit_bb
                if strat_played:
                    strat_results[strat]['played'] += 1
                else:
                    strat_results[strat]['folded'] += 1
            else:
                strat_results[strat]['disagree'] += 1
                if strat_played:
                    # Strategy would play, hero folded - strategy gets 0 (unknown outcome)
                    strat_results[strat]['played'] += 1
                else:
                    # Strategy would fold, hero played - strategy saves/loses the blind
                    strat_results[strat]['folded'] += 1
                    # If hero lost, strategy saved money. If hero won, strategy missed out.
                    if profit_bb < 0:
                        strat_results[strat]['profit'] += abs(profit_bb)  # Saved
                    else:
                        strat_results[strat]['profit'] -= profit_bb  # Missed
    
    print(f"\n{'Strategy':<15} {'Played':>8} {'Folded':>8} {'Agree':>8} {'Disagree':>8} {'Est BB':>10}")
    print("-" * 65)
    for strat in strategies:
        r = strat_results[strat]
        print(f"{strat:<15} {r['played']:>8} {r['folded']:>8} {r['agree']:>8} {r['disagree']:>8} {r['profit']:>+10.1f}")

if __name__ == '__main__':
    main()
