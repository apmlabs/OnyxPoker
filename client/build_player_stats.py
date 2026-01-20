"""
Build player statistics from PokerStars hand histories.
Calculates VPIP, PFR, AF, 3-bet% for each opponent.
Consolidates OCR variations of names using fuzzy matching.
"""

import os
import re
import json
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

HAND_HISTORY_DIR = "../idealistslp_extracted"
HERO_NAME = "idealistslp"
FUZZY_THRESHOLD = 0.82  # 82% similarity to merge names

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

def consolidate_names(stats: Dict[str, Dict]) -> Dict[str, Dict]:
    """Merge similar player names, keeping the one with most hands."""
    names = list(stats.keys())
    merged = {}  # canonical_name -> list of merged names
    name_map = {}  # any_name -> canonical_name
    
    for name in sorted(names, key=lambda n: -stats[n]['hands']):
        if name in name_map:
            continue  # Already merged into another
        
        # Find similar names not yet assigned
        similar = [name]
        for other in names:
            if other == name or other in name_map:
                continue
            ratio = SequenceMatcher(None, name.lower(), other.lower()).ratio()
            if ratio > FUZZY_THRESHOLD:
                similar.append(other)
                name_map[other] = name
        
        name_map[name] = name
        merged[name] = similar
    
    # Combine stats for merged names
    result = {}
    for canonical, variants in merged.items():
        combined = stats[canonical].copy()
        for var in variants[1:]:  # Skip canonical itself
            s = stats[var]
            combined['hands'] += s['hands']
            # Weighted average for percentages
            total = combined['hands']
            w1 = stats[canonical]['hands'] / total
            w2 = s['hands'] / total
            combined['vpip'] = round(combined['vpip'] * w1 + s['vpip'] * w2, 1)
            combined['pfr'] = round(combined['pfr'] * w1 + s['pfr'] * w2, 1)
            combined['3bet'] = round(combined['3bet'] * w1 + s['3bet'] * w2, 1)
            combined['af'] = round(combined['af'] * w1 + s['af'] * w2, 2)
        
        # Reclassify with combined stats
        combined['archetype'] = classify_archetype(combined['vpip'], combined['pfr'], combined['af'])
        combined['advice'] = get_advice(combined['archetype'], {})
        if len(variants) > 1:
            combined['aliases'] = variants[1:]  # Store merged names
        result[canonical] = combined
    
    return result

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
        
        archetype = classify_archetype(vpip_pct, pfr_pct, af)
        result[player] = {
            'hands': s['hands'],
            'vpip': round(vpip_pct, 1),
            'pfr': round(pfr_pct, 1),
            '3bet': round(three_bet_pct, 1),
            'af': round(af, 2),
            'archetype': archetype,
            'advice': get_advice(archetype, {})
        }
    
    return result

def classify_archetype(vpip: float, pfr: float, af: float) -> str:
    """
    Classify player into archetype based on comprehensive research.
    
    Sources: PokerTracker, Poker Copilot, SmartPokerStudy, 2+2, Reddit
    Key rule: gap > PFR = fish (but only for loose players, VPIP 25+)
    
    Ranges (6-max):
    - Nit: VPIP ≤12%
    - Rock: VPIP 10-20%, PFR ≤5%
    - TAG: VPIP 18-25%, PFR 15-20%, gap ≤5
    - LAG: VPIP 26-35%, PFR 20-30%, gap ≤10
    - Maniac: VPIP 40%+, PFR 30%+
    - Fish: VPIP 25%+ with gap > PFR, or VPIP 40%+ with low PFR
    """
    gap = vpip - pfr
    
    # Maniac: VPIP 40+, PFR 30+ (both very high)
    if vpip >= 40 and pfr >= 30:
        return 'maniac'
    
    # Nit: VPIP ≤12 (ultra tight)
    if vpip <= 12:
        return 'nit'
    
    # Rock: VPIP ≤20, PFR ≤5 (tight passive) - check before fish rule
    if vpip <= 20 and pfr <= 5:
        return 'rock'
    
    # Fish: VPIP 40+ with low PFR
    if vpip >= 40 and pfr < 20:
        return 'fish'
    
    # Fish rule: gap > PFR for loose players (VPIP 25+)
    if vpip >= 25 and pfr > 0 and gap > pfr:
        return 'fish'
    
    # TAG: VPIP 18-25, PFR 15+, gap ≤5
    if vpip >= 18 and vpip <= 25 and pfr >= 15 and gap <= 5:
        return 'tag'
    
    # LAG: VPIP 26-35, PFR 20+, gap ≤10
    if vpip >= 26 and vpip <= 35 and pfr >= 20 and gap <= 10:
        return 'lag'
    
    # Nit-ish: VPIP 13-18 (tight but not ultra)
    if vpip <= 18:
        return 'nit'
    
    # Rock: VPIP 18-25, PFR 6-14 (moderate tight passive)
    if vpip >= 18 and vpip <= 25 and pfr < 15:
        return 'rock'
    
    # LAG: VPIP >25, PFR high, small gap
    if vpip > 25 and pfr >= 18 and gap <= 10:
        return 'lag'
    
    # Default loose = fish
    return 'fish'

def get_advice(archetype: str, stats: Dict) -> str:
    """Get exploitation advice for archetype."""
    advice = {
        'fish': "Isolate wide | Value bet | Calls too much | Never bluff",
        'nit': "Steal blinds | Fold to bets | Too tight | Raise IP, fold to 3bet",
        'rock': "Steal more | Bet = nuts | Raises monsters | Raise IP, fold vs bet",
        'tag': "Respect raises | Play solid | Avoid | vs raise: TT+/AK",
        'lag': "Tighten up | Call down | Over-aggro | vs raise: 99+/AQ+, call down",
        'maniac': "Only premiums | Call everything | Can't fold | vs raise: QQ+/AK, call down",
    }
    return advice.get(archetype, "no reads")

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
    before_count = len(player_stats)
    
    # Consolidate similar names
    player_stats = consolidate_names(player_stats)
    merged_count = before_count - len(player_stats)
    
    # Sort by hands played
    sorted_players = sorted(player_stats.items(), key=lambda x: x[1]['hands'], reverse=True)
    
    print(f"\nFound {len(sorted_players)} players with 5+ hands")
    if merged_count > 0:
        print(f"Merged {merged_count} duplicate names")
    
    print(f"\n{'Player':<20} {'Hands':>6} {'VPIP':>6} {'PFR':>6} {'3bet':>6} {'AF':>6} {'Type':<8} Advice")
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
