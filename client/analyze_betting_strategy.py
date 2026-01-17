#!/usr/bin/env python3
"""
Analyze betting patterns from real hand histories.
Shows win rates by hand strength, bet size, street, and aggressor status.
"""

import os
import re
from collections import defaultdict

HH_DIR = '../idealistslp_extracted'
HERO = 'idealistslp'
BB = 0.05  # €0.05 big blind

def parse_hands():
    """Parse all hand histories."""
    all_hands = []
    
    for fname in os.listdir(HH_DIR):
        if not fname.endswith('.txt'):
            continue
        
        with open(os.path.join(HH_DIR, fname), 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        for hand_text in re.split(r'\n\n\n+', content):
            if 'Zoom Hand' not in hand_text or HERO not in hand_text:
                continue
            
            parsed = parse_single_hand(hand_text)
            if parsed and parsed['hero_cards']:
                all_hands.append(parsed)
    
    return all_hands

def parse_single_hand(text):
    """Parse a single hand for betting analysis."""
    lines = text.strip().split('\n')
    
    hero_cards = None
    board = []
    current_street = 'preflop'
    was_preflop_aggressor = False
    
    # Track pot at start of each street
    pot = 0
    pot_at_street = {'flop': 0, 'turn': 0, 'river': 0}
    
    # Hero bets with context
    hero_bets = []
    hero_won = 0
    
    for line in lines:
        # Hero cards
        if f'Dealt to {HERO}' in line:
            m = re.search(r'\[(\w\w) (\w\w)\]', line)
            if m:
                hero_cards = [m.group(1), m.group(2)]
        
        # Preflop aggression
        if current_street == 'preflop' and HERO in line and ': raises' in line:
            was_preflop_aggressor = True
        
        # Track pot
        if current_street == 'preflop':
            for pattern in [r': posts small blind €([\d.]+)', r': posts big blind €([\d.]+)',
                           r': calls €([\d.]+)']:
                m = re.search(pattern, line)
                if m:
                    pot += float(m.group(1))
            if ': raises' in line:
                m = re.search(r'to €([\d.]+)', line)
                if m:
                    pot = float(m.group(1)) * 2  # Rough estimate
        
        # Street transitions
        if '*** FLOP ***' in line:
            pot_at_street['flop'] = pot
            current_street = 'flop'
            m = re.search(r'\[(\w\w) (\w\w) (\w\w)\]', line)
            if m:
                board = [m.group(1), m.group(2), m.group(3)]
        elif '*** TURN ***' in line:
            pot_at_street['turn'] = pot
            current_street = 'turn'
            m = re.search(r'\] \[(\w\w)\]', line)
            if m:
                board.append(m.group(1))
        elif '*** RIVER ***' in line:
            pot_at_street['river'] = pot
            current_street = 'river'
            m = re.search(r'\] \[(\w\w)\]', line)
            if m:
                board.append(m.group(1))
        
        # Track pot growth
        if current_street in ['flop', 'turn', 'river']:
            for pattern in [r': bets €([\d.]+)', r': calls €([\d.]+)']:
                m = re.search(pattern, line)
                if m:
                    pot += float(m.group(1))
            if ': raises' in line:
                m = re.search(r'to €([\d.]+)', line)
                if m:
                    pot += float(m.group(1))
        
        # Hero bets
        if HERO in line and current_street in ['flop', 'turn', 'river']:
            if ': bets' in line:
                m = re.search(r'bets €([\d.]+)', line)
                if m:
                    bet_amt = float(m.group(1))
                    hero_bets.append({
                        'street': current_street,
                        'bet': bet_amt,
                        'pot_before': pot_at_street[current_street],
                        'board': board.copy()
                    })
    
    # Check if hero won
    for line in lines:
        if HERO in line and 'collected' in line:
            m = re.search(r'collected €([\d.]+)', line)
            if m:
                hero_won = float(m.group(1))
    
    return {
        'hero_cards': hero_cards,
        'board': board,
        'hero_bets': hero_bets,
        'hero_won': hero_won,
        'was_aggressor': was_preflop_aggressor
    }

def get_hand_strength(hero_cards, board):
    """Detailed hand strength classification."""
    if not hero_cards or not board:
        return 'unknown'
    
    ranks = '23456789TJQKA'
    suits = 'cdhs'
    
    hero_ranks = [c[0] for c in hero_cards]
    hero_suits = [c[1] for c in hero_cards]
    board_ranks = [c[0] for c in board]
    board_suits = [c[1] for c in board]
    
    all_ranks = hero_ranks + board_ranks
    all_suits = hero_suits + board_suits
    
    # Count rank occurrences
    rank_counts = defaultdict(int)
    for r in all_ranks:
        rank_counts[r] += 1
    
    board_rank_counts = defaultdict(int)
    for r in board_ranks:
        board_rank_counts[r] += 1
    
    # Check for flush
    suit_counts = defaultdict(int)
    for s in all_suits:
        suit_counts[s] += 1
    has_flush = any(c >= 5 for c in suit_counts.values())
    
    # Check for straight
    rank_values = sorted(set(ranks.index(r) for r in all_ranks))
    has_straight = False
    for i in range(len(rank_values) - 4):
        if rank_values[i+4] - rank_values[i] == 4:
            has_straight = True
    # Wheel
    if set([0,1,2,3,12]).issubset(set(ranks.index(r) for r in all_ranks)):
        has_straight = True
    
    # Quads
    if 4 in rank_counts.values():
        return 'quads'
    
    # Full house
    if 3 in rank_counts.values() and 2 in rank_counts.values():
        return 'full_house'
    
    # Flush
    if has_flush:
        return 'flush'
    
    # Straight
    if has_straight:
        return 'straight'
    
    # Trips/Set
    if 3 in rank_counts.values():
        trip_rank = [r for r, c in rank_counts.items() if c == 3][0]
        if trip_rank in hero_ranks and board_rank_counts[trip_rank] == 2:
            return 'set'
        elif trip_rank in hero_ranks:
            return 'trips'
        else:
            return 'board_trips'
    
    # Two pair
    pairs = [r for r, c in rank_counts.items() if c == 2]
    if len(pairs) >= 2:
        hero_pairs = [r for r in pairs if r in hero_ranks]
        if len(hero_pairs) == 2:
            return 'two_pair_both'
        elif len(hero_pairs) == 1:
            # Check if pocket pair + board pair
            if hero_ranks[0] == hero_ranks[1]:
                pp_rank = ranks.index(hero_ranks[0])
                board_pair_rank = max(ranks.index(r) for r in pairs if r != hero_ranks[0])
                if pp_rank > board_pair_rank:
                    return 'two_pair_pp_over'
                else:
                    return 'two_pair_pp_under'
            return 'two_pair_one'
        return 'two_pair_board'
    
    # One pair
    if len(pairs) == 1:
        pair_rank = pairs[0]
        board_rank_values = [ranks.index(r) for r in board_ranks]
        max_board = max(board_rank_values)
        second_board = sorted(board_rank_values, reverse=True)[1] if len(board_rank_values) > 1 else -1
        
        # Pocket pair
        if hero_ranks[0] == hero_ranks[1]:
            pp_value = ranks.index(hero_ranks[0])
            if pp_value > max_board:
                return 'overpair'
            elif pp_value == max_board:
                return 'top_set'  # Actually top pair with pocket
            else:
                return 'underpair'
        
        # Board pair (hero doesn't have it)
        if pair_rank not in hero_ranks:
            return 'high_card_bp'  # High card on paired board
        
        # Hero has the pair
        pair_value = ranks.index(pair_rank)
        kicker = [r for r in hero_ranks if r != pair_rank][0]
        kicker_value = ranks.index(kicker)
        
        if pair_value == max_board:
            if kicker_value >= 10:  # T or higher
                return 'tpgk'  # Top pair good kicker
            else:
                return 'tpwk'  # Top pair weak kicker
        elif pair_value == second_board:
            return 'middle_pair'
        else:
            return 'bottom_pair'
    
    # High card
    return 'high_card'

def analyze_bets(hands):
    """Analyze all bets by street, strength, size, and aggressor status."""
    
    # Structure: street -> strength -> size_bucket -> aggressor -> [won, lost]
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {'agg': [], 'nonagg': []})))
    
    size_buckets = ['0-2BB', '2-4BB', '4-6BB', '6-10BB', '10-20BB', '20+BB']
    
    def get_bucket(bb_amt):
        if bb_amt <= 2:
            return '0-2BB'
        elif bb_amt <= 4:
            return '2-4BB'
        elif bb_amt <= 6:
            return '4-6BB'
        elif bb_amt <= 10:
            return '6-10BB'
        elif bb_amt <= 20:
            return '10-20BB'
        else:
            return '20+BB'
    
    for h in hands:
        won = h['hero_won'] > 0
        agg_key = 'agg' if h['was_aggressor'] else 'nonagg'
        
        for bet in h['hero_bets']:
            street = bet['street']
            board_len = 3 if street == 'flop' else 4 if street == 'turn' else 5
            board = bet['board'][:board_len]
            
            strength = get_hand_strength(h['hero_cards'], board)
            bb_amt = bet['bet'] / BB
            bucket = get_bucket(bb_amt)
            pot_pct = (bet['bet'] / bet['pot_before'] * 100) if bet['pot_before'] > 0 else 0
            
            data[street][strength][bucket][agg_key].append({
                'won': won,
                'bb': bb_amt,
                'pot_pct': pot_pct
            })
    
    return data, size_buckets

