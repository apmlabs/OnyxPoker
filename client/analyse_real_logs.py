#!/usr/bin/env python3
"""
Analyze real PokerStars hand histories from idealistslp_extracted/.
Shows what each strategy would do differently and the € impact.

Usage:
    python analyze_hands.py                    # Full analysis
    python analyze_hands.py --big 10           # Only hands >= 10 BB
    python analyze_hands.py --strategy value_lord  # Single strategy focus
"""

import argparse
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poker_logic import preflop_action, postflop_action, STRATEGIES, analyze_hand

ALL_STRATEGIES = ['value_lord', 'value_maniac', 'kiro_lord', 'kiro_optimal', 'sonnet', 'nit', 'tag', 'lag', 'fish', 'maniac']

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
        'preflop_pot': 0,  # Track pot going to flop
    }
    
    current_street = 'preflop'
    hero_seat = None
    button_seat = None
    seats = {}
    preflop_pot = 0  # Track all preflop contributions
    
    # Track hero's investment per street
    # Key insight: "raises to €X" means hero's TOTAL on this street is X
    # "calls €X" means hero adds X more to their current street investment
    # "bets €X" means hero adds X (first action on street)
    street_invested = {'preflop': 0, 'flop': 0, 'turn': 0, 'river': 0}
    
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
        
        # Track ALL preflop contributions (blinds, calls, raises)
        if current_street == 'preflop':
            if ': posts small blind' in line or ': posts big blind' in line:
                m = re.search(r'€([\d.]+)', line)
                if m:
                    preflop_pot += float(m.group(1))
            elif ': calls' in line:
                m = re.search(r'€([\d.]+)', line)
                if m:
                    preflop_pot += float(m.group(1))
            elif ': raises' in line:
                # "raises €X to €Y" - Y is total put in by this player
                m = re.search(r'to €([\d.]+)', line)
                if m:
                    preflop_pot += float(m.group(1))
        
        # Streets
        if '*** FLOP ***' in line:
            current_street = 'flop'
            # Save preflop pot before moving to flop
            hand['preflop_pot'] = preflop_pot
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
        
        # Uncalled bet returned - subtract from current street
        if 'returned to idealistslp' in line:
            m = re.search(r'€([\d.]+)', line)
            if m:
                street_invested[current_street] -= float(m.group(1))
        
        # Hero actions
        if line.startswith('idealistslp:'):
            action = None
            amt = 0
            
            if ': raises' in line:
                # "raises €X to €Y" - Y is hero's TOTAL on this street (replaces prior)
                m = re.search(r'to €([\d.]+)', line)
                if m:
                    amt = float(m.group(1))
                    street_invested[current_street] = amt  # REPLACE, not add
                action = 'raise'
            elif ': calls' in line:
                # "calls €X" - X is ADDITIONAL amount
                m = re.search(r'€([\d.]+)', line)
                if m:
                    amt = float(m.group(1))
                    street_invested[current_street] += amt
                action = 'call'
            elif ': bets' in line:
                # "bets €X" - X is the amount (first action on street)
                m = re.search(r'€([\d.]+)', line)
                if m:
                    amt = float(m.group(1))
                    street_invested[current_street] += amt
                action = 'bet'
            elif ': posts small blind' in line:
                m = re.search(r'€([\d.]+)', line)
                if m:
                    amt = float(m.group(1))
                    street_invested['preflop'] += amt
            elif ': posts big blind' in line:
                m = re.search(r'€([\d.]+)', line)
                if m:
                    amt = float(m.group(1))
                    street_invested['preflop'] += amt
            elif ': folds' in line:
                action = 'fold'
            elif ': checks' in line:
                action = 'check'
            
            if action and current_street == 'preflop' and hand['hero_preflop_action'] is None:
                hand['hero_preflop_action'] = action
            
            if action and current_street != 'preflop':
                hand['postflop_actions'].append({
                    'street': current_street,
                    'action': action,
                    'amount': amt
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
    
    # Calculate total invested from per-street tracking
    hand['hero_invested'] = sum(street_invested.values())
    
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
    
    # If hero's first action was raise and it's the only/first raise, hero opened
    hero_action = hand.get('hero_preflop_action')
    preflop_actions = hand.get('preflop_actions', [])
    
    # Count raises before hero's action
    # preflop_actions only contains hero's actions, so if hero raised, they opened
    # We need to check if there were villain raises BEFORE hero acted
    # Since we only track hero actions, if hero raised it means they opened or 3bet
    
    # Simple heuristic: if hero raised and amount is small (2-4bb), they opened
    # If hero raised and amount is larger (6bb+), they likely 3bet
    if hero_action == 'raise' and preflop_actions:
        raise_amount = preflop_actions[0].get('amount', 0)
        bb = hand['bb']
        raise_bb = raise_amount / bb if bb > 0 else 0
        
        # Standard open is 2-7bb, 3bet is typically 3x the open (8-15bb)
        if raise_bb <= 7:
            # Hero opened, facing = none
            return 'none', 0
        elif raise_bb <= 18:
            # Hero 3bet, was facing open
            facing = 'open'
            to_call = 0  # Hero already acted
        else:
            # Hero 4bet, was facing 3bet
            facing = '3bet'
            to_call = 0
    elif hero_action == 'call':
        # Hero called, so was facing something
        # Use the LAST raise amount (what hero actually called)
        if preflop_actions:
            call_amount = preflop_actions[-1].get('amount', 0)
            bb = hand['bb']
            call_bb = call_amount / bb if bb > 0 else 0
            
            if call_bb <= 4:
                facing = 'open'
            elif call_bb <= 15:
                facing = '3bet'
            else:
                facing = '4bet'
            to_call = call_amount
    
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
        # Start with preflop pot
        pot = hand.get('preflop_pot', 0)
        to_call = 0
        hero_action_on_street = None
        hero_already_acted = False  # Track if hero bet/raised/checked before villain's action
        is_facing_raise = False
        
        # Calculate pot and find hero's decision
        for action in hand['postflop_actions']:
            if action['street'] != street:
                if action['street'] in ['flop', 'turn', 'river']:
                    # Previous street - add all actions to pot
                    if action['action'] in ['call', 'bet', 'raise', 'villain_bet', 'villain_raise']:
                        pot += action.get('amount', 0)
                continue
            
            # Current street - add hero's bet to pot before villain's action
            if action['action'] in ['bet', 'raise']:
                pot += action.get('amount', 0)
                hero_already_acted = True
            elif action['action'] == 'check':
                hero_already_acted = True
            
            if action['action'] in ['villain_bet', 'villain_raise']:
                to_call = action['amount']
                pot += action['amount']
                # If hero already acted and now faces a bet, it's a check-raise
                if hero_already_acted:
                    is_facing_raise = True
            elif action['action'] in ['fold', 'call']:
                # Hero's response to villain's bet
                hero_action_on_street = action['action']
                break
        
        if to_call > 0 and hero_action_on_street:
            situations.append({
                'street': street,
                'board': board,
                'pot': pot,
                'to_call': to_call,
                'is_aggressor': is_aggressor,
                'hero_action': hero_action_on_street,
                'is_facing_raise': is_facing_raise
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
            strategy=strategy_name,
            is_facing_raise=situation.get('is_facing_raise', False)
        )
        return action, reason
    except:
        return None, None

def main(min_bb=None, focus_strategy=None):
    hh_dir = '/home/ubuntu/mcpprojects/onyxpoker/idealistslp_extracted'
    all_hands = parse_all_hands(hh_dir)
    
    # Filter by BB threshold if specified
    if min_bb:
        all_hands = [h for h in all_hands if abs(h['profit_bb']) >= min_bb]
        print(f"Filtered to {len(all_hands)} hands with >= {min_bb} BB swing")
        print()
    
    strategies = [focus_strategy] if focus_strategy else ALL_STRATEGIES
    
    print("=" * 100)
    print("STRATEGY ANALYSIS ON REAL POKERSTARS HANDS")
    print("=" * 100)
    print()
    
    # Basic stats
    print(f"Total hands: {len(all_hands)}")
    
    total_profit = sum(h['hero_profit'] for h in all_hands)
    total_bb = sum(h['profit_bb'] for h in all_hands)
    
    if all_hands:
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
    
    print(f"Hands played: {len(played)} ({len(played)/len(all_hands)*100:.1f}%)" if all_hands else "")
    print(f"Hands folded preflop: {len(folded)} ({len(folded)/len(all_hands)*100:.1f}%)" if all_hands else "")
    print()
    
    # Evaluate strategies
    results = {}
    for strategy in strategies:
        results[strategy] = {
            'pf_would_fold': [],  # Hands where strategy would fold but hero played
            'pf_would_play': [],  # Hands where strategy would play but hero folded
            'post_would_fold': [],  # Postflop spots where strategy would fold
            'unsaved_losses': [],  # Losing hands where strategy still plays
        }
    
    for hand in all_hands:
        if not hand['hero_position'] or not hand['hand_str']:
            continue
        
        for strategy in strategies:
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
            for strategy in strategies:
                # Skip if strategy would fold preflop (already counted above)
                strat_pf_action, _ = evaluate_preflop(hand, strategy)
                if strat_pf_action == 'fold':
                    continue
                
                # Only count FIRST postflop fold (if fold flop, won't see turn)
                found_fold = False
                for sit in situations:
                    strat_action, reason = evaluate_postflop(hand, sit, strategy)
                    if strat_action == 'fold' and sit['hero_action'] != 'fold':
                        results[strategy]['post_would_fold'].append({
                            'hand': hand,
                            'situation': sit,
                            'reason': reason
                        })
                        found_fold = True
                        break  # Only count first fold per hand
                
                # Track unsaved losses: strategy plays through but loses
                if not found_fold and hand['profit_bb'] < -10:  # Only significant losses
                    results[strategy]['unsaved_losses'].append(hand)
    
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
    for strategy in strategies:
        r = results[strategy]
        
        # Preflop: hands strategy would fold that hero played
        pf_saved = sum(abs(h['hero_profit']) for h in r['pf_would_fold'] if h['hero_profit'] < 0)
        pf_missed = sum(h['hero_profit'] for h in r['pf_would_fold'] if h['hero_profit'] > 0)
        
        # Postflop: spots strategy would fold
        # For saves: use hand profit (what we actually lost)
        # For misses: use hand profit (what we actually won)
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
        pot_pct = s['to_call'] / s['pot'] if s['pot'] > 0 else 0
        reason = p.get('reason', '')
        print(f"    {h['hand_str']:<6} on {board:<18} {s['street']:<5} {pot_pct:>3.0%} pot -> saved {abs(h['profit_bb']):.1f} BB")
        print(f"           Reason: {reason}")
    
    post_misses.sort(key=lambda x: -x['hand']['profit_bb'])
    print(f"\n  BIGGEST POSTFLOP MISSES:")
    for p in post_misses[:10]:
        h = p['hand']
        s = p['situation']
        board = ' '.join(s['board'])
        pot_pct = s['to_call'] / s['pot'] if s['pot'] > 0 else 0
        reason = p.get('reason', '')
        print(f"    {h['hand_str']:<6} on {board:<18} {s['street']:<5} {pot_pct:>3.0%} pot -> missed {h['profit_bb']:.1f} BB")
        print(f"           Reason: {reason}")
    
    # Unsaved losses section
    unsaved = results[strategies[0]]['unsaved_losses']
    if unsaved:
        unsaved_bb = sum(abs(h['profit_bb']) for h in unsaved)
        print()
        print("=" * 130)
        print(f"UNSAVED LOSSES (strategy plays through, still loses): {len(unsaved)} hands, {unsaved_bb:.1f} BB")
        print("=" * 130)
        unsaved.sort(key=lambda x: x['profit_bb'])
        for h in unsaved[:10]:
            board_str = ' '.join(h['board']) if h['board'] else '-'
            hand_info = analyze_hand(h['hero_cards'], h['board']) if h['board'] else {'desc': 'preflop'}
            print(f"    {h['hand_str']:<6} {h['hero_position']:<4} {abs(h['profit_bb']):>6.1f} BB - {hand_info['desc']:<30} {board_str}")
    
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
        for strategy in strategies:
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

def test_range_changes(min_bb=10):
    """Test impact of proposed range changes."""
    from poker_logic import STRATEGIES, expand_range
    
    hh_dir = '/home/ubuntu/mcpprojects/onyxpoker/idealistslp_extracted'
    all_hands = parse_all_hands(hh_dir)
    big_hands = [h for h in all_hands if abs(h['profit_bb']) >= min_bb]
    
    # Current value_lord ranges
    current_call_open_ip = STRATEGIES['value_lord']['call_open_ip']
    current_call_3bet = STRATEGIES['value_lord']['call_3bet']
    
    # Proposed changes
    proposed_call_open_ip = current_call_open_ip | {'97s', '76s'}
    proposed_call_3bet = current_call_3bet | {'ATs'}
    
    print("=" * 80)
    print("TESTING PROPOSED RANGE CHANGES")
    print("=" * 80)
    print()
    print("Proposed changes:")
    print("  1. Add 97s, 76s to call_open_ip")
    print("  2. Add ATs to call_3bet")
    print()
    
    # Find hands affected by each change
    affected_97s = []
    affected_76s = []
    affected_ATs_3bet = []
    
    for h in big_hands:
        if not h['hand_str'] or not h['hero_position']:
            continue
        
        facing, to_call = get_preflop_facing(h)
        
        # 97s/76s: would now call opens IP
        if h['hand_str'] in ['97s', '76s'] and facing == 'open':
            # Check if IP (CO, BTN)
            if h['hero_position'] in ['CO', 'BTN']:
                if h['hand_str'] == '97s':
                    affected_97s.append(h)
                else:
                    affected_76s.append(h)
        
        # ATs: would now call 3bets
        if h['hand_str'] == 'ATs' and facing == '3bet':
            affected_ATs_3bet.append(h)
        
        # Also check if hero opened and then faced 3bet (parser bug workaround)
        if h['hand_str'] == 'ATs' and h['hero_preflop_action'] == 'raise':
            # Check if there was a 3bet after hero's open
            for action in h['preflop_actions']:
                if action['action'] == 'raise' and action['amount'] > to_call:
                    affected_ATs_3bet.append(h)
                    break
    
    print("IMPACT OF ADDING 97s TO call_open_ip (IP only):")
    print("-" * 60)
    total_97s = sum(h['profit_bb'] for h in affected_97s)
    for h in affected_97s:
        print(f"  {h['hand_str']:<6} {h['hero_position']:<4} {h['profit_bb']:>+7.1f} BB")
    print(f"  TOTAL: {total_97s:>+7.1f} BB ({len(affected_97s)} hands)")
    print()
    
    print("IMPACT OF ADDING 76s TO call_open_ip (IP only):")
    print("-" * 60)
    total_76s = sum(h['profit_bb'] for h in affected_76s)
    for h in affected_76s:
        print(f"  {h['hand_str']:<6} {h['hero_position']:<4} {h['profit_bb']:>+7.1f} BB")
    print(f"  TOTAL: {total_76s:>+7.1f} BB ({len(affected_76s)} hands)")
    print()
    
    print("IMPACT OF ADDING ATs TO call_3bet:")
    print("-" * 60)
    total_ATs = sum(h['profit_bb'] for h in affected_ATs_3bet)
    for h in affected_ATs_3bet:
        print(f"  {h['hand_str']:<6} {h['hero_position']:<4} {h['profit_bb']:>+7.1f} BB  board: {' '.join(h['board']) if h['board'] else '-'}")
    print(f"  TOTAL: {total_ATs:>+7.1f} BB ({len(affected_ATs_3bet)} hands)")
    print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  97s IP: {total_97s:>+7.1f} BB")
    print(f"  76s IP: {total_76s:>+7.1f} BB")
    print(f"  ATs 3bet: {total_ATs:>+7.1f} BB")
    print(f"  TOTAL IMPACT: {total_97s + total_76s + total_ATs:>+7.1f} BB")

def detailed_analysis(min_bb=10, strategy_name='value_lord'):
    """Hand-by-hand analysis showing exactly where strategy would fold."""
    hh_dir = '/home/ubuntu/mcpprojects/onyxpoker/idealistslp_extracted'
    all_hands = parse_all_hands(hh_dir)
    
    # Filter to big hands
    big_hands = [h for h in all_hands if abs(h['profit_bb']) >= min_bb]
    
    # Separate winners and losers
    winners = sorted([h for h in big_hands if h['profit_bb'] > 0], key=lambda x: -x['profit_bb'])
    losers = sorted([h for h in big_hands if h['profit_bb'] < 0], key=lambda x: x['profit_bb'])
    
    print("=" * 120)
    print(f"DETAILED HAND-BY-HAND ANALYSIS: {strategy_name} on hands >= {min_bb} BB")
    print("=" * 120)
    
    total_won = sum(h['hero_profit'] for h in winners)
    total_lost = sum(abs(h['hero_profit']) for h in losers)
    
    print(f"\nSUMMARY:")
    print(f"  Winners: {len(winners)} hands, €{total_won:.2f} ({sum(h['profit_bb'] for h in winners):.1f} BB)")
    print(f"  Losers:  {len(losers)} hands, €{total_lost:.2f} ({sum(abs(h['profit_bb']) for h in losers):.1f} BB)")
    print(f"  Net:     €{total_won - total_lost:.2f}")
    
    # Analyze each hand
    strategy_saves = []  # Losers where strategy folds
    strategy_misses = []  # Winners where strategy folds
    
    def analyze_single_hand(hand):
        """Returns (fold_point, reason) or (None, None) if strategy plays through."""
        # Check preflop
        pf_action, pf_reason = evaluate_preflop(hand, strategy_name)
        if pf_action == 'fold':
            return ('preflop', pf_reason)
        
        # Check postflop
        if hand['hero_preflop_action'] and hand['hero_preflop_action'] != 'fold':
            situations = get_postflop_situations(hand)
            for sit in situations:
                action, reason = evaluate_postflop(hand, sit, strategy_name)
                if action == 'fold':
                    return (sit['street'], reason)
        
        return (None, None)
    
    def get_play_analysis(hand):
        """For hands strategy plays, return analysis of hand strength and villain action."""
        from poker_logic import analyze_hand
        
        if not hand['board']:
            return "preflop all-in", 0
        
        # Parse hero cards
        hole = []
        for c in hand['hero_cards']:
            rank, suit = c[0], c[1].lower()
            hole.append((rank, suit))
        
        # Parse board
        board = []
        for c in hand['board']:
            rank, suit = c[0], c[1].lower()
            board.append((rank, suit))
        
        info = analyze_hand(hole, board)
        
        # Check for villain raises in postflop
        villain_raised = False
        raise_street = None
        for act in hand.get('postflop_actions', []):
            if act['action'] == 'villain_raise':
                villain_raised = True
                raise_street = act['street']
        
        result = f"{info['desc']}"
        if villain_raised:
            result += f" [VILLAIN RAISED on {raise_street}]"
        
        # Calculate postflop savings
        postflop_savings_bb = calculate_postflop_savings(hand, strategy_name)
        
        return result, postflop_savings_bb
    
    def calculate_postflop_savings(hand, strategy_name):
        """Calculate how much strategy would save by checking instead of betting."""
        from poker_logic import postflop_action, analyze_hand
        
        if not hand['board']:
            return 0
        
        # Parse hero cards
        hole = []
        for c in hand['hero_cards']:
            rank, suit = c[0], c[1].lower()
            hole.append((rank, suit))
        
        bb = hand['bb']
        savings = 0
        
        # Get hero's actual bets per street from postflop_actions (all are hero actions)
        hero_bets = {'flop': 0, 'turn': 0, 'river': 0}
        for act in hand.get('postflop_actions', []):
            if act['action'] in ['bet', 'raise']:
                hero_bets[act['street']] += act.get('amount', 0)
        
        # Simulate strategy on each street
        streets = ['flop', 'turn', 'river']
        board_cards = hand['board']
        
        for i, street in enumerate(streets):
            if i == 0:
                board = board_cards[:3] if len(board_cards) >= 3 else []
            elif i == 1:
                board = board_cards[:4] if len(board_cards) >= 4 else []
            else:
                board = board_cards[:5] if len(board_cards) >= 5 else []
            
            if not board:
                continue
            
            # Parse board for strategy
            parsed_board = []
            for c in board:
                rank, suit = c[0], c[1].lower()
                parsed_board.append((rank, suit))
            
            # What would strategy do? (assume no bet to call, we're checking if strategy would bet)
            try:
                action, size, reason = postflop_action(
                    hole, parsed_board, 1.0, 0, street, True,
                    strategy=strategy_name, is_aggressor=True
                )
                
                # If strategy checks/folds but hero bet, that's savings
                if action in ['check', 'fold'] and hero_bets[street] > 0:
                    savings += hero_bets[street] / bb
                    # If fold, also save all future street bets
                    if action == 'fold':
                        for future_street in streets[i+1:]:
                            savings += hero_bets[future_street] / bb
                        break  # No more streets after fold
            except:
                pass
        
        return savings
    
    print("\n" + "=" * 120)
    print("LOSING HANDS (where strategy could SAVE money by folding)")
    print("=" * 120)
    print(f"\n{'Hand':<6} {'Pos':<4} {'Board':<20} {'Lost BB':>8} {'Strategy':>10} {'Fold Point':<10} Reason")
    print("-" * 120)
    
    strategy_plays = []  # Losers where strategy plays through
    
    for h in losers:
        fold_point, reason = analyze_single_hand(h)
        board_str = ' '.join(h['board']) if h['board'] else '-'
        
        if fold_point:
            strategy_saves.append({'hand': h, 'fold_point': fold_point, 'reason': reason})
            status = "SAVES"
            detail = reason
        else:
            play_analysis, postflop_savings = get_play_analysis(h)
            strategy_plays.append({'hand': h, 'analysis': play_analysis, 'postflop_savings': postflop_savings})
            status = "plays"
            detail = play_analysis
        
        print(f"{h['hand_str']:<6} {h['hero_position']:<4} {board_str:<20} {abs(h['profit_bb']):>8.1f} {status:>10} {fold_point or '-':<10} {detail}")
    
    print("\n" + "=" * 120)
    print("WINNING HANDS (where strategy would MISS profit by folding)")
    print("=" * 120)
    print(f"\n{'Hand':<6} {'Pos':<4} {'Board':<20} {'Won BB':>8} {'Strategy':>10} {'Fold Point':<10} Reason")
    print("-" * 120)
    
    for h in winners:
        fold_point, reason = analyze_single_hand(h)
        board_str = ' '.join(h['board']) if h['board'] else '-'
        
        if fold_point:
            strategy_misses.append({'hand': h, 'fold_point': fold_point, 'reason': reason})
            status = "MISSES"
        else:
            status = "plays"
        
        print(f"{h['hand_str']:<6} {h['hero_position']:<4} {board_str:<20} {h['profit_bb']:>8.1f} {status:>10} {fold_point or '-':<10} {reason or '-'}")
    
    # Summary
    saved_bb = sum(abs(s['hand']['profit_bb']) for s in strategy_saves)
    missed_bb = sum(m['hand']['profit_bb'] for m in strategy_misses)
    
    print("\n" + "=" * 120)
    print("STRATEGY IMPACT SUMMARY")
    print("=" * 120)
    print(f"\nSAVES (folds losing hands):")
    print(f"  {len(strategy_saves)} hands, {saved_bb:.1f} BB saved")
    for s in sorted(strategy_saves, key=lambda x: x['hand']['profit_bb']):
        h = s['hand']
        print(f"    {h['hand_str']:<6} {h['hero_position']:<4} {abs(h['profit_bb']):>6.1f} BB - {s['fold_point']}: {s['reason']}")
    
    print(f"\nMISSES (folds winning hands):")
    print(f"  {len(strategy_misses)} hands, {missed_bb:.1f} BB missed")
    for m in sorted(strategy_misses, key=lambda x: -x['hand']['profit_bb']):
        h = m['hand']
        print(f"    {h['hand_str']:<6} {h['hero_position']:<4} {h['profit_bb']:>6.1f} BB - {m['fold_point']}: {m['reason']}")
    
    print(f"\nNET IMPACT: {saved_bb:.1f} - {missed_bb:.1f} = {saved_bb - missed_bb:+.1f} BB")
    
    # Analyze unsaved losses
    if strategy_plays:
        plays_bb = sum(abs(p['hand']['profit_bb']) for p in strategy_plays)
        postflop_savings_bb = sum(p.get('postflop_savings', 0) for p in strategy_plays)
        net_loss_bb = plays_bb - postflop_savings_bb
        
        print(f"\n" + "=" * 120)
        print(f"UNSAVED LOSSES (strategy plays, still loses): {len(strategy_plays)} hands")
        print(f"  Total lost: {plays_bb:.1f} BB | Postflop savings: {postflop_savings_bb:.1f} BB | Net loss: {net_loss_bb:.1f} BB")
        print("=" * 120)
        
        # Categorize by villain raise
        raised_hands = [p for p in strategy_plays if 'VILLAIN RAISED' in p['analysis']]
        other_hands = [p for p in strategy_plays if 'VILLAIN RAISED' not in p['analysis']]
        
        if raised_hands:
            raised_bb = sum(abs(p['hand']['profit_bb']) for p in raised_hands)
            raised_savings = sum(p.get('postflop_savings', 0) for p in raised_hands)
            print(f"\n  VILLAIN RAISED (check-raise detection would help): {len(raised_hands)} hands, {raised_bb:.1f} BB lost, {raised_savings:.1f} BB saved")
            for p in sorted(raised_hands, key=lambda x: x['hand']['profit_bb']):
                h = p['hand']
                savings = p.get('postflop_savings', 0)
                savings_str = f" [saves {savings:.1f} BB]" if savings > 0 else ""
                print(f"    {h['hand_str']:<6} {h['hero_position']:<4} {abs(h['profit_bb']):>6.1f} BB - {p['analysis']}{savings_str}")
        
        if other_hands:
            other_bb = sum(abs(p['hand']['profit_bb']) for p in other_hands)
            other_savings = sum(p.get('postflop_savings', 0) for p in other_hands)
            print(f"\n  OTHER LOSSES (coolers/unavoidable): {len(other_hands)} hands, {other_bb:.1f} BB lost, {other_savings:.1f} BB saved")
            for p in sorted(other_hands, key=lambda x: x['hand']['profit_bb']):
                h = p['hand']
                savings = p.get('postflop_savings', 0)
                savings_str = f" [saves {savings:.1f} BB]" if savings > 0 else ""
                print(f"    {h['hand_str']:<6} {h['hero_position']:<4} {abs(h['profit_bb']):>6.1f} BB - {p['analysis']}{savings_str}")
    
    return strategy_saves, strategy_misses

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze hand histories with strategies')
    parser.add_argument('--big', type=float, help='Only analyze hands >= N BB')
    parser.add_argument('--strategy', type=str, help='Focus on single strategy')
    parser.add_argument('--detailed', action='store_true', help='Hand-by-hand detailed analysis')
    parser.add_argument('--test-ranges', action='store_true', help='Test proposed range changes')
    args = parser.parse_args()
    
    if args.test_ranges:
        test_range_changes(min_bb=args.big or 10)
    elif args.detailed:
        detailed_analysis(min_bb=args.big or 10, strategy_name=args.strategy or 'value_lord')
    else:
        main(min_bb=args.big, focus_strategy=args.strategy)
