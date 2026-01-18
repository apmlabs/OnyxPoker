"""
Build player statistics from PokerStars hand histories.
Calculates VPIP, PFR, AF, 3-bet% for each opponent.
"""

import os
import re
import json
from collections import defaultdict
from typing import Dict, List, Tuple

HAND_HISTORY_DIR = "../idealistslp_extracted"
HERO_NAME = "idealistslp"

def parse_hand_file(filepath: str) -> List[Dict]:
    """Parse a hand history file into individual hands."""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    hands = []
    hand_texts = re.split(r'\n\n\n+', content)
    
    for hand_text in hand_texts:
        if not hand_text.strip() or 'PokerStars' not in hand_text:
            continue
        hands.append(parse_single_hand(hand_text))
    
    return [h for h in hands if h]

def parse_single_hand(text: str) -> Dict:
    """Parse a single hand into structured data."""
    lines = text.strip().split('\n')
    
    # Extract players
    players = {}
    for line in lines:
        seat_match = re.match(r'Seat (\d+): (\S+) \(.*€([\d.]+)', line)
        if seat_match:
            seat, name, stack = seat_match.groups()
            players[name] = {'seat': int(seat), 'stack': float(stack)}
    
    if not players:
        return None
    
    # Find preflop actions
    preflop_start = False
    preflop_actions = []
    postflop_actions = []
    current_section = None
    
    for line in lines:
        if '*** HOLE CARDS ***' in line:
            current_section = 'preflop'
            continue
        elif '*** FLOP ***' in line:
            current_section = 'flop'
            continue
        elif '*** TURN ***' in line:
            current_section = 'turn'
            continue
        elif '*** RIVER ***' in line:
            current_section = 'river'
            continue
        elif '*** SUMMARY ***' in line:
            break
        
        if current_section == 'preflop':
            # Parse preflop action
            action_match = re.match(r'(\S+): (folds|calls|raises|checks|bets)', line)
            if action_match:
                player, action = action_match.groups()
                preflop_actions.append((player, action))
        elif current_section in ['flop', 'turn', 'river']:
            action_match = re.match(r'(\S+): (folds|calls|raises|checks|bets)', line)
            if action_match:
                player, action = action_match.groups()
                postflop_actions.append((player, action, current_section))
    
    return {
        'players': players,
        'preflop_actions': preflop_actions,
        'postflop_actions': postflop_actions
    }

def calculate_stats(hands: List[Dict]) -> Dict[str, Dict]:
    """Calculate VPIP, PFR, AF, 3-bet% for each player."""
    stats = defaultdict(lambda: {
        'hands': 0,
        'vpip': 0,  # Voluntarily put $ in pot
        'pfr': 0,   # Preflop raise
        'three_bet_opps': 0,
        'three_bets': 0,
        'postflop_bets': 0,
        'postflop_calls': 0,
        'postflop_raises': 0,
        'af_actions': 0,  # bets + raises
        'af_passive': 0,  # calls
    })
    
    for hand in hands:
        if not hand:
            continue
        
        players_in_hand = set(hand['players'].keys())
        preflop = hand['preflop_actions']
        
        # Track who has acted and how
        first_raiser = None
        players_acted = set()
        
        for player, action in preflop:
            if player == HERO_NAME:
                continue  # Skip hero stats
            
            stats[player]['hands'] += 1
            
            # VPIP: any voluntary action (call or raise, not fold/check)
            if action in ['calls', 'raises']:
                stats[player]['vpip'] += 1
            
            # PFR: raised preflop
            if action == 'raises':
                if first_raiser is None:
                    first_raiser = player
                    stats[player]['pfr'] += 1
                else:
                    # This is a 3-bet or higher
                    stats[player]['pfr'] += 1
                    stats[player]['three_bets'] += 1
            
            # 3-bet opportunity: someone raised before you
            if first_raiser and player != first_raiser and player not in players_acted:
                stats[player]['three_bet_opps'] += 1
            
            players_acted.add(player)
        
        # Postflop aggression
        for player, action, street in hand['postflop_actions']:
            if player == HERO_NAME:
                continue
            
            if action in ['bets', 'raises']:
                stats[player]['af_actions'] += 1
            elif action == 'calls':
                stats[player]['af_passive'] += 1
    
    # Calculate final percentages
    result = {}
    for player, s in stats.items():
        if s['hands'] < 5:  # Need minimum sample
            continue
        
        vpip_pct = (s['vpip'] / s['hands'] * 100) if s['hands'] > 0 else 0
        pfr_pct = (s['pfr'] / s['hands'] * 100) if s['hands'] > 0 else 0
        three_bet_pct = (s['three_bets'] / s['three_bet_opps'] * 100) if s['three_bet_opps'] > 0 else 0
        af = (s['af_actions'] / s['af_passive']) if s['af_passive'] > 0 else s['af_actions']
        
        result[player] = {
            'hands': s['hands'],
            'vpip': round(vpip_pct, 1),
            'pfr': round(pfr_pct, 1),
            '3bet': round(three_bet_pct, 1),
            'af': round(af, 2),
            'archetype': classify_archetype(vpip_pct, pfr_pct, af)
        }
    
    return result