def print_analysis(data, size_buckets):
    """Print formatted analysis."""
    
    strength_order = [
        'high_card', 'high_card_bp',
        'bottom_pair', 'middle_pair', 'tpwk', 'tpgk',
        'underpair', 'overpair',
        'two_pair_board', 'two_pair_one', 'two_pair_pp_under', 'two_pair_pp_over', 'two_pair_both',
        'board_trips', 'trips', 'set',
        'straight', 'flush', 'full_house', 'quads'
    ]
    
    for street in ['flop', 'turn', 'river']:
        print(f"\n{'='*100}")
        print(f"  {street.upper()} BETS")
        print(f"{'='*100}")
        
        street_data = data[street]
        
        for strength in strength_order:
            if strength not in street_data:
                continue
            
            strength_data = street_data[strength]
            
            # Check if any data exists
            total_bets = sum(
                len(strength_data[b]['agg']) + len(strength_data[b]['nonagg'])
                for b in size_buckets
            )
            if total_bets == 0:
                continue
            
            print(f"\n  {strength.upper()}")
            print(f"  {'-'*96}")
            print(f"  {'Size':<10} | {'AGGRESSOR':<35} | {'NON-AGGRESSOR':<35}")
            print(f"  {'':<10} | {'Bets':<6} {'Win%':<8} {'AvgBB':<8} {'AvgPot%':<10} | {'Bets':<6} {'Win%':<8} {'AvgBB':<8} {'AvgPot%':<10}")
            print(f"  {'-'*96}")
            
            for bucket in size_buckets:
                agg_data = strength_data[bucket]['agg']
                nonagg_data = strength_data[bucket]['nonagg']
                
                if not agg_data and not nonagg_data:
                    continue
                
                def format_stats(d):
                    if not d:
                        return '-', '-', '-', '-'
                    wins = sum(1 for x in d if x['won'])
                    win_pct = f"{100*wins/len(d):.0f}%"
                    avg_bb = f"{sum(x['bb'] for x in d)/len(d):.1f}"
                    avg_pot = f"{sum(x['pot_pct'] for x in d)/len(d):.0f}%"
                    return str(len(d)), win_pct, avg_bb, avg_pot
                
                a_n, a_w, a_bb, a_pot = format_stats(agg_data)
                n_n, n_w, n_bb, n_pot = format_stats(nonagg_data)
                
                print(f"  {bucket:<10} | {a_n:<6} {a_w:<8} {a_bb:<8} {a_pot:<10} | {n_n:<6} {n_w:<8} {n_bb:<8} {n_pot:<10}")
            
            # Totals
            all_agg = [x for b in size_buckets for x in strength_data[b]['agg']]
            all_nonagg = [x for b in size_buckets for x in strength_data[b]['nonagg']]
            
            def format_total(d):
                if not d:
                    return '-', '-', '-', '-'
                wins = sum(1 for x in d if x['won'])
                return str(len(d)), f"{100*wins/len(d):.0f}%", f"{sum(x['bb'] for x in d)/len(d):.1f}", f"{sum(x['pot_pct'] for x in d)/len(d):.0f}%"
            
            a_n, a_w, a_bb, a_pot = format_total(all_agg)
            n_n, n_w, n_bb, n_pot = format_total(all_nonagg)
            
            print(f"  {'-'*96}")
            print(f"  {'TOTAL':<10} | {a_n:<6} {a_w:<8} {a_bb:<8} {a_pot:<10} | {n_n:<6} {n_w:<8} {n_bb:<8} {n_pot:<10}")

