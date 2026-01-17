#!/usr/bin/env python3
"""Analyze hero's hole card combinations - BB won/lost per hand."""

import os
import re
from collections import defaultdict

def normalize_hand(c1, c2):
    """Normalize to standard format: AA, AKs, AKo"""
    r1, s1 = c1[0], c1[1]
    r2, s2 = c2[0], c2[1]
    
    rank_order = '23456789TJQKA'
    if rank_order.index(r1) < rank_order.index(r2):
        r1, r2 = r2, r1
        s1, s2 = s2, s1
    
    if r1 == r2:
        return r1 + r2  # Pair: AA, KK
    elif s1 == s2:
        return r1 + r2 + 's'  # Suited: AKs
    else:
        return r1 + r2 + 'o'  # Offsuit: AKo

def parse_hand_histories():
    results = defaultdict(lambda: {'hands': 0, 'bb_won': 0.0})
    
    hh_dir = '../idealistslp_extracted'
    for fname in os.listdir(hh_dir):
        if not fname.startswith('HH') or not fname.endswith('.txt'):
            continue
        
        with open(os.path.join(hh_dir, fname), 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Split into individual hands
        hands = re.split(r'\n(?=PokerStars)', content)
        
        for hand in hands:
            if not hand.strip():
                continue
            
            # Find hero and their cards
            hero_match = re.search(r'Dealt to (\w+) \[(\w\w) (\w\w)\]', hand)
            if not hero_match:
                continue
            
            hero = hero_match.group(1)
            card1, card2 = hero_match.group(2), hero_match.group(3)
            combo = normalize_hand(card1, card2)
            
            # Get BB size (€ or $)
            bb_match = re.search(r'[€$](\d+\.?\d*)/[€$](\d+\.?\d*)', hand)
            if not bb_match:
                continue
            bb = float(bb_match.group(2))
            
            # Parse SUMMARY section for accurate profit
            summary_match = re.search(r'\*\*\* SUMMARY \*\*\*.*', hand, re.DOTALL)
            if not summary_match:
                continue
            summary = summary_match.group(0)
            
            # Find hero's seat result
            # Patterns: "won (€X)", "lost", "folded", "mucked"
            hero_result = re.search(rf'Seat \d+: {hero}[^\n]*', summary)
            if not hero_result:
                continue
            
            result_line = hero_result.group(0)
            
            # Calculate profit
            won = 0.0
            invested = 0.0
            
            # Check if hero won
            won_match = re.search(r'won \([€$](\d+\.?\d*)\)', result_line)
            if won_match:
                won = float(won_match.group(1))
            
            # Calculate invested from actions in hand
            # Posts (blinds/antes)
            for m in re.finditer(rf'{hero}: posts[^\n]*[€$](\d+\.?\d*)', hand):
                invested += float(m.group(1))
            
            # Calls
            for m in re.finditer(rf'{hero}: calls [€$](\d+\.?\d*)', hand):
                invested += float(m.group(1))
            
            # Bets
            for m in re.finditer(rf'{hero}: bets [€$](\d+\.?\d*)', hand):
                invested += float(m.group(1))
            
            # Raises - "raises €X to €Y" means total is Y
            for m in re.finditer(rf'{hero}: raises [€$][\d.]+ to [€$](\d+\.?\d*)', hand):
                # This replaces previous investment on this street
                invested += float(m.group(1))
            
            # Uncalled bet returned
            uncalled = re.search(rf'Uncalled bet \([€$](\d+\.?\d*)\) returned to {hero}', hand)
            if uncalled:
                invested -= float(uncalled.group(1))
            
            profit_bb = (won - invested) / bb
            results[combo]['hands'] += 1
            results[combo]['bb_won'] += profit_bb
    
    return results

def main():
    results = parse_hand_histories()
    
    # Calculate BB/hand and sort
    data = []
    for combo, stats in results.items():
        bb_per_hand = stats['bb_won'] / stats['hands'] if stats['hands'] > 0 else 0
        data.append((combo, stats['hands'], stats['bb_won'], bb_per_hand))
    
    # Sort by total BB won
    data.sort(key=lambda x: x[2], reverse=True)
    
    print(f"{'Hand':<6} {'Count':>6} {'Total BB':>10} {'BB/Hand':>10}")
    print("-" * 36)
    
    total_hands = sum(d[1] for d in data)
    total_bb = sum(d[2] for d in data)
    
    for combo, count, total, per_hand in data:
        print(f"{combo:<6} {count:>6} {total:>+10.1f} {per_hand:>+10.2f}")
    
    print("-" * 36)
    print(f"{'TOTAL':<6} {total_hands:>6} {total_bb:>+10.1f} {total_bb/total_hands if total_hands else 0:>+10.2f}")
    
    # Top winners and losers
    print("\n=== TOP 10 WINNERS (by total BB) ===")
    for combo, count, total, per_hand in data[:10]:
        print(f"{combo}: {total:+.1f} BB ({count} hands, {per_hand:+.2f}/hand)")
    
    print("\n=== TOP 10 LOSERS (by total BB) ===")
    for combo, count, total, per_hand in sorted(data, key=lambda x: x[2])[:10]:
        print(f"{combo}: {total:+.1f} BB ({count} hands, {per_hand:+.2f}/hand)")
    
    # Most played hands
    print("\n=== MOST PLAYED (10+ hands) ===")
    frequent = sorted([d for d in data if d[1] >= 10], key=lambda x: x[1], reverse=True)
    for combo, count, total, per_hand in frequent[:20]:
        print(f"{combo}: {count} hands, {total:+.1f} BB total, {per_hand:+.2f}/hand")

if __name__ == '__main__':
    main()
