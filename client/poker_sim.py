#!/usr/bin/env python3
"""
Poker Strategy Simulator - Pits 8 preflop strategies against each other
"""

import random
from collections import defaultdict
from itertools import combinations

# Card representation
RANKS = '23456789TJQKA'
SUITS = 'shdc'
RANK_VAL = {r: i for i, r in enumerate(RANKS)}

def make_deck():
    return [(r, s) for r in RANKS for s in SUITS]

def hand_to_str(cards):
    """Convert 2 cards to hand notation like 'AKs' or 'AKo'"""
    c1, c2 = sorted(cards, key=lambda x: RANK_VAL[x[0]], reverse=True)
    r1, s1 = c1
    r2, s2 = c2
    if r1 == r2:
        return r1 + r2  # Pair
    elif s1 == s2:
        return r1 + r2 + 's'  # Suited
    else:
        return r1 + r2 + 'o'  # Offsuit

# Hand range definitions for each strategy
# Format: {position: {action: set of hands}}
# Positions: UTG, MP, CO, BTN, SB, BB
# Actions: open, 3bet_vs_utg, 3bet_vs_mp, 3bet_vs_co, 3bet_vs_btn, call_vs_X, etc.

def expand_range(range_str):
    """Expand range notation to set of hands"""
    hands = set()
    
    # Parse pairs like "77+" or "22"
    def add_pairs(start, end='A'):
        for i in range(RANK_VAL[start], RANK_VAL[end] + 1):
            hands.add(RANKS[i] + RANKS[i])
    
    # Parse suited/offsuit like "ATs+" or "AJo"
    def add_hands(h1, h2, suited, plus=False):
        if plus:
            start_idx = RANK_VAL[h2]
            end_idx = RANK_VAL[h1] - 1
            for i in range(start_idx, end_idx + 1):
                h = h1 + RANKS[i] + ('s' if suited else 'o')
                hands.add(h)
        else:
            hands.add(h1 + h2 + ('s' if suited else 'o'))
    
    parts = range_str.replace(' ', '').split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Pairs: 77+, 22, TT-88
        if len(part) == 2 and part[0] == part[1]:
            add_pairs(part[0], part[0])
        elif len(part) == 3 and part[0] == part[1] and part[2] == '+':
            add_pairs(part[0], 'A')
        elif '-' in part and len(part) == 5 and part[0] == part[1]:
            add_pairs(part[3], part[0])
        
        # Suited: ATs+, A5s-A2s, KQs
        elif part.endswith('s+'):
            add_hands(part[0], part[1], True, True)
        elif part.endswith('s') and '-' not in part:
            add_hands(part[0], part[1], True, False)
        elif 's-' in part:  # A5s-A2s
            h1 = part[0]
            start = part[part.index('-')+2]
            end = part[1]
            for i in range(RANK_VAL[start], RANK_VAL[end] + 1):
                hands.add(h1 + RANKS[i] + 's')
        
        # Offsuit: AJo+, KQo
        elif part.endswith('o+'):
            add_hands(part[0], part[1], False, True)
        elif part.endswith('o'):
            add_hands(part[0], part[1], False, False)
        
        # Both suited and offsuit: A2+
        elif len(part) == 3 and part[2] == '+':
            add_hands(part[0], part[1], True, True)
            add_hands(part[0], part[1], False, True)
    
    return hands

