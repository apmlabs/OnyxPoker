#!/usr/bin/env python3
"""
Analyze REAL postflop behavior by archetype from hand histories.
Compare to what our simulated archetypes do.
"""

import os
import re
from collections import defaultdict

HH_DIR = '/home/ubuntu/mcpprojects/onyxpoker/idealistslp_extracted'


def classify_archetype(vpip, pfr, hands):
    """Classify player archetype based on VPIP/PFR."""
    if hands < 20:
        return 'unknown'
    gap = vpip - pfr
    if vpip >= 40 and pfr >= 25:
        return 'maniac'
    if vpip >= 25 and pfr >= 18 and gap <= 12:
        return 'lag'
    if vpip >= 25 and gap >= 10:
        return 'fish'
    if 15 <= vpip <= 28 and pfr >= 12 and gap <= 8:
        return 'tag'
    if vpip <= 15:
        return 'nit'
    if vpip >= 22:
        return 'fish'
    return 'tag'


def parse_all_hands():
    """Parse hand histories and collect player stats + postflop actions."""
    player_preflop = defaultdict(lambda: {'hands': 0, 'vpip': 0, 'pfr': 0})
    player_postflop = defaultdict(lambda: {'check': 0, 'bet': 0, 'call': 0, 'fold': 0, 'raise': 0})
    
    for filename in os.listdir(HH_DIR):
        if not filename.endswith('.txt'):
            continue
        filepath = os.path.join(HH_DIR, filename)
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        for hand_text in re.split(r'\n\n\n+', content):
            if not hand_text.strip():
                continue
            parse_hand(hand_text, player_preflop, player_postflop)
    
    return player_preflop, player_postflop


def parse_hand(text, player_preflop, player_postflop):
    """Parse single hand for preflop stats and postflop actions."""
    lines = text.strip().split('\n')
    
    # Get players
    players = set()
    for line in lines:
        m = re.match(r'Seat \d+: (\S+)', line)
        if m and m.group(1) != 'idealistslp':
            players.add(m.group(1))
    
    # Track preflop
    in_preflop = False
    preflop_raisers = set()
    preflop_callers = set()
    
    # Track postflop
    in_postflop = False
    
    for line in lines:
        if '*** HOLE CARDS ***' in line:
            in_preflop = True
            continue
        if '*** FLOP ***' in line:
            in_preflop = False
            in_postflop = True
            continue
        if '*** SUMMARY ***' in line:
            in_postflop = False
            continue
        
        for player in players:
            if not line.startswith(f'{player}:'):
                continue
            
            if in_preflop:
                if ': raises' in line or ': bets' in line:
                    preflop_raisers.add(player)
                elif ': calls' in line:
                    preflop_callers.add(player)
            
            if in_postflop:
                if ': checks' in line:
                    player_postflop[player]['check'] += 1
                elif ': bets' in line:
                    player_postflop[player]['bet'] += 1
                elif ': calls' in line:
                    player_postflop[player]['call'] += 1
                elif ': folds' in line:
                    player_postflop[player]['fold'] += 1
                elif ': raises' in line:
                    player_postflop[player]['raise'] += 1
    
    # Update preflop stats
    for player in players:
        player_preflop[player]['hands'] += 1
        if player in preflop_raisers or player in preflop_callers:
            player_preflop[player]['vpip'] += 1
        if player in preflop_raisers:
            player_preflop[player]['pfr'] += 1


def simulate_archetype_behavior():
    """Run actual simulation to get archetype behavior stats."""
    import random
    from poker_logic import postflop_action, analyze_hand, RANK_VAL
    
    results = {}
    
    for arch in ['fish', 'nit', 'tag', 'lag']:
        actions = {'check': 0, 'bet': 0, 'call': 0, 'fold': 0, 'raise': 0}
        
        # Simulate 5000 postflop situations
        for _ in range(5000):
            # Random hole cards
            ranks = list('23456789TJQKA')
            suits = list('shdc')
            deck = [r + s for r in ranks for s in suits]
            random.shuffle(deck)
            
            hole = [deck[0], deck[1]]
            board_len = random.choice([3, 4, 5])  # flop/turn/river
            board = deck[2:2+board_len]
            street = ['flop', 'turn', 'river'][board_len - 3]
            
            pot = random.uniform(0.5, 5.0)
            
            # 30% facing bet, 70% first to act (more realistic)
            if random.random() < 0.30:
                to_call = random.uniform(0.2, 2.0)
            else:
                to_call = 0
            
            action, _, _ = postflop_action(hole, board, pot, to_call, street, 
                                           is_ip=random.choice([True, False]),
                                           is_aggressor=random.choice([True, False]),
                                           archetype=arch)
            
            if action in actions:
                actions[action] += 1
        
        total = sum(actions.values())
        af = (actions['bet'] + actions['raise']) / actions['call'] if actions['call'] > 0 else 99
        
        results[arch] = {
            'check': actions['check'] / total * 100,
            'bet': actions['bet'] / total * 100,
            'call': actions['call'] / total * 100,
            'fold': actions['fold'] / total * 100,
            'af': af
        }
    
    return results


