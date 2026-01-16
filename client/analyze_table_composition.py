#!/usr/bin/env python3
"""
Analyze real table compositions from PokerStars hand histories.
Calculate player archetypes based on VPIP/PFR and show table compositions.
"""

import os
import re
from collections import defaultdict

HH_DIR = '/home/ubuntu/mcpprojects/onyxpoker/idealistslp_extracted'

# Archetype thresholds based on VPIP/PFR
# From poker_logic.py calibrated values:
# FISH: VPIP 25.5%, PFR 14.6% (loose passive)
# NIT: VPIP 10.7%, PFR 7.5% (tight passive)
# TAG: VPIP 20.2%, PFR 14.7% (tight aggressive)
# LAG: VPIP 28.7%, PFR 23.5% (loose aggressive)
# MANIAC: VPIP 40%+, PFR 30%+ (ultra aggressive)

def classify_archetype(vpip, pfr, hands):
    """Classify player archetype based on VPIP/PFR."""
    if hands < 20:
        return 'unknown'
    
    gap = vpip - pfr  # How often they call vs raise
    
    # Maniac: Very high VPIP and PFR
    if vpip >= 40 and pfr >= 25:
        return 'maniac'
    
    # LAG: High VPIP, high PFR, low gap
    if vpip >= 25 and pfr >= 18 and gap <= 12:
        return 'lag'
    
    # Fish: High VPIP, low PFR, high gap (calls a lot)
    if vpip >= 25 and gap >= 10:
        return 'fish'
    
    # TAG: Medium VPIP, good PFR, low gap
    if 15 <= vpip <= 28 and pfr >= 12 and gap <= 8:
        return 'tag'
    
    # Nit: Low VPIP
    if vpip <= 15:
        return 'nit'
    
    # Default to fish if loose, tag if tight
    if vpip >= 22:
        return 'fish'
    return 'tag'


def parse_hand_histories():
    """Parse all hand histories and collect player stats."""
    player_stats = defaultdict(lambda: {'hands': 0, 'vpip': 0, 'pfr': 0, 'tables': set()})
    table_hands = defaultdict(lambda: defaultdict(list))  # table -> player -> list of hands
    
    for filename in os.listdir(HH_DIR):
        if not filename.endswith('.txt'):
            continue
        
        # Extract table name
        m = re.search(r'(Asterope|Caph|Atria)( #\d+)?', filename)
        table_name = m.group(0) if m else filename
        
        filepath = os.path.join(HH_DIR, filename)
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        # Split into individual hands
        for hand_text in re.split(r'\n\n\n+', content):
            if not hand_text.strip():
                continue
            
            parse_single_hand(hand_text, player_stats, table_hands, table_name)
    
    return player_stats, table_hands


def parse_single_hand(text, player_stats, table_hands, table_name):
    """Parse a single hand and update player stats."""
    lines = text.strip().split('\n')
    
    # Get players at table
    players_in_hand = set()
    for line in lines:
        m = re.match(r'Seat \d+: (\S+)', line)
        if m:
            player = m.group(1)
            if player != 'idealistslp':
                players_in_hand.add(player)
    
    # Track preflop actions
    in_preflop = False
    preflop_raisers = set()
    preflop_callers = set()
    
    for line in lines:
        if '*** HOLE CARDS ***' in line:
            in_preflop = True
            continue
        if '*** FLOP ***' in line or '*** SUMMARY ***' in line:
            in_preflop = False
            continue
        
        if not in_preflop:
            continue
        
        # Check for player actions
        for player in players_in_hand:
            if line.startswith(f'{player}:'):
                if ': raises' in line or ': bets' in line:
                    preflop_raisers.add(player)
                elif ': calls' in line:
                    preflop_callers.add(player)
    
    # Update stats
    for player in players_in_hand:
        player_stats[player]['hands'] += 1
        player_stats[player]['tables'].add(table_name)
        
        if player in preflop_raisers or player in preflop_callers:
            player_stats[player]['vpip'] += 1
        if player in preflop_raisers:
            player_stats[player]['pfr'] += 1
        
        table_hands[table_name][player].append({
            'vpip': player in preflop_raisers or player in preflop_callers,
            'pfr': player in preflop_raisers
        })