# Strategy definitions (simplified from files)
STRATEGIES = {
    'kiro_v2': {
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A3s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('55+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,87s,76s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T7s+,96s+,85s+,75s,65s,54s,A8o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_value': expand_range('QQ+,AKs,AKo,JJ,AQs+,AKo'),
        '3bet_bluff': expand_range('A5s-A4s,K9s'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'sonnet': {
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A2s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K6s+,Q7s+,J7s+,T7s+,96s+,85s+,75s+,64s+,54s,A7o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_value': expand_range('QQ+,AKs,AKo,JJ,AQs+'),
        '3bet_bluff': expand_range('A5s-A4s,K9s-K8s'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'kiro_optimal': {
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A2s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T7s+,96s+,85s+,75s+,64s+,54s,A7o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_value': expand_range('QQ+,AKs,AKo,JJ,AQs+'),
        '3bet_bluff': expand_range('A5s-A4s,K9s'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'kiro5': {
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A3s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T7s+,96s+,85s+,75s+,64s+,54s,A8o+,K9o+,QTo+,JTo'),
            'SB': expand_range('44+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_value': expand_range('QQ+,AKs,AKo,JJ,AQs+'),
        '3bet_bluff': expand_range('A5s-A4s,K9s'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'gpt4': {
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AJo+,AQo+'),
            'MP': expand_range('66+,ATs+,A5s-A2s,KJs+,QJs,JTs,KQo,AJo+,AQo+'),
            'CO': expand_range('55+,A8s+,A5s-A2s,KTs+,QTs+,JTs,T9s,98s,87s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,75s+,65s,54s,A2o+,KTo+,QTo+,JTo,T9o,98o'),
            'SB': expand_range('22+,A2s+,K6s+,Q7s+,J7s+,T7s+,97s+,86s+,75s+,65s,54s,ATo+,KJo+,QJo,JTo'),
        },
        '3bet_value': expand_range('QQ+,AKs,AKo,JJ,AQs,TT,AJs+,AQo+,KQs'),
        '3bet_bluff': expand_range('A5s-A2s'),
        'call_3bet': expand_range('JJ,TT,AQs,AKo,KQs'),
        '4bet': expand_range('QQ+,AKs,AKo'),
    },
    'gpt3': {
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AJo+,AQo+'),
            'MP': expand_range('66+,ATs+,A5s-A2s,KJs+,QJs,JTs,KQo,AJo+,AQo+'),
            'CO': expand_range('55+,A8s+,A5s-A2s,KTs+,QTs+,JTs,T9s,98s,87s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,75s+,65s,54s,A2o+,KTo+,QTo+,JTo,T9o,98o'),
            'SB': expand_range('22+,A2s+,K6s+,Q7s+,J7s+,T7s+,97s+,86s+,75s+,65s,54s,ATo+,KJo+,QJo,JTo'),
        },
        '3bet_value': expand_range('QQ+,AKs,AKo,JJ,AQs,TT,AJs+,AQo+,KQs'),
        '3bet_bluff': expand_range('A5s-A2s'),
        'call_3bet': expand_range('JJ,TT,AQs,AKo,KQs'),
        '4bet': expand_range('QQ+,AKs,AKo'),
    },
    'opus2': {
        'open': {
            'UTG': expand_range('99+,AJs+,KQs,AQo+'),
            'MP': expand_range('77+,ATs+,KJs+,QJs,AJo+,KQo'),
            'CO': expand_range('55+,A8s+,A5s-A4s,KTs+,QTs+,JTs,T9s,98s,ATo+,KJo+'),
            'BTN': expand_range('22+,A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A7o+,KTo+,QJo'),
            'SB': expand_range('55+,A4s+,K9s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KJo+'),
        },
        '3bet_value': expand_range('QQ+,AKs,AKo,JJ,AQs'),
        '3bet_bluff': expand_range('A5s-A4s'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    # Player archetypes
    'fish': {
        'open': {
            'UTG': expand_range('88+,ATs+,KQs,AJo+'),
            'MP': expand_range('77+,A9s+,KJs+,QJs,ATo+,KQo'),
            'CO': expand_range('66+,A7s+,KTs+,QTs+,JTs,ATo+,KJo+'),
            'BTN': expand_range('55+,A5s+,K9s+,Q9s+,J9s+,T9s,98s,A9o+,KTo+,QJo'),
            'SB': expand_range('66+,A7s+,K9s+,Q9s+,JTs,A9o+,KJo+'),
        },
        '3bet_value': expand_range('QQ+,AKs'),
        '3bet_bluff': set(),  # Fish don't bluff 3-bet
        'call_3bet': expand_range('QQ,JJ,TT,AKs,AKo,AQs,AQo,AJs,KQs'),  # Calls too wide
        '4bet': expand_range('AA,KK'),
        'call_open_wide': True,  # Special flag: calls opens very wide
    },
    'nit': {
        'open': {
            'UTG': expand_range('TT+,AQs+,AKo'),
            'MP': expand_range('99+,AJs+,KQs,AQo+'),
            'CO': expand_range('88+,ATs+,KQs,AJo+,KQo'),
            'BTN': expand_range('77+,A9s+,KJs+,QJs,ATo+,KJo+'),
            'SB': expand_range('88+,ATs+,KQs,AJo+'),
        },
        '3bet_value': expand_range('QQ+,AKs,AKo'),
        '3bet_bluff': set(),  # Nits don't bluff
        'call_3bet': expand_range('QQ,AKs'),  # Very tight
        '4bet': expand_range('KK+'),
        'fold_to_3bet_wide': True,  # Special flag: folds too much to 3-bets
    },
    'lag': {
        'open': {
            'UTG': expand_range('66+,A9s+,A5s-A2s,KTs+,QTs+,JTs,ATo+,KQo'),
            'MP': expand_range('55+,A7s+,A5s-A2s,K9s+,Q9s+,J9s+,T9s,98s,ATo+,KJo+,QJo'),
            'CO': expand_range('33+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,54s,A8o+,KTo+,QTo+,JTo'),
            'BTN': expand_range('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,96s+,85s+,74s+,64s+,53s+,A5o+,K8o+,Q9o+,J9o+,T9o'),
            'SB': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,A7o+,K9o+,QTo+'),
        },
        '3bet_value': expand_range('QQ+,AKs,AKo,JJ,TT,AQs'),
        '3bet_bluff': expand_range('A5s-A2s,K9s-K7s,Q9s,J9s,T9s,98s,87s,76s'),
        'call_3bet': expand_range('JJ,TT,AKo,AQs,AQo,KQs'),
        '4bet': expand_range('QQ+,AKs'),
    },
    'tag': {
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('55+,A7s+,K9s+,Q9s+,J9s+,T9s,98s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,87s,76s,65s,A9o+,KTo+,QJo'),
            'SB': expand_range('55+,A5s+,K9s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KJo+'),
        },
        '3bet_value': expand_range('QQ+,AKs,AKo,JJ,AQs'),
        '3bet_bluff': expand_range('A5s-A4s'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
}

# Preflop hand equity (simplified - heads up all-in equity approximations)
HAND_STRENGTH = {}
for r1 in RANKS:
    for r2 in RANKS:
        if RANK_VAL[r1] >= RANK_VAL[r2]:
            # Pairs
            if r1 == r2:
                HAND_STRENGTH[r1+r2] = 50 + RANK_VAL[r1] * 3
            else:
                # Suited
                HAND_STRENGTH[r1+r2+'s'] = 35 + RANK_VAL[r1] * 2 + RANK_VAL[r2]
                # Offsuit
                HAND_STRENGTH[r1+r2+'o'] = 32 + RANK_VAL[r1] * 2 + RANK_VAL[r2]

# Boost premium hands
HAND_STRENGTH['AA'] = 85
HAND_STRENGTH['KK'] = 82
HAND_STRENGTH['QQ'] = 80
HAND_STRENGTH['JJ'] = 77
HAND_STRENGTH['TT'] = 75
HAND_STRENGTH['AKs'] = 67
HAND_STRENGTH['AKo'] = 65
HAND_STRENGTH['AQs'] = 64
HAND_STRENGTH['AQo'] = 62

POSITIONS = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']

class Player:
    def __init__(self, name, strategy):
        self.name = name
        self.strategy = strategy
        self.stack = 100.0  # BB
        self.stats = defaultdict(int)
        self.profit = 0.0
    
    def decide_open(self, hand, position):
        """Decide whether to open raise"""
        if position == 'BB':
            return False  # BB doesn't open
        open_range = self.strategy['open'].get(position, set())
        return hand in open_range
    
    def decide_vs_open(self, hand, opener_pos, my_pos):
        """Decide action vs an open: 3bet, call, or fold"""
        # 3-bet value
        if hand in self.strategy['3bet_value']:
            return '3bet'
        # 3-bet bluff (only vs late position)
        if opener_pos in ['CO', 'BTN'] and hand in self.strategy['3bet_bluff']:
            if random.random() < 0.4:  # Don't always bluff
                return '3bet'
        
        # Fish calls way too wide
        if self.strategy.get('call_open_wide'):
            strength = HAND_STRENGTH.get(hand, 30)
            if strength > 35:  # Calls with almost anything
                return 'call'
        
        # Normal call logic (call with medium strength hands IP)
        if my_pos in ['BTN', 'CO', 'BB']:
            strength = HAND_STRENGTH.get(hand, 30)
            if strength > 55:
                return 'call'
        return 'fold'
    
    def decide_vs_3bet(self, hand):
        """Decide action vs a 3-bet: 4bet, call, or fold"""
        if hand in self.strategy['4bet']:
            return '4bet'
        
        # Nit folds too much to 3-bets
        if self.strategy.get('fold_to_3bet_wide'):
            if hand in self.strategy['call_3bet']:
                return 'call'
            return 'fold'
        
        if hand in self.strategy['call_3bet']:
            return 'call'
        return 'fold'

def simulate_hand(players, dealer_pos):
    """Simulate one hand of poker, return profit/loss for each player"""
    deck = make_deck()
    random.shuffle(deck)
    
    # Deal hands
    hands = {}
    for i, p in enumerate(players):
        cards = (deck.pop(), deck.pop())
        hands[p.name] = hand_to_str(cards)
    
    # Positions
    positions = {}
    for i, pos in enumerate(POSITIONS):
        idx = (dealer_pos + i + 1) % 6
        positions[players[idx].name] = pos
    
    # Track money invested by each player
    invested = {p.name: 0.0 for p in players}
    
    # Post blinds
    sb_player = [p for p in players if positions[p.name] == 'SB'][0]
    bb_player = [p for p in players if positions[p.name] == 'BB'][0]
    invested[sb_player.name] = 0.5
    invested[bb_player.name] = 1.0
    
    # Preflop action
    active = {p.name: True for p in players}
    opener = None
    open_size = 2.5
    three_bettor = None
    three_bet_size = 8.0
    
    # Action order: UTG, MP, CO, BTN, SB, BB
    action_order = []
    for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
        for p in players:
            if positions[p.name] == pos:
                action_order.append(p)
                break
    
    # First orbit - opens and 3-bets
    for p in action_order:
        if not active[p.name]:
            continue
        
        hand = hands[p.name]
        pos = positions[p.name]
        p.stats['hands'] += 1
        
        if opener is None:
            # No open yet
            if p.decide_open(hand, pos):
                opener = p
                invested[p.name] = open_size
                p.stats['opens'] += 1
                p.stats['vpip'] += 1
                p.stats['pfr'] += 1
            else:
                if pos != 'BB':
                    active[p.name] = False
        else:
            # Facing an open
            action = p.decide_vs_open(hand, positions[opener.name], pos)
            if action == '3bet':
                three_bettor = p
                invested[p.name] = three_bet_size
                p.stats['3bets'] += 1
                p.stats['vpip'] += 1
                p.stats['pfr'] += 1
            elif action == 'call':
                invested[p.name] = open_size
                p.stats['vpip'] += 1
                p.stats['calls'] += 1
            else:
                active[p.name] = False
    
    # Handle 3-bet response
    if three_bettor and opener:
        hand = hands[opener.name]
        action = opener.decide_vs_3bet(hand)
        if action == '4bet':
            invested[opener.name] = 20.0
            opener.stats['4bets'] += 1
        elif action == 'call':
            invested[opener.name] = three_bet_size
        else:
            active[opener.name] = False
            opener.stats['fold_to_3bet'] += 1
    
    # Calculate pot
    pot = sum(invested.values())
    
    # Determine winners
    active_players = [p for p in players if active[p.name]]
    
    if len(active_players) == 1:
        # Everyone else folded - winner takes pot
        winner = active_players[0]
        winner.stats['steals'] += 1
        # Profit = pot minus what winner invested
        for p in players:
            if p == winner:
                p.profit += pot - invested[p.name]
            else:
                p.profit -= invested[p.name]
        return
    
    if len(active_players) == 0:
        # Edge case: everyone folded (shouldn't happen, BB always active)
        for p in players:
            p.profit -= invested[p.name]
        bb_player.profit += pot
        return
    
    # Showdown (use hand strength + position + variance)
    showdown_players = active_players
    strengths = {}
    for p in showdown_players:
        hand = hands[p.name]
        base = HAND_STRENGTH.get(hand, 40)
        # Position bonus (IP realizes more equity)
        pos = positions[p.name]
        pos_bonus = {'BTN': 8, 'CO': 5, 'MP': 2, 'UTG': 0, 'SB': -3, 'BB': 2}
        # Aggressor bonus (3-bettor has initiative)
        agg_bonus = 5 if p == three_bettor else (3 if p == opener else 0)
        strengths[p.name] = base + pos_bonus.get(pos, 0) + agg_bonus + random.gauss(0, 12)
    
    # Winner takes pot
    winner = max(showdown_players, key=lambda p: strengths[p.name])
    winner.stats['wins'] += 1
    
    for p in players:
        if p == winner:
            p.profit += pot - invested[p.name]
        else:
            p.profit -= invested[p.name]

def run_simulation(num_hands=10000):
    """Run simulation with all strategies"""
    # Create players
    strategy_names = list(STRATEGIES.keys())[:6]  # Use first 6 for 6-max
    players = [Player(name, STRATEGIES[name]) for name in strategy_names]
    
    print(f"Simulating {num_hands} hands with strategies:")
    for p in players:
        print(f"  - {p.name}")
    print()
    
    # Run hands
    for i in range(num_hands):
        dealer_pos = i % 6
        simulate_hand(players, dealer_pos)
        
        if (i + 1) % 2000 == 0:
            print(f"  {i+1} hands completed...")
    
    # Results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    
    # Sort by profit
    players.sort(key=lambda p: p.profit, reverse=True)
    
    print(f"\n{'Strategy':<15} {'Profit':>10} {'BB/100':>10} {'VPIP':>8} {'PFR':>8} {'3bet%':>8} {'Steals':>8}")
    print("-"*70)
    
    for p in players:
        hands = p.stats['hands']
        bb_per_100 = (p.profit / hands) * 100 if hands > 0 else 0
        vpip = (p.stats['vpip'] / hands) * 100 if hands > 0 else 0
        pfr = (p.stats['pfr'] / hands) * 100 if hands > 0 else 0
        three_bet = (p.stats['3bets'] / hands) * 100 if hands > 0 else 0
        
        print(f"{p.name:<15} {p.profit:>+10.1f} {bb_per_100:>+10.2f} {vpip:>7.1f}% {pfr:>7.1f}% {three_bet:>7.1f}% {p.stats['steals']:>8}")
    
    print("\n" + "="*70)
    print("RANKING")
    print("="*70)
    for i, p in enumerate(players, 1):
        bb_per_100 = (p.profit / p.stats['hands']) * 100
        print(f"{i}. {p.name}: {bb_per_100:+.2f} BB/100")

def run_all_strategies(num_hands=5000):
    """Run simulation with all 8 strategies across multiple tables"""
    random.seed(42)  # Fixed seed for reproducibility
    
    strategy_names = list(STRATEGIES.keys())
    
    print(f"Running {num_hands} hands per table")
    print(f"All 8 strategies compete across multiple 6-max tables\n")
    
    # Track cumulative results
    total_profit = {name: 0.0 for name in strategy_names}
    total_hands = {name: 0 for name in strategy_names}
    total_stats = {name: defaultdict(int) for name in strategy_names}
    
    # Run tables with different 6-player combinations
    # Each strategy plays against each other strategy
    from itertools import combinations
    combos = list(combinations(strategy_names, 6))
    hands_per_table = num_hands // len(combos)
    
    for combo in combos:
        players = [Player(name, STRATEGIES[name]) for name in combo]
        
        for i in range(hands_per_table):
            dealer_pos = i % 6
            simulate_hand(players, dealer_pos)
        
        for p in players:
            total_profit[p.name] += p.profit
            total_hands[p.name] += p.stats['hands']
            for k, v in p.stats.items():
                total_stats[p.name][k] += v
    
    # Results
    print("="*80)
    print("RESULTS (All 8 Strategies)")
    print("="*80)
    
    results = []
    for name in strategy_names:
        hands = total_hands[name]
        profit = total_profit[name]
        bb_per_100 = (profit / hands) * 100 if hands > 0 else 0
        vpip = (total_stats[name]['vpip'] / hands) * 100 if hands > 0 else 0
        pfr = (total_stats[name]['pfr'] / hands) * 100 if hands > 0 else 0
        three_bet = (total_stats[name]['3bets'] / hands) * 100 if hands > 0 else 0
        steals = total_stats[name]['steals']
        results.append((name, profit, bb_per_100, vpip, pfr, three_bet, steals, hands))
    
    results.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n{'Strategy':<15} {'Profit':>10} {'BB/100':>10} {'VPIP':>8} {'PFR':>8} {'3bet%':>8} {'Steals':>8}")
    print("-"*80)
    
    for name, profit, bb100, vpip, pfr, three_bet, steals, hands in results:
        print(f"{name:<15} {profit:>+10.1f} {bb100:>+10.2f} {vpip:>7.1f}% {pfr:>7.1f}% {three_bet:>7.1f}% {steals:>8}")
    
    total = sum(r[1] for r in results)
    print(f"\nTotal profit sum: {total:.2f} (should be ~0)")
    
    print("\n" + "="*80)
    print("FINAL RANKING")
    print("="*80)
    for i, (name, profit, bb100, *_) in enumerate(results, 1):
        status = "WINNER" if profit > 0 else "LOSER"
        print(f"{i}. {name}: {profit:+.1f} BB ({bb100:+.2f} BB/100) [{status}]")

if __name__ == '__main__':
    import sys
    
    num_hands = 100000
    if len(sys.argv) > 1:
        num_hands = int(sys.argv[1])
    
    print("="*80)
    print("POKER STRATEGY SIMULATOR")
    print("="*80)
    print(flush=True)
    
    # Strategies to test (bots)
    bot_strategies = ['kiro_v2', 'sonnet', 'kiro_optimal', 'kiro5', 'gpt4', 'gpt3', 'opus2']
    # Simulated player archetypes
    player_archetypes = ['fish', 'nit', 'lag', 'tag']
    
    print(f"Testing {len(bot_strategies)} bot strategies against player archetypes")
    print(f"Bots: {', '.join(bot_strategies)}")
    print(f"Players: {', '.join(player_archetypes)}")
    print(f"REALISTIC ZOOM 2NL-5NL: ~40% fish, ~25% nit/tag, ~10% LAG")
    print(f"Avg table: 2-3 fish, 1-2 nit/tag, 0-1 LAG, 1 bot\n", flush=True)
    
    # Generate table combinations
    # REALISTIC ZOOM 2NL-5NL: ~40% fish, ~25% nit, ~25% tag, ~10% LAG
    from itertools import combinations
    
    valid_tables = []
    
    # Weight tables by frequency (more common = more entries)
    
    # === SOFT TABLES (no LAG) - 50% of tables ===
    # 3 fish + 1 nit + 1 tag + 1 bot (very soft)
    for bot in bot_strategies:
        for _ in range(3):  # 3x weight
            valid_tables.append(['fish', 'fish', 'fish', 'nit', 'tag', bot])
    
    # 2 fish + 2 nit + 1 tag + 1 bot
    for bot in bot_strategies:
        for _ in range(2):
            valid_tables.append(['fish', 'fish', 'nit', 'nit', 'tag', bot])
    
    # 2 fish + 1 nit + 2 tag + 1 bot
    for bot in bot_strategies:
        for _ in range(2):
            valid_tables.append(['fish', 'fish', 'nit', 'tag', 'tag', bot])
    
    # 2 fish + 3 nit + 1 bot (nitty soft)
    for bot in bot_strategies:
        valid_tables.append(['fish', 'fish', 'nit', 'nit', 'nit', bot])
    
    # 2 fish + 3 tag + 1 bot (reg heavy soft)
    for bot in bot_strategies:
        valid_tables.append(['fish', 'fish', 'tag', 'tag', 'tag', bot])
    
    # === TABLES WITH LAG - 40% of tables ===
    # 2 fish + 1 nit + 1 tag + 1 lag + 1 bot (standard)
    for bot in bot_strategies:
        for _ in range(3):
            valid_tables.append(['fish', 'fish', 'nit', 'tag', 'lag', bot])
    
    # 2 fish + 2 nit + 1 lag + 1 bot
    for bot in bot_strategies:
        for _ in range(2):
            valid_tables.append(['fish', 'fish', 'nit', 'nit', 'lag', bot])
    
    # 2 fish + 2 tag + 1 lag + 1 bot
    for bot in bot_strategies:
        for _ in range(2):
            valid_tables.append(['fish', 'fish', 'tag', 'tag', 'lag', bot])
    
    # 3 fish + 1 nit + 1 lag + 1 bot (soft with lag)
    for bot in bot_strategies:
        valid_tables.append(['fish', 'fish', 'fish', 'nit', 'lag', bot])
    
    # 3 fish + 1 tag + 1 lag + 1 bot
    for bot in bot_strategies:
        valid_tables.append(['fish', 'fish', 'fish', 'tag', 'lag', bot])
    
    # === TOUGH TABLES - 10% of tables ===
    # 1 fish + 2 tag + 1 nit + 1 lag + 1 bot (reg battle)
    for bot in bot_strategies:
        valid_tables.append(['fish', 'tag', 'tag', 'nit', 'lag', bot])
    
    # 1 fish + 1 tag + 2 nit + 1 lag + 1 bot
    for bot in bot_strategies:
        valid_tables.append(['fish', 'tag', 'nit', 'nit', 'lag', bot])
    
    # 1 fish + 2 tag + 2 nit + 1 bot (no lag, reg heavy)
    for bot in bot_strategies:
        valid_tables.append(['fish', 'tag', 'tag', 'nit', 'nit', bot])
    
    print(f"Generated {len(valid_tables)} valid table configurations", flush=True)
    
    # Run 3 trials
    all_results = defaultdict(list)
    all_strategies = bot_strategies + player_archetypes
    
    for trial in range(3):
        print(f"\n--- Trial {trial+1}/3 ---", flush=True)
        random.seed(trial * 1000 + 42)
        
        total_profit = {name: 0.0 for name in all_strategies}
        total_hands = {name: 0 for name in all_strategies}
        
        hands_per_table = num_hands // len(valid_tables)
        
        for idx, table_strats in enumerate(valid_tables):
            # Create players with unique names (fish_1, fish_2, etc.)
            name_counts = {}
            players = []
            for strat in table_strats:
                name_counts[strat] = name_counts.get(strat, 0) + 1
                unique_name = f"{strat}_{name_counts[strat]}" if table_strats.count(strat) > 1 else strat
                p = Player(unique_name, STRATEGIES[strat])
                p.base_strategy = strat  # Track original strategy name
                players.append(p)
            
            for i in range(hands_per_table):
                simulate_hand(players, i % 6)
            for p in players:
                strat = p.base_strategy if hasattr(p, 'base_strategy') else p.name
                total_profit[strat] += p.profit
                total_hands[strat] += p.stats['hands']
            
            # Progress every 20 tables
            if (idx + 1) % 20 == 0:
                print(f"  Table {idx+1}/{len(valid_tables)} complete...", flush=True)
        
        for name in all_strategies:
            if total_hands[name] > 0:
                bb100 = (total_profit[name] / total_hands[name]) * 100
                all_results[name].append(bb100)
        
        print(f"Trial {trial+1} complete!", flush=True)
    
    # Final results
    print("\n" + "="*80)
    print(f"FINAL RESULTS (Average of 3 trials, {num_hands} hands each)")
    print("="*80, flush=True)
    
    final = []
    for name in all_strategies:
        if all_results[name]:
            avg = sum(all_results[name]) / len(all_results[name])
            std = (sum((x - avg)**2 for x in all_results[name]) / len(all_results[name])) ** 0.5
            is_bot = name in bot_strategies
            final.append((name, avg, std, all_results[name], is_bot))
    
    final.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n{'Strategy':<15} {'Type':<8} {'Avg BB/100':>12} {'StdDev':>10} {'Trial1':>10} {'Trial2':>10} {'Trial3':>10}")
    print("-"*85)
    
    for name, avg, std, trials, is_bot in final:
        type_str = "BOT" if is_bot else "PLAYER"
        print(f"{name:<15} {type_str:<8} {avg:>+12.2f} {std:>10.2f} {trials[0]:>+10.2f} {trials[1]:>+10.2f} {trials[2]:>+10.2f}")
    
    # Bot-only ranking
    print("\n" + "="*80)
    print("BOT RANKING (strategies being tested)")
    print("="*80)
    bot_results = [(n, a, s) for n, a, s, _, is_bot in final if is_bot]
    for i, (name, avg, std) in enumerate(bot_results, 1):
        print(f"{i}. {name}: {avg:+.2f} BB/100 (+/- {std:.2f})")
