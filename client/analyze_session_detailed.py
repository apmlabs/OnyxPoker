#!/usr/bin/env python3
"""Analyze session with proper decision-point strategy comparison."""
import re
import sys
sys.path.insert(0, '.')
from poker_logic import preflop_action, postflop_action, STRATEGIES

def hand_to_str(c1, c2):
    rank_order = '23456789TJQKA'
    r1, s1 = c1[0], c1[1]
    r2, s2 = c2[0], c2[1]
    if rank_order.index(r1) < rank_order.index(r2):
        r1, r2 = r2, r1
        s1, s2 = s2, s1
    suited = 's' if s1 == s2 else 'o'
    return f'{r1}{r2}' if r1 == r2 else f'{r1}{r2}{suited}'

def get_position(seat_num, button_seat, seats):
    active = sorted(seats)
    btn_idx = active.index(button_seat)
    my_idx = active.index(seat_num)
    dist = (my_idx - btn_idx) % len(active)
    if len(active) >= 6:
        positions = ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO']
    elif len(active) == 5:
        positions = ['BTN', 'SB', 'BB', 'UTG', 'CO']
    elif len(active) == 4:
        positions = ['BTN', 'SB', 'BB', 'CO']
    else:
        positions = ['BTN', 'SB', 'BB']
    return positions[dist % len(positions)]

def parse_hand_decisions(hand_text, bb=0.05):
    """Parse a hand and extract all hero decision points with context."""
    if 'Dealt to idealistslp' not in hand_text:
        return None
    
    m = re.search(r'Dealt to idealistslp \[(\w\w) (\w\w)\]', hand_text)
    if not m:
        return None
    hole_cards = [m.group(1), m.group(2)]
    hand_str = hand_to_str(hole_cards[0], hole_cards[1])
    
    m = re.search(r"Seat #(\d) is the button", hand_text)
    button_seat = int(m.group(1)) if m else 1
    m = re.search(r"Seat (\d): idealistslp", hand_text)
    hero_seat = int(m.group(1)) if m else 1
    seats = list(set([int(x) for x in re.findall(r"Seat (\d):", hand_text)]))
    position = get_position(hero_seat, button_seat, seats)
    
    # Parse board progressively
    board_flop = []
    board_turn = []
    board_river = []
    
    flop_m = re.search(r'\*\*\* FLOP \*\*\* \[(\w\w) (\w\w) (\w\w)\]', hand_text)
    if flop_m:
        board_flop = [flop_m.group(1), flop_m.group(2), flop_m.group(3)]
    turn_m = re.search(r'\*\*\* TURN \*\*\* \[\w\w \w\w \w\w\] \[(\w\w)\]', hand_text)
    if turn_m:
        board_turn = board_flop + [turn_m.group(1)]
    river_m = re.search(r'\*\*\* RIVER \*\*\* \[\w\w \w\w \w\w \w\w\] \[(\w\w)\]', hand_text)
    if river_m:
        board_river = board_turn + [river_m.group(1)]
    
    # Calculate final profit
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
    
    won = 0.0
    m = re.search(r'idealistslp collected \(?€?([\d.]+)\)?', hand_text)
    if m:
        won = float(m.group(1))
    
    profit = won - invested
    profit_bb = profit / bb
    
    # Extract hero actions
    hero_actions = []
    lines = hand_text.split('\n')
    current_street = 'preflop'
    pot = 0.07
    to_call = 0.0
    
    for line in lines:
        if '*** FLOP ***' in line:
            current_street = 'flop'
        elif '*** TURN ***' in line:
            current_street = 'turn'
        elif '*** RIVER ***' in line:
            current_street = 'river'
        
        # Track raises before hero acts
        if 'raises' in line and 'idealistslp' not in line:
            m = re.search(r'raises €?[\d.]+ to €?([\d.]+)', line)
            if m:
                to_call = float(m.group(1))
        
        if 'idealistslp:' in line:
            action = None
            if 'folds' in line:
                action = 'fold'
            elif 'checks' in line:
                action = 'check'
            elif 'calls' in line:
                action = 'call'
                m = re.search(r'calls €?([\d.]+)', line)
                if m:
                    to_call = float(m.group(1))
            elif 'raises' in line:
                action = 'raise'
            elif 'bets' in line:
                action = 'bet'
            
            if action and action not in ['posts']:
                board = []
                if current_street == 'flop':
                    board = board_flop
                elif current_street == 'turn':
                    board = board_turn
                elif current_street == 'river':
                    board = board_river
                
                hero_actions.append({
                    'street': current_street,
                    'action': action,
                    'board': board,
                    'to_call': to_call
                })
            
            to_call = 0.0  # Reset after hero acts
    
    return {
        'hand': hand_str,
        'hole': hole_cards,
        'position': position,
        'profit_bb': profit_bb,
        'actions': hero_actions,
        'board_final': board_river or board_turn or board_flop
    }