def main():
    print("=" * 70)
    print("REAL TABLE COMPOSITION ANALYSIS")
    print("=" * 70)
    
    player_stats, table_hands = parse_hand_histories()
    
    # Calculate VPIP/PFR percentages and archetypes
    players_with_archetype = {}
    for player, stats in player_stats.items():
        if stats['hands'] >= 20:
            vpip_pct = stats['vpip'] / stats['hands'] * 100
            pfr_pct = stats['pfr'] / stats['hands'] * 100
            archetype = classify_archetype(vpip_pct, pfr_pct, stats['hands'])
            players_with_archetype[player] = {
                'hands': stats['hands'],
                'vpip': vpip_pct,
                'pfr': pfr_pct,
                'archetype': archetype,
                'tables': stats['tables']
            }
    
    # Print player stats
    print(f"\n{'='*70}")
    print("PLAYER ARCHETYPES (20+ hands)")
    print(f"{'='*70}")
    print(f"{'Player':<20} {'Hands':>6} {'VPIP%':>7} {'PFR%':>7} {'Gap':>5} {'Archetype':<10}")
    print("-" * 70)
    
    # Sort by hands played
    sorted_players = sorted(players_with_archetype.items(), key=lambda x: -x[1]['hands'])
    
    archetype_counts = defaultdict(int)
    for player, data in sorted_players:
        gap = data['vpip'] - data['pfr']
        print(f"{player:<20} {data['hands']:>6} {data['vpip']:>6.1f}% {data['pfr']:>6.1f}% {gap:>5.1f} {data['archetype']:<10}")
        archetype_counts[data['archetype']] += 1
    
    # Overall archetype distribution
    total = sum(archetype_counts.values())
    print(f"\n{'='*70}")
    print("OVERALL ARCHETYPE DISTRIBUTION (players with 20+ hands)")
    print(f"{'='*70}")
    for arch in ['fish', 'nit', 'tag', 'lag', 'maniac', 'unknown']:
        count = archetype_counts.get(arch, 0)
        pct = count / total * 100 if total > 0 else 0
        bar = '#' * int(pct / 2)
        print(f"{arch:<10}: {count:>3} ({pct:>5.1f}%) {bar}")
    
    # Table compositions
    print(f"\n{'='*70}")
    print("TABLE COMPOSITIONS")
    print(f"{'='*70}")
    
    # Group by unique table (not table instance)
    table_compositions = defaultdict(lambda: defaultdict(int))
    
    for table_name, players in table_hands.items():
        for player in players.keys():
            if player in players_with_archetype:
                arch = players_with_archetype[player]['archetype']
                table_compositions[table_name][arch] += 1
    
    # Print each table's composition
    for table_name in sorted(table_compositions.keys()):
        comp = table_compositions[table_name]
        total_players = sum(comp.values())
        print(f"\n{table_name}:")
        print(f"  Players with known archetype: {total_players}")
        for arch in ['fish', 'nit', 'tag', 'lag', 'maniac']:
            count = comp.get(arch, 0)
            pct = count / total_players * 100 if total_players > 0 else 0
            print(f"    {arch:<8}: {count:>2} ({pct:>5.1f}%)")
    
    # Average table composition
    print(f"\n{'='*70}")
    print("AVERAGE TABLE COMPOSITION (weighted by player count)")
    print(f"{'='*70}")
    
    total_by_arch = defaultdict(int)
    grand_total = 0
    for comp in table_compositions.values():
        for arch, count in comp.items():
            total_by_arch[arch] += count
            grand_total += count
    
    for arch in ['fish', 'nit', 'tag', 'lag', 'maniac']:
        count = total_by_arch.get(arch, 0)
        pct = count / grand_total * 100 if grand_total > 0 else 0
        bar = '#' * int(pct / 2)
        print(f"{arch:<10}: {pct:>5.1f}% {bar}")
    
    # Compare to simulation
    print(f"\n{'='*70}")
    print("COMPARISON: REAL vs SIMULATION")
    print(f"{'='*70}")
    print(f"{'Archetype':<10} {'Real%':>8} {'Sim%':>8} {'Diff':>8}")
    print("-" * 40)
    
    # Current simulation: 60% fish, 25% nit, 15% tag
    sim_comp = {'fish': 60, 'nit': 25, 'tag': 15, 'lag': 0, 'maniac': 0}
    
    for arch in ['fish', 'nit', 'tag', 'lag', 'maniac']:
        real_pct = total_by_arch.get(arch, 0) / grand_total * 100 if grand_total > 0 else 0
        sim_pct = sim_comp.get(arch, 0)
        diff = real_pct - sim_pct
        print(f"{arch:<10} {real_pct:>7.1f}% {sim_pct:>7.1f}% {diff:>+7.1f}%")


if __name__ == '__main__':
    main()