def classify_archetype(vpip: float, pfr: float, af: float) -> str:
    """Classify player into archetype based on stats."""
    if vpip == 0:
        return 'nit'
    
    # Aggression factor ratio
    af_ratio = pfr / vpip if vpip > 0 else 0
    
    # Maniac: super loose super aggressive
    if vpip > 50 and pfr > 35:
        return 'maniac'
    # Fish: loose passive (high VPIP, low PFR relative to VPIP)
    if vpip > 40 or (vpip > 30 and af_ratio < 0.5):
        return 'fish'
    # Nit: ultra tight
    if vpip < 15:
        return 'nit'
    # LAG: loose aggressive (VPIP > 27 is key threshold)
    if vpip > 27 and af_ratio > 0.6:
        return 'lag'
    # TAG: tight aggressive (the default winning style)
    if vpip <= 27 and af_ratio > 0.5:
        return 'tag'
    # Loose passive (calls a lot, rarely raises)
    if vpip > 25 and af_ratio < 0.5:
        return 'fish'
    # Tight passive
    if vpip <= 25 and af_ratio < 0.5:
        return 'rock'
    
    return 'reg'  # Default: regular player

def get_advice(archetype: str, stats: Dict) -> str:
    """Get exploitation advice for archetype."""
    advice = {
        'fish': "Value bet relentlessly. Don't bluff. They call too much.",
        'nit': "Steal blinds. Fold to their raises - they have it.",
        'tag': "Respect their raises. 3-bet light occasionally.",
        'lag': "Call down lighter. They bluff too much.",
        'maniac': "Let them hang themselves. Call with medium strength."
    }
    return advice.get(archetype, "Play solid.")

def main():
    # Parse all hand histories
    all_hands = []
    hh_dir = os.path.join(os.path.dirname(__file__), HAND_HISTORY_DIR)
    
    for filename in os.listdir(hh_dir):
        if filename.startswith('HH') and filename.endswith('.txt'):
            filepath = os.path.join(hh_dir, filename)
            hands = parse_hand_file(filepath)
            all_hands.extend(hands)
    
    print(f"Parsed {len(all_hands)} hands")
    
    # Calculate stats
    player_stats = calculate_stats(all_hands)
    
    # Sort by hands played
    sorted_players = sorted(player_stats.items(), key=lambda x: x[1]['hands'], reverse=True)
    
    print(f"\nFound {len(sorted_players)} players with 5+ hands\n")
    print(f"{'Player':<20} {'Hands':>6} {'VPIP':>6} {'PFR':>6} {'3bet':>6} {'AF':>6} {'Type':<8} Advice")
    print("-" * 100)
    
    for player, s in sorted_players[:30]:  # Top 30
        advice = get_advice(s['archetype'], s)
        print(f"{player:<20} {s['hands']:>6} {s['vpip']:>5.1f}% {s['pfr']:>5.1f}% {s['3bet']:>5.1f}% {s['af']:>6.2f} {s['archetype']:<8} {advice}")
    
    # Save to JSON for helper_bar to use
    output_path = os.path.join(os.path.dirname(__file__), 'player_stats.json')
    with open(output_path, 'w') as f:
        json.dump(player_stats, f, indent=2)
    print(f"\nSaved stats to {output_path}")

if __name__ == "__main__":
    main()
