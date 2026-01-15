#!/usr/bin/env python3
"""
Deep strategy evaluation with real poker metrics.
Compares strategies against industry-standard winning player stats.
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poker_logic import STRATEGIES, preflop_action, postflop_action, analyze_hand, calculate_equity

# All 169 starting hands
def generate_all_hands():
    """Generate all 169 unique starting hands."""
    ranks = 'AKQJT98765432'
    hands = []
    for i, r1 in enumerate(ranks):
        for j, r2 in enumerate(ranks):
            if i < j:
                hands.append(f"{r1}{r2}s")  # suited
                hands.append(f"{r1}{r2}o")  # offsuit
            elif i == j:
                hands.append(f"{r1}{r2}")   # pair
    return hands

ALL_HANDS = generate_all_hands()
POSITIONS = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']

# Industry benchmarks
BENCHMARKS = {
    'fish':      {'vpip': 56, 'pfr': 5,  'gap': 51, 'af': 0.5, 'profile': 'Loose-Passive'},
    'passive':   {'vpip': 24, 'pfr': 2,  'gap': 22, 'af': 0.8, 'profile': 'Loose-Passive'},
    'nit':       {'vpip': 12, 'pfr': 10, 'gap': 2,  'af': 1.5, 'profile': 'Tight-Passive'},
    'tag':       {'vpip': 21, 'pfr': 18, 'gap': 3,  'af': 2.5, 'profile': 'Tight-Aggressive (Winner)'},
    'lag':       {'vpip': 28, 'pfr': 25, 'gap': 3,  'af': 3.5, 'profile': 'Loose-Aggressive'},
}

def calc_preflop_stats(strategy_name):
    """Calculate VPIP/PFR for a strategy across all positions."""
    strategy = STRATEGIES.get(strategy_name)
    if not strategy:
        return None
    
    stats = {pos: {'vpip': 0, 'pfr': 0, 'call': 0, 'total': 0, '3bet': 0, '3bet_opp': 0, 'defend': 0, 'defend_opp': 0} for pos in POSITIONS}
    
    for hand in ALL_HANDS:
        for pos in POSITIONS:
            # Scenario 1: First to act (no raise) - BB can't be first to act
            if pos != 'BB':
                action, _ = preflop_action(hand, pos, strategy, facing='none')
                stats[pos]['total'] += 1
                if action in ['raise', 'call']:
                    stats[pos]['vpip'] += 1
                if action == 'raise':
                    stats[pos]['pfr'] += 1
            
            # Scenario 2: Facing open (from earlier position)
            if pos not in ['UTG']:  # UTG can't face an open
                action2, _ = preflop_action(hand, pos, strategy, facing='open', opener_pos='UTG')
                stats[pos]['total'] += 1
                stats[pos]['3bet_opp'] += 1
                
                if action2 in ['raise', 'call']:
                    stats[pos]['vpip'] += 1
                if action2 == 'raise':
                    stats[pos]['pfr'] += 1
                    stats[pos]['3bet'] += 1
                if action2 == 'call':
                    stats[pos]['call'] += 1
                
                # BB defense tracking
                if pos == 'BB':
                    stats[pos]['defend_opp'] += 1
                    if action2 in ['raise', 'call']:
                        stats[pos]['defend'] += 1
    
    # Aggregate
    total_vpip = sum(s['vpip'] for s in stats.values())
    total_pfr = sum(s['pfr'] for s in stats.values())
    total_call = sum(s['call'] for s in stats.values())
    total_hands = sum(s['total'] for s in stats.values())
    total_3bet = sum(s['3bet'] for s in stats.values())
    total_3bet_opp = sum(s['3bet_opp'] for s in stats.values())
    total_defend = stats['BB']['defend']
    total_defend_opp = stats['BB']['defend_opp']
    
    return {
        'vpip': total_vpip / total_hands * 100,
        'pfr': total_pfr / total_hands * 100,
        'call_pct': total_call / total_hands * 100,
        'gap': (total_vpip - total_pfr) / total_hands * 100,
        '3bet': total_3bet / total_3bet_opp * 100 if total_3bet_opp > 0 else 0,
        'bb_defend': total_defend / total_defend_opp * 100 if total_defend_opp > 0 else 0,
        'by_position': {
            pos: {
                'vpip': s['vpip'] / s['total'] * 100 if s['total'] > 0 else 0,
                'pfr': s['pfr'] / s['total'] * 100 if s['total'] > 0 else 0,
                '3bet': s['3bet'] / s['3bet_opp'] * 100 if s['3bet_opp'] > 0 else 0,
            } for pos, s in stats.items()
        }
    }

def calc_postflop_stats_from_logs():
    """Calculate postflop stats from real session logs."""
    log_dir = '../server/uploads'
    
    stats = {
        'flop': {'bets': 0, 'raises': 0, 'calls': 0, 'checks': 0, 'folds': 0},
        'turn': {'bets': 0, 'raises': 0, 'calls': 0, 'checks': 0, 'folds': 0},
        'river': {'bets': 0, 'raises': 0, 'calls': 0, 'checks': 0, 'folds': 0},
    }
    
    total_hands = 0
    
    for fname in os.listdir(log_dir):
        if not fname.startswith('session_') or not fname.endswith('.jsonl'):
            continue
        with open(os.path.join(log_dir, fname)) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if not d.get('board') or not d.get('is_hero_turn'):
                        continue
                    
                    total_hands += 1
                    board_len = len(d['board'])
                    street = 'flop' if board_len == 3 else 'turn' if board_len == 4 else 'river'
                    action = d.get('action', '').lower()
                    to_call = float(d.get('to_call') or 0)
                    
                    if action == 'fold':
                        stats[street]['folds'] += 1
                    elif action == 'check':
                        stats[street]['checks'] += 1
                    elif action == 'call':
                        stats[street]['calls'] += 1
                    elif action == 'bet':
                        stats[street]['bets'] += 1
                    elif action == 'raise':
                        if to_call > 0:
                            stats[street]['raises'] += 1
                        else:
                            stats[street]['bets'] += 1
                except:
                    pass
    
    # Calculate AF per street: (bets + raises) / calls
    result = {'total_hands': total_hands}
    for street in ['flop', 'turn', 'river']:
        s = stats[street]
        total = s['bets'] + s['raises'] + s['calls'] + s['checks'] + s['folds']
        aggressive = s['bets'] + s['raises']
        passive = s['calls']
        
        result[street] = {
            'af': aggressive / passive if passive > 0 else aggressive,
            'fold_pct': s['folds'] / total * 100 if total > 0 else 0,
            'agg_pct': aggressive / total * 100 if total > 0 else 0,
            'total': total,
        }
    
    # Overall AF
    all_bets = sum(stats[st]['bets'] + stats[st]['raises'] for st in stats)
    all_calls = sum(stats[st]['calls'] for st in stats)
    result['overall_af'] = all_bets / all_calls if all_calls > 0 else all_bets
    
    return result

def classify_profile(vpip, pfr, af):
    """Classify strategy into player type."""
    gap = vpip - pfr
    
    # Loose vs Tight
    tightness = 'Tight' if vpip < 25 else 'Loose'
    
    # Passive vs Aggressive
    aggression = 'Aggressive' if af >= 2.0 or (pfr / vpip > 0.7 if vpip > 0 else False) else 'Passive'
    
    profile = f"{tightness}-{aggression}"
    
    # Find closest benchmark
    min_dist = float('inf')
    closest = 'tag'
    for name, bench in BENCHMARKS.items():
        dist = abs(vpip - bench['vpip']) + abs(pfr - bench['pfr']) + abs(af - bench['af']) * 5
        if dist < min_dist:
            min_dist = dist
            closest = name
    
    return profile, closest

def print_preflop_report(strategy_name, stats):
    """Print preflop stats report."""
    print(f"\n{'='*70}")
    print(f"PREFLOP PROFILE: {strategy_name.upper()}")
    print('='*70)
    
    tag = BENCHMARKS['tag']
    
    def rating(val, target, tolerance=3):
        diff = abs(val - target)
        if diff <= tolerance: return 'GOOD'
        elif val > target: return 'HIGH'
        else: return 'LOW'
    
    print(f"\n  VPIP:  {stats['vpip']:5.1f}%  (target: {tag['vpip']}%)  [{rating(stats['vpip'], tag['vpip'])}]")
    print(f"  PFR:   {stats['pfr']:5.1f}%  (target: {tag['pfr']}%)  [{rating(stats['pfr'], tag['pfr'])}]")
    print(f"  Gap:   {stats['gap']:5.1f}%  (target: {tag['gap']}%)  [{rating(stats['gap'], tag['gap'], 2)}]")
    print(f"  3-bet: {stats['3bet']:5.1f}%  (target: 6-10%)")
    print(f"  BB Def:{stats['bb_defend']:5.1f}%  (target: 35-45%)")
    
    print(f"\n  Position Breakdown:")
    print(f"  {'Pos':<5} {'VPIP':>7} {'PFR':>7} {'3bet':>7}")
    print(f"  {'-'*28}")
    for pos in POSITIONS:
        p = stats['by_position'][pos]
        print(f"  {pos:<5} {p['vpip']:>6.1f}% {p['pfr']:>6.1f}% {p['3bet']:>6.1f}%")

def print_postflop_report(stats):
    """Print postflop stats report."""
    print(f"\n{'='*70}")
    print("POSTFLOP PROFILE (from real logs)")
    print('='*70)
    
    tag_af = BENCHMARKS['tag']['af']
    
    def af_rating(val):
        if 2.0 <= val <= 3.5: return 'GOOD'
        elif val < 2.0: return 'PASSIVE'
        else: return 'AGGRO'
    
    print(f"\n  Overall AF: {stats['overall_af']:.2f}  (target: {tag_af})  [{af_rating(stats['overall_af'])}]")
    print(f"  Total postflop hands: {stats['total_hands']}")
    
    print(f"\n  By Street:")
    print(f"  {'Street':<8} {'AF':>6} {'Fold%':>8} {'Agg%':>8} {'Hands':>8}")
    print(f"  {'-'*42}")
    for street in ['flop', 'turn', 'river']:
        s = stats[street]
        print(f"  {street.capitalize():<8} {s['af']:>6.2f} {s['fold_pct']:>7.1f}% {s['agg_pct']:>7.1f}% {s['total']:>8}")

def print_comparison(strategy_name, preflop, postflop):
    """Print comparison to benchmarks."""
    print(f"\n{'='*70}")
    print("COMPARISON TO PLAYER TYPES")
    print('='*70)
    
    vpip = preflop['vpip']
    pfr = preflop['pfr']
    af = postflop['overall_af']
    
    profile, closest = classify_profile(vpip, pfr, af)
    
    print(f"\n  {'Type':<12} {'VPIP':>7} {'PFR':>7} {'Gap':>5} {'AF':>5}  Profile")
    print(f"  {'-'*55}")
    
    for name, bench in BENCHMARKS.items():
        marker = ' <-- closest' if name == closest else ''
        print(f"  {name:<12} {bench['vpip']:>6}% {bench['pfr']:>6}% {bench['gap']:>5} {bench['af']:>5.1f}  {bench['profile']}{marker}")
    
    print(f"  {'-'*55}")
    print(f"  {strategy_name:<12} {vpip:>6.1f}% {pfr:>6.1f}% {vpip-pfr:>5.1f} {af:>5.2f}  {profile}")
    
    # Verdict
    print(f"\n  VERDICT: {strategy_name} plays like a {closest.upper()}")
    if closest == 'tag':
        print("           This is the winning player profile!")
    elif closest == 'lag':
        print("           Aggressive but can be profitable with skill.")
    elif closest == 'nit':
        print("           Too tight - missing value from playable hands.")
    else:
        print("           This profile typically loses money long-term.")

def main():
    strategies = sys.argv[1:] if len(sys.argv) > 1 else ['value_lord', 'value_maniac', 'value_max']
    
    print("\n" + "="*70)
    print("DEEP STRATEGY EVALUATION")
    print("="*70)
    print(f"\nStrategies: {', '.join(strategies)}")
    
    # Get postflop stats once (same for all - from logs)
    postflop = calc_postflop_stats_from_logs()
    
    for strat in strategies:
        if strat not in STRATEGIES:
            print(f"\nStrategy '{strat}' not found!")
            continue
        
        preflop = calc_preflop_stats(strat)
        
        print_preflop_report(strat, preflop)
        print_postflop_report(postflop)
        print_comparison(strat, preflop, postflop)
    
    # Summary table
    if len(strategies) > 1:
        print(f"\n{'='*70}")
        print("SUMMARY")
        print('='*70)
        print(f"\n  {'Strategy':<14} {'VPIP':>7} {'PFR':>7} {'3bet':>7} {'AF':>6}  Profile")
        print(f"  {'-'*58}")
        
        for strat in strategies:
            if strat not in STRATEGIES:
                continue
            preflop = calc_preflop_stats(strat)
            profile, closest = classify_profile(preflop['vpip'], preflop['pfr'], postflop['overall_af'])
            print(f"  {strat:<14} {preflop['vpip']:>6.1f}% {preflop['pfr']:>6.1f}% {preflop['3bet']:>6.1f}% {postflop['overall_af']:>6.2f}  {profile}")

if __name__ == '__main__':
    main()