def main():
    print("=" * 70)
    print("REAL ARCHETYPE POSTFLOP BEHAVIOR ANALYSIS")
    print("=" * 70)
    
    player_preflop, player_postflop = parse_all_hands()
    
    # Classify players and aggregate postflop by archetype
    archetype_postflop = defaultdict(lambda: {'check': 0, 'bet': 0, 'call': 0, 'fold': 0, 'raise': 0, 'players': 0})
    
    for player, pf in player_preflop.items():
        if pf['hands'] < 20:
            continue
        vpip = pf['vpip'] / pf['hands'] * 100
        pfr = pf['pfr'] / pf['hands'] * 100
        arch = classify_archetype(vpip, pfr, pf['hands'])
        
        if arch == 'unknown':
            continue
        
        archetype_postflop[arch]['players'] += 1
        for action in ['check', 'bet', 'call', 'fold', 'raise']:
            archetype_postflop[arch][action] += player_postflop[player][action]
    
    # Print results
    print(f"\n{'Archetype':<10} {'Players':>8} {'Check%':>8} {'Bet%':>8} {'Call%':>8} {'Fold%':>8} {'Raise%':>8} {'AF':>6}")
    print("-" * 70)
    
    for arch in ['fish', 'nit', 'tag', 'lag', 'maniac']:
        data = archetype_postflop[arch]
        total = data['check'] + data['bet'] + data['call'] + data['fold'] + data['raise']
        if total == 0:
            continue
        
        check_pct = data['check'] / total * 100
        bet_pct = data['bet'] / total * 100
        call_pct = data['call'] / total * 100
        fold_pct = data['fold'] / total * 100
        raise_pct = data['raise'] / total * 100
        
        # AF = (bet + raise) / call
        af = (data['bet'] + data['raise']) / data['call'] if data['call'] > 0 else 99
        
        print(f"{arch:<10} {data['players']:>8} {check_pct:>7.1f}% {bet_pct:>7.1f}% {call_pct:>7.1f}% {fold_pct:>7.1f}% {raise_pct:>7.1f}% {af:>6.2f}")
    
    # Compare to simulation
    print(f"\n{'='*70}")
    print("COMPARISON: REAL vs SIMULATED ARCHETYPE BEHAVIOR")
    print("=" * 70)
    
    # Simulated behavior - run actual simulation to get these
    sim_behavior = simulate_archetype_behavior()
    
    print(f"\n{'Archetype':<10} {'Metric':<10} {'Real':>10} {'Sim':>10} {'Diff':>10}")
    print("-" * 55)
    
    for arch in ['fish', 'nit', 'tag', 'lag']:
        data = archetype_postflop[arch]
        total = data['check'] + data['bet'] + data['call'] + data['fold'] + data['raise']
        if total == 0:
            continue
        
        real_check = data['check'] / total * 100
        real_bet = data['bet'] / total * 100
        real_call = data['call'] / total * 100
        real_fold = data['fold'] / total * 100
        real_af = (data['bet'] + data['raise']) / data['call'] if data['call'] > 0 else 99
        
        sim = sim_behavior.get(arch, {})
        
        print(f"{arch:<10} {'Check%':<10} {real_check:>9.1f}% {sim.get('check', 0):>9.1f}% {real_check - sim.get('check', 0):>+9.1f}%")
        print(f"{'':<10} {'Bet%':<10} {real_bet:>9.1f}% {sim.get('bet', 0):>9.1f}% {real_bet - sim.get('bet', 0):>+9.1f}%")
        print(f"{'':<10} {'Call%':<10} {real_call:>9.1f}% {sim.get('call', 0):>9.1f}% {real_call - sim.get('call', 0):>+9.1f}%")
        print(f"{'':<10} {'Fold%':<10} {real_fold:>9.1f}% {sim.get('fold', 0):>9.1f}% {real_fold - sim.get('fold', 0):>+9.1f}%")
        print(f"{'':<10} {'AF':<10} {real_af:>10.2f} {sim.get('af', 0):>10.2f} {real_af - sim.get('af', 0):>+10.2f}")
        print()


if __name__ == '__main__':
    main()