def print_summary(data):
    """Print key insights summary."""
    print(f"\n{'='*100}")
    print("  KEY INSIGHTS")
    print(f"{'='*100}")
    
    # Flop bluffs
    flop_hc_agg = [x for b in data['flop']['high_card'] for x in data['flop']['high_card'][b]['agg']]
    flop_hc_nonagg = [x for b in data['flop']['high_card'] for x in data['flop']['high_card'][b]['nonagg']]
    
    if flop_hc_agg:
        wins = sum(1 for x in flop_hc_agg if x['won'])
        print(f"\n  FLOP HIGH CARD (as aggressor): {len(flop_hc_agg)} bets, {100*wins/len(flop_hc_agg):.0f}% win")
    if flop_hc_nonagg:
        wins = sum(1 for x in flop_hc_nonagg if x['won'])
        print(f"  FLOP HIGH CARD (not aggressor): {len(flop_hc_nonagg)} bets, {100*wins/len(flop_hc_nonagg):.0f}% win")
    
    # Turn bluffs
    for strength in ['high_card', 'bottom_pair', 'middle_pair']:
        if strength in data['turn']:
            all_bets = [x for b in data['turn'][strength] for x in data['turn'][strength][b]['agg'] + data['turn'][strength][b]['nonagg']]
            if all_bets:
                wins = sum(1 for x in all_bets if x['won'])
                print(f"  TURN {strength.upper()}: {len(all_bets)} bets, {100*wins/len(all_bets):.0f}% win")
    
    # Value hands
    print(f"\n  VALUE HANDS:")
    for strength in ['tpgk', 'overpair', 'two_pair_both', 'set']:
        for street in ['flop', 'turn', 'river']:
            if strength in data[street]:
                all_bets = [x for b in data[street][strength] for x in data[street][strength][b]['agg'] + data[street][strength][b]['nonagg']]
                if all_bets:
                    wins = sum(1 for x in all_bets if x['won'])
                    print(f"  {street.upper()} {strength.upper()}: {len(all_bets)} bets, {100*wins/len(all_bets):.0f}% win")

if __name__ == '__main__':
    print("Parsing hand histories...")
    hands = parse_hands()
    print(f"Found {len(hands)} hands with hero cards")
    
    data, buckets = analyze_bets(hands)
    print_analysis(data, buckets)
    print_summary(data)