def get_strategy_decision(strat_name, hand_str, hole_cards, board, to_call, street, position, bb=0.05):
    """Get strategy decision at a specific point."""
    strategy = STRATEGIES.get(strat_name)
    if not strategy:
        return 'fold', ''
    
    if not board:  # Preflop
        if to_call <= bb:
            facing = 'none'
        elif to_call <= 4 * bb:
            facing = 'open'
        else:
            facing = '3bet'
        action, reason = preflop_action(hand_str, position, strategy, facing, opener_pos='CO')
        return action, reason
    else:
        action, size, reason = postflop_action(
            hole_cards, board, 1.0, to_call,  # pot=1.0 as placeholder
            street=street, is_ip=True, is_aggressor=True, 
            strategy=strat_name, num_opponents=1
        )
        return action, reason

def analyze_files(files, strategies=['kiro_lord', 'kiro_optimal', 'value_lord']):
    """Analyze multiple files."""
    all_results = []
    
    for hh_file in files:
        with open(hh_file, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        for hand_text in content.split('\n\n\n'):
            result = parse_hand_decisions(hand_text)
            if result:
                all_results.append(result)
    
    # Summary stats
    hero_total = sum(r['profit_bb'] for r in all_results)
    
    print(f"Total hands: {len(all_results)}")
    print(f"Hero result: {hero_total:+.1f} BB")
    print()
    
    # For each strategy, check if it would have made different decisions
    strat_diffs = {s: {'agree': 0, 'disagree_save': 0, 'disagree_miss': 0, 'saved_bb': 0, 'missed_bb': 0} for s in strategies}
    
    disagreements = []
    
    for r in all_results:
        if not r['actions']:
            continue
        
        # Check first significant action (preflop or first postflop)
        first_action = r['actions'][0]
        hero_plays = first_action['action'] in ['call', 'raise', 'bet', 'check']
        
        for strat in strategies:
            strat_action, reason = get_strategy_decision(
                strat, r['hand'], r['hole'], first_action['board'],
                first_action['to_call'], first_action['street'], r['position']
            )
            strat_plays = strat_action in ['call', 'raise', 'bet', 'check']
            
            if strat_plays == hero_plays:
                strat_diffs[strat]['agree'] += 1
            else:
                if not strat_plays and hero_plays:
                    # Strategy folds, hero played
                    if r['profit_bb'] < 0:
                        strat_diffs[strat]['disagree_save'] += 1
                        strat_diffs[strat]['saved_bb'] += abs(r['profit_bb'])
                    else:
                        strat_diffs[strat]['disagree_miss'] += 1
                        strat_diffs[strat]['missed_bb'] += r['profit_bb']
                    
                    if abs(r['profit_bb']) > 5:
                        disagreements.append({
                            'hand': r['hand'],
                            'pos': r['position'],
                            'board': ' '.join(r['board_final']) if r['board_final'] else '--',
                            'profit': r['profit_bb'],
                            'hero': 'PLAY',
                            'strat': strat,
                            'strat_action': strat_action
                        })
    
    print("=" * 70)
    print("STRATEGY COMPARISON")
    print("=" * 70)
    print(f"{'Strategy':<15} {'Agree':>8} {'Save':>8} {'Miss':>8} {'Saved BB':>10} {'Missed BB':>10} {'Net':>10}")
    print("-" * 70)
    
    for strat in strategies:
        d = strat_diffs[strat]
        net = d['saved_bb'] - d['missed_bb']
        print(f"{strat:<15} {d['agree']:>8} {d['disagree_save']:>8} {d['disagree_miss']:>8} {d['saved_bb']:>+10.1f} {d['missed_bb']:>-10.1f} {net:>+10.1f}")
    
    print()
    print("=" * 70)
    print("KEY DISAGREEMENTS (|profit| > 5 BB, strategy would FOLD)")
    print("=" * 70)
    
    for d in sorted(disagreements, key=lambda x: x['profit']):
        print(f"{d['hand']:<7} {d['pos']:<4} {d['board']:<20} {d['profit']:>+7.1f} BB | {d['strat']}: {d['strat_action']}")

if __name__ == '__main__':
    import glob
    
    # Last 4 files from Jan 15-16
    files = sorted(glob.glob('/home/ubuntu/mcpprojects/onyxpoker/idealistslp_extracted/HH202601*.txt'))[-4:]
    print("Analyzing files:")
    for f in files:
        print(f"  {f.split('/')[-1]}")
    print()
    
    analyze_files(files)
