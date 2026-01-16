#!/usr/bin/env python3
"""Analyze real bet sizes by archetype from hand histories."""

import os
import re
from collections import defaultdict

HH_DIR = '/home/ubuntu/mcpprojects/onyxpoker/idealistslp_extracted'


def classify_archetype(vpip, pfr, hands):
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
    return 'fish' if vpip >= 22 else 'tag'


def parse_all_hands():
    player_preflop = defaultdict(lambda: {'hands': 0, 'vpip': 0, 'pfr': 0})
    # bet_sizes[player] = list of (bet_amount, pot_before_bet) tuples
    player_bets = defaultdict(list)
    
    for filename in os.listdir(HH_DIR):
        if not filename.endswith('.txt'):
            continue
        with open(os.path.join(HH_DIR, filename), 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        for hand_text in re.split(r'\n\n\n+', content):
            if hand_text.strip():
                parse_hand(hand_text, player_preflop, player_bets)
    
    return player_preflop, player_bets


def parse_hand(text, player_preflop, player_bets):
    lines = text.strip().split('\n')
    
    # Get players
    players = set()
    for line in lines:
        m = re.match(r'Seat \d+: (\S+)', line)
        if m and m.group(1) != 'idealistslp':
            players.add(m.group(1))
    
    # Track pot per street
    pot = 0
    street_pot = 0  # Pot at start of current street
    in_preflop = False
    in_postflop = False
    preflop_raisers = set()
    preflop_callers = set()
    
    for line in lines:
        # Track blinds (€ or $)
        if ': posts small blind' in line:
            m = re.search(r'posts small blind [€$]?([\d.]+)', line)
            if m:
                pot += float(m.group(1))
        elif ': posts big blind' in line:
            m = re.search(r'posts big blind [€$]?([\d.]+)', line)
            if m:
                pot += float(m.group(1))
        
        if '*** HOLE CARDS ***' in line:
            in_preflop = True
            continue
        if '*** FLOP ***' in line:
            in_preflop = False
            in_postflop = True
            street_pot = pot  # Record pot at start of flop
            continue
        if '*** TURN ***' in line:
            street_pot = pot  # Record pot at start of turn
            continue
        if '*** RIVER ***' in line:
            street_pot = pot  # Record pot at start of river
            continue
        if '*** SUMMARY ***' in line:
            in_postflop = False
            continue
        
        # Track preflop actions for VPIP/PFR
        if in_preflop:
            for player in players:
                if line.startswith(f'{player}:'):
                    if ': raises' in line or ': bets' in line:
                        preflop_raisers.add(player)
                        m = re.search(r'to [€$]?([\d.]+)', line)
                        if m:
                            pot = float(m.group(1)) + pot * 0.5  # Approximate
                    elif ': calls' in line:
                        preflop_callers.add(player)
                        m = re.search(r'calls [€$]?([\d.]+)', line)
                        if m:
                            pot += float(m.group(1))
        
        # Track postflop bets
        if in_postflop:
            for player in players:
                if not line.startswith(f'{player}:'):
                    continue
                
                # Track bets only
                m = re.search(r': bets [€$]?([\d.]+)', line)
                if m:
                    bet = float(m.group(1))
                    if street_pot > 0.01:
                        player_bets[player].append((bet, street_pot))
                    pot += bet
                
                # Track calls/raises for pot
                m = re.search(r': calls [€$]?([\d.]+)', line)
                if m:
                    pot += float(m.group(1))
                m = re.search(r': raises [€$]?[\d.]+ to [€$]?([\d.]+)', line)
                if m:
                    pot += float(m.group(1))
    
    # Update preflop stats
    for player in players:
        player_preflop[player]['hands'] += 1
        if player in preflop_raisers or player in preflop_callers:
            player_preflop[player]['vpip'] += 1
        if player in preflop_raisers:
            player_preflop[player]['pfr'] += 1


def main():
    print("=" * 70)
    print("REAL BET SIZES BY ARCHETYPE")
    print("=" * 70)
    
    player_preflop, player_bets = parse_all_hands()
    
    # Aggregate by archetype
    arch_bets = defaultdict(list)
    
    for player, pf in player_preflop.items():
        if pf['hands'] < 20:
            continue
        vpip = pf['vpip'] / pf['hands'] * 100
        pfr = pf['pfr'] / pf['hands'] * 100
        arch = classify_archetype(vpip, pfr, pf['hands'])
        
        if arch != 'unknown':
            for bet, pot in player_bets[player]:
                if pot > 0:
                    pct = bet / pot * 100
                    arch_bets[arch].append(pct)
    
    # Print results
    print(f"\n{'Archetype':<10} {'Bets':>6} {'Avg%':>8} {'Med%':>8} {'Min%':>8} {'Max%':>8}")
    print("-" * 55)
    
    for arch in ['fish', 'nit', 'tag', 'lag', 'maniac']:
        bets = arch_bets[arch]
        if not bets:
            continue
        bets_sorted = sorted(bets)
        avg = sum(bets) / len(bets)
        med = bets_sorted[len(bets) // 2]
        print(f"{arch:<10} {len(bets):>6} {avg:>7.1f}% {med:>7.1f}% {min(bets):>7.1f}% {max(bets):>7.1f}%")
    
    # Distribution buckets
    print(f"\n{'='*70}")
    print("BET SIZE DISTRIBUTION (% of pot)")
    print("=" * 70)
    
    buckets = [(0, 33), (33, 50), (50, 75), (75, 100), (100, 150), (150, 999)]
    
    print(f"\n{'Archetype':<10}", end="")
    for lo, hi in buckets:
        label = f"{lo}-{hi}%" if hi < 999 else f"{lo}%+"
        print(f" {label:>8}", end="")
    print()
    print("-" * 70)
    
    for arch in ['fish', 'nit', 'tag', 'lag', 'maniac']:
        bets = arch_bets[arch]
        if not bets:
            continue
        print(f"{arch:<10}", end="")
        for lo, hi in buckets:
            count = sum(1 for b in bets if lo <= b < hi)
            pct = count / len(bets) * 100
            print(f" {pct:>7.1f}%", end="")
        print()
    
    # Compare to simulation
    print(f"\n{'='*70}")
    print("SIMULATION BET SIZES (from poker_logic.py)")
    print("=" * 70)
    print("""
Archetype   Sim Bet Sizes
--------------------------
fish        35-50% pot
nit         40-50% pot  
tag         40-55% pot
lag         40-60% pot
maniac      45-75% pot
""")


if __name__ == '__main__':
    main()
