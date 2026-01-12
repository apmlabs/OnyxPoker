"""
Shared poker logic for both poker_sim.py and strategy_engine.py.
Contains hand evaluation, postflop decisions, and strategy definitions.
"""

from typing import Dict, List, Set, Tuple, Optional
import random

# Card constants
RANKS = '23456789TJQKA'
SUITS = 'shdc'
RANK_VAL = {r: i for i, r in enumerate(RANKS)}

def expand_range(range_str: str) -> Set[str]:
    """Expand range notation to set of hands."""
    hands = set()
    
    def add_pairs(start, end='A'):
        for i in range(RANK_VAL[start], RANK_VAL[end] + 1):
            hands.add(RANKS[i] + RANKS[i])
    
    def add_hands(h1, h2, suited, plus=False):
        if plus:
            start_idx = RANK_VAL[h2]
            end_idx = RANK_VAL[h1] - 1
            for i in range(start_idx, end_idx + 1):
                hands.add(h1 + RANKS[i] + ('s' if suited else 'o'))
        else:
            hands.add(h1 + h2 + ('s' if suited else 'o'))
    
    for part in range_str.replace(' ', '').split(','):
        part = part.strip()
        if not part:
            continue
        
        if len(part) == 2 and part[0] == part[1]:
            add_pairs(part[0], part[0])
        elif len(part) == 3 and part[0] == part[1] and part[2] == '+':
            add_pairs(part[0], 'A')
        elif '-' in part and len(part) == 5 and part[0] == part[1]:
            add_pairs(part[3], part[0])
        elif part.endswith('s+'):
            add_hands(part[0], part[1], True, True)
        elif part.endswith('s') and '-' not in part:
            add_hands(part[0], part[1], True, False)
        elif 's-' in part:
            h1 = part[0]
            start = part[part.index('-')+2]
            end = part[1]
            for i in range(RANK_VAL[start], RANK_VAL[end] + 1):
                hands.add(h1 + RANKS[i] + 's')
        elif part.endswith('o+'):
            add_hands(part[0], part[1], False, True)
        elif part.endswith('o'):
            add_hands(part[0], part[1], False, False)
        elif len(part) == 3 and part[2] == '+':
            add_hands(part[0], part[1], True, True)
            add_hands(part[0], part[1], False, True)
    
    return hands


# Strategy definitions - from pokerstrategy files
STRATEGIES = {
    'gpt3': {
        'name': 'GPT3 Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AJo+,AQo+'),
            'MP': expand_range('66+,ATs+,A5s-A2s,KJs+,QJs,JTs,KQo,AJo+,AQo+'),
            'CO': expand_range('55+,A8s+,A5s-A2s,KTs+,QTs+,JTs,T9s,98s,87s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,75s+,65s,54s,A2o+,KTo+,QTo+,JTo,T9o,98o'),
            'SB': expand_range('22+,A2s+,K6s+,Q7s+,J7s+,T7s+,97s+,86s+,75s+,65s,54s,ATo+,KJo+,QJo,JTo'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('JJ+,AKs,AKo,AQs'),
            'CO': expand_range('TT+,AJs+,AQo+,KQs'),
            'BTN': expand_range('TT+,AJs+,AQo+,KQs'),
        },
        '3bet_bluff': expand_range('A5s-A2s'),
        'call_open_ip': expand_range('99-22,AQs-AJs,KQs,QJs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('99-22,A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,86s+,75s+,65s,54s,A8o+,KTo+,QTo+,JTo,T9o,98o'),
        'call_3bet': expand_range('JJ,TT,AQs,AKo,KQs'),
        '4bet': expand_range('QQ+,AKs,AKo'),
    },
    'gpt4': {
        'name': 'GPT4 Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AJo+,AQo+'),
            'MP': expand_range('66+,ATs+,A5s-A2s,KJs+,QJs,JTs,KQo,AJo+,AQo+'),
            'CO': expand_range('55+,A8s+,A5s-A2s,KTs+,QTs+,JTs,T9s,98s,87s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,75s+,65s,54s,A2o+,KTo+,QTo+,JTo,T9o,98o'),
            'SB': expand_range('22+,A2s+,K6s+,Q7s+,J7s+,T7s+,97s+,86s+,75s+,65s,54s,ATo+,KJo+,QJo,JTo'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('JJ+,AKs,AKo,AQs'),
            'CO': expand_range('TT+,AJs+,AQo+,KQs'),
            'BTN': expand_range('TT+,AJs+,AQo+,KQs'),
        },
        '3bet_bluff': expand_range('A5s-A2s,KTs-K9s'),
        'call_open_ip': expand_range('99-22,AQs-AJs,KQs,QJs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,86s+,75s+,65s,54s,A8o+,KTo+,QTo+,JTo,T9o,98o'),
        'call_3bet': expand_range('JJ,TT,AQs,AKo,KQs'),
        '4bet': expand_range('QQ+,AKs,AKo'),
    },
    'sonnet': {
        'name': 'Sonnet Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A2s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K6s+,Q7s+,J7s+,T7s+,96s+,85s+,75s+,64s+,54s,A7o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('QQ+,AKs,AKo'),
            'CO': expand_range('JJ+,AQs+,AKo'),
            'BTN': expand_range('TT+,AQs+,AKo'),
        },
        '3bet_bluff': expand_range('A5s-A4s,K9s-K8s'),
        'call_open_ip': expand_range('JJ-66,AJs-ATs,KQs-KJs,QJs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('99-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,54s,A9o+,KJo,QJo,JTo'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'kiro_optimal': {
        'name': 'Kiro Optimal Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A2s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T7s+,96s+,85s+,75s+,64s+,54s,A7o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('QQ+,AKs,AKo'),
            'CO': expand_range('JJ+,AQs+,AKo'),
            'BTN': expand_range('TT+,AQs+,AKo'),
        },
        '3bet_bluff': expand_range('A5s-A4s,K9s'),
        'call_open_ip': expand_range('JJ-66,AJs-ATs,KQs-KJs,QJs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('99-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,54s,A9o+,KJo,QJo'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
}

# Player archetypes
STRATEGIES['fish'] = {
    'name': 'Fish',
    'open': {
        'UTG': expand_range('88+,ATs+,KQs,AJo+'),
        'MP': expand_range('77+,A9s+,KJs+,QJs,ATo+,KQo'),
        'CO': expand_range('66+,A7s+,KTs+,QTs+,JTs,ATo+,KJo+'),
        'BTN': expand_range('55+,A5s+,K9s+,Q9s+,J9s+,T9s,98s,A9o+,KTo+,QJo'),
        'SB': expand_range('66+,A7s+,K9s+,Q9s+,JTs,A9o+,KJo+'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs'), 'MP': expand_range('QQ+,AKs'), 'CO': expand_range('QQ+,AKs'), 'BTN': expand_range('QQ+,AKs')},
    '3bet_bluff': set(),
    'call_open_ip': expand_range('22+,A2s+,K5s+,Q7s+,J8s+,T8s+,97s+,87s,76s,65s,A5o+,K9o+,QTo+,JTo'),
    'bb_defend': expand_range('22+,A2s+,K5s+,Q7s+,J8s+,T8s+,97s+,87s,76s,65s,A5o+,K9o+,QTo+,JTo,T9o'),
    'call_3bet': expand_range('QQ,JJ,TT,AKs,AKo,AQs,AQo,AJs,KQs'),
    '4bet': expand_range('AA,KK'),
    'call_wide': True,
}

STRATEGIES['nit'] = {
    'name': 'Nit',
    'open': {
        'UTG': expand_range('TT+,AQs+,AKo'),
        'MP': expand_range('99+,AJs+,KQs,AQo+'),
        'CO': expand_range('88+,ATs+,KQs,AJo+,KQo'),
        'BTN': expand_range('77+,A9s+,KJs+,QJs,ATo+,KJo+'),
        'SB': expand_range('88+,ATs+,KQs,AJo+'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs'), 'MP': expand_range('QQ+,AKs'), 'CO': expand_range('QQ+,AKs,AKo'), 'BTN': expand_range('QQ+,AKs,AKo')},
    '3bet_bluff': set(),
    'call_open_ip': expand_range('JJ-88,AQs-AJs,KQs'),
    'bb_defend': expand_range('TT-66,AQs-ATs,KQs,QJs,JTs'),
    'call_3bet': expand_range('QQ,AKs'),
    '4bet': expand_range('KK+'),
    'fold_wide': True,
}

STRATEGIES['lag'] = {
    'name': 'LAG',
    'open': {
        'UTG': expand_range('66+,A9s+,A5s-A2s,KTs+,QTs+,JTs,ATo+,KQo'),
        'MP': expand_range('55+,A7s+,A5s-A2s,K9s+,Q9s+,J9s+,T9s,98s,ATo+,KJo+,QJo'),
        'CO': expand_range('33+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,54s,A8o+,KTo+,QTo+,JTo'),
        'BTN': expand_range('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,96s+,85s+,74s+,64s+,53s+,A5o+,K8o+,Q9o+,J9o+,T9o'),
        'SB': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,A7o+,K9o+,QTo+'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo,JJ'), 'MP': expand_range('JJ+,AKs,AKo,AQs,TT'), 'CO': expand_range('TT+,AQs+,AKo,AJs'), 'BTN': expand_range('TT+,AQs+,AKo,AJs,KQs')},
    '3bet_bluff': expand_range('A5s-A2s,K9s-K7s,Q9s,J9s,T9s,98s,87s,76s'),
    'call_open_ip': expand_range('TT-22,AJs-A7s,KQs-KTs,QJs-QTs,JTs,T9s,98s,87s,76s'),
    'bb_defend': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,54s,A7o+,KTo+,QTo+,JTo,T9o'),
    'call_3bet': expand_range('JJ,TT,AKo,AQs,AQo,KQs'),
    '4bet': expand_range('QQ+,AKs'),
}

STRATEGIES['tag'] = {
    'name': 'TAG',
    'open': {
        'UTG': expand_range('77+,ATs+,KQs,AQo+'),
        'MP': expand_range('66+,A9s+,KJs+,QJs,JTs,AJo+,KQo'),
        'CO': expand_range('55+,A7s+,K9s+,Q9s+,J9s+,T9s,98s,ATo+,KJo+,QJo'),
        'BTN': expand_range('22+,A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,87s,76s,65s,A9o+,KTo+,QJo'),
        'SB': expand_range('55+,A5s+,K9s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KJo+'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo'), 'MP': expand_range('QQ+,AKs,AKo'), 'CO': expand_range('JJ+,AQs+,AKo'), 'BTN': expand_range('TT+,AQs+,AKo')},
    '3bet_bluff': expand_range('A5s-A4s'),
    'call_open_ip': expand_range('JJ-55,AQs-ATs,KQs-KJs,QJs,JTs,T9s,98s'),
    'bb_defend': expand_range('TT-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A9o+,KJo,QJo'),
    'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
    '4bet': expand_range('KK+,AKs'),
}


# Hand evaluation
def hand_to_str(cards: List[Tuple[str, str]]) -> str:
    """Convert 2 card tuples to hand notation like 'AKs' or 'AKo'."""
    c1, c2 = sorted(cards, key=lambda x: RANK_VAL[x[0]], reverse=True)
    r1, s1 = c1
    r2, s2 = c2
    if r1 == r2:
        return r1 + r2
    elif s1 == s2:
        return r1 + r2 + 's'
    else:
        return r1 + r2 + 'o'


def parse_card(card: str) -> Tuple[str, str]:
    """Parse card string like 'As' to ('A', 's')."""
    if not card or len(card) < 2:
        return (None, None)
    rank = card[:-1].upper()
    suit = card[-1].lower()
    if rank == '10':
        rank = 'T'
    return (rank, suit)


def evaluate_hand(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]]) -> Tuple[int, str, int]:
    """
    Evaluate 5-7 card hand. Returns (rank, description, kicker_value).
    Rank: 9=straight flush, 8=quads, 7=full house, 6=flush, 5=straight,
          4=trips/set, 3=two pair, 2=pair, 1=high card
    """
    all_cards = hole_cards + board
    if len(all_cards) < 5:
        return (0, "incomplete", 0)
    
    ranks = [c[0] for c in all_cards]
    suits = [c[1] for c in all_cards]
    hero_ranks = set(c[0] for c in hole_cards)
    
    rank_counts = {}
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1
    
    suit_counts = {}
    for s in suits:
        suit_counts[s] = suit_counts.get(s, 0) + 1
    
    # Check flush
    flush_suit = None
    for s, count in suit_counts.items():
        if count >= 5:
            flush_suit = s
    
    # Check straight
    rank_set = set(RANK_VAL[r] for r in ranks)
    if 12 in rank_set:
        rank_set.add(-1)
    
    straight_high = None
    for i in range(8, -2, -1):
        if all(j in rank_set for j in range(i, i+5)):
            straight_high = i + 4
            break
    
    # Straight flush
    if flush_suit and straight_high is not None:
        flush_ranks = set(RANK_VAL[c[0]] for c in all_cards if c[1] == flush_suit)
        if 12 in flush_ranks:
            flush_ranks.add(-1)
        for i in range(8, -2, -1):
            if all(j in flush_ranks for j in range(i, i+5)):
                return (9, "straight flush", i+4)
    
    # Four of a kind
    for r, count in rank_counts.items():
        if count >= 4:
            return (8, f"quads {r}s", RANK_VAL[r])
    
    # Full house
    trips = [r for r, c in rank_counts.items() if c >= 3]
    pairs = [r for r, c in rank_counts.items() if c >= 2]
    if trips and len(pairs) >= 2:
        return (7, "full house", RANK_VAL[trips[0]])
    
    # Flush
    if flush_suit:
        flush_cards = sorted([RANK_VAL[c[0]] for c in all_cards if c[1] == flush_suit], reverse=True)
        return (6, "flush", flush_cards[0])
    
    # Straight
    if straight_high is not None:
        return (5, "straight", straight_high)
    
    # Three of a kind
    if trips:
        is_set = trips[0] in hero_ranks and len(hero_ranks) == 1
        return (4, f"set of {trips[0]}s" if is_set else f"trips {trips[0]}s", RANK_VAL[trips[0]])
    
    # Two pair
    pair_ranks = sorted([r for r, c in rank_counts.items() if c >= 2], key=lambda r: RANK_VAL[r], reverse=True)
    if len(pair_ranks) >= 2:
        return (3, "two pair", RANK_VAL[pair_ranks[0]])
    
    # One pair
    if pair_ranks:
        pr = pair_ranks[0]
        board_ranks = [c[0] for c in board] if board else []
        board_vals = sorted([RANK_VAL[r] for r in board_ranks], reverse=True)
        
        if pr in hero_ranks:
            if board_vals and RANK_VAL[pr] >= board_vals[0]:
                kicker = max(RANK_VAL[r] for r in hero_ranks if r != pr) if len(hero_ranks) > 1 else 0
                if kicker >= RANK_VAL['T']:
                    return (2, "top pair good kicker", RANK_VAL[pr] * 100 + kicker)
                return (2, "top pair weak kicker", RANK_VAL[pr] * 100 + kicker)
            elif board_vals and len(board_vals) > 1 and RANK_VAL[pr] >= board_vals[1]:
                return (2, "middle pair", RANK_VAL[pr])
            return (2, "bottom pair", RANK_VAL[pr])
        return (2, "pair", RANK_VAL[pr])
    
    # High card
    high = max(RANK_VAL[r] for r in ranks)
    return (1, "high card", high)


def check_draws(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]]) -> List[str]:
    """Check for flush and straight draws."""
    draws = []
    if len(board) < 3:
        return draws
    
    all_cards = hole_cards + board
    suits = [c[1] for c in all_cards]
    
    suit_counts = {}
    for s in suits:
        suit_counts[s] = suit_counts.get(s, 0) + 1
    
    for s, count in suit_counts.items():
        if count == 4:
            draws.append("flush_draw")
            break
    
    ranks = set(RANK_VAL[c[0]] for c in all_cards)
    if 12 in ranks:
        ranks.add(-1)
    
    for i in range(-1, 10):
        window = set(range(i, i+5))
        in_window = len(window & ranks)
        if in_window == 4:
            missing = window - ranks
            if missing:
                m = list(missing)[0]
                if m == i or m == i+4:
                    draws.append("oesd")
                else:
                    draws.append("gutshot")
            break
    
    return draws


# Postflop decision logic - matches strategy files exactly
def postflop_action(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]], 
                    pot: float, to_call: float, street: str, is_ip: bool,
                    is_aggressor: bool, archetype: str = None) -> Tuple[str, float, str]:
    """
    Postflop decision based on strategy file rules.
    Returns (action, bet_size, reasoning).
    archetype: 'fish', 'nit', 'tag', 'lag' for special behavior
    """
    strength, desc, kicker = evaluate_hand(hole_cards, board)
    draws = check_draws(hole_cards, board)
    
    has_flush_draw = "flush_draw" in draws
    has_oesd = "oesd" in draws
    has_gutshot = "gutshot" in draws
    combo_draw = has_flush_draw and (has_oesd or has_gutshot)
    has_any_draw = has_flush_draw or has_oesd or has_gutshot
    has_pair = strength >= 2
    
    # FISH: Calls with any pair/draw, never folds top pair, stations
    if archetype == 'fish':
        if to_call == 0 or to_call is None:
            if strength >= 3:  # Two pair+
                return ('bet', round(pot * 0.5, 2), f"{desc} - fish bets small")
            return ('check', 0, "fish checks")
        else:
            # Fish calls with any pair or draw
            if has_pair or has_any_draw:
                return ('call', 0, f"{desc} - fish calls")
            return ('fold', 0, "fish folds air")
    
    # NIT: Only continues top pair+, folds to aggression, never bluffs
    if archetype == 'nit':
        if to_call == 0 or to_call is None:
            if strength >= 4:  # Set+
                return ('bet', round(pot * 0.65, 2), f"{desc} - nit value bets")
            if strength == 3 or "top pair" in desc:
                return ('bet', round(pot * 0.5, 2), f"{desc} - nit bets")
            return ('check', 0, "nit checks weak hand")
        else:
            # Nit folds to aggression without strong hand
            if strength >= 4:  # Set+
                return ('call', 0, f"{desc} - nit calls")
            if strength == 3 and street == 'flop':
                return ('call', 0, f"{desc} - nit calls flop")
            if "top pair good kicker" in desc and street == 'flop':
                return ('call', 0, f"{desc} - nit calls flop")
            return ('fold', 0, f"{desc} - nit folds to aggression")
    
    # TAG: C-bets 65%, gives up without equity, folds to raises
    if archetype == 'tag':
        if to_call == 0 or to_call is None:
            if strength >= 3:  # Two pair+
                return ('bet', round(pot * 0.65, 2), f"{desc} - tag value bets")
            if "top pair" in desc or "pair" in desc:
                if street == 'flop' and random.random() < 0.65:
                    return ('bet', round(pot * 0.5, 2), f"{desc} - tag c-bets")
                if street == 'turn' and strength >= 2 and "top" in desc:
                    return ('bet', round(pot * 0.55, 2), f"{desc} - tag barrels")
            if combo_draw and street == 'flop':
                return ('bet', round(pot * 0.5, 2), "tag semi-bluffs draw")
            return ('check', 0, f"{desc} - tag checks")
        else:
            if strength >= 4:
                return ('call', 0, f"{desc} - tag calls")
            if strength == 3 and street != 'river':
                return ('call', 0, f"{desc} - tag calls")
            if "top pair" in desc and street == 'flop':
                return ('call', 0, f"{desc} - tag calls flop")
            return ('fold', 0, f"{desc} - tag folds")
    
    # LAG: C-bets 75%, double barrels, bluffs rivers
    if archetype == 'lag':
        if to_call == 0 or to_call is None:
            if strength >= 3:
                return ('bet', round(pot * 0.75, 2), f"{desc} - lag value bets big")
            if "pair" in desc:
                if street in ['flop', 'turn'] and random.random() < 0.75:
                    return ('bet', round(pot * 0.6, 2), f"{desc} - lag barrels")
            if has_any_draw:
                return ('bet', round(pot * 0.65, 2), "lag semi-bluffs")
            if street == 'flop' and random.random() < 0.70:
                return ('bet', round(pot * 0.5, 2), "lag c-bets air")
            if street == 'river' and random.random() < 0.25:
                return ('bet', round(pot * 0.6, 2), "lag river bluff")
            return ('check', 0, f"{desc} - lag checks")
        else:
            if strength >= 3:
                return ('call', 0, f"{desc} - lag calls")
            if "pair" in desc and street != 'river':
                return ('call', 0, f"{desc} - lag floats")
            if has_flush_draw or has_oesd:
                return ('call', 0, "lag calls with draw")
            return ('fold', 0, f"{desc} - lag folds")
    
    # DEFAULT (bot strategies) - original logic
    s = {
        'flop': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.80, 'tptk': 0.75, 'tpgk': 0.70, 'tpwk': 0.65},
        'turn': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.80, 'tptk': 0.70, 'tpgk': 0.60, 'tpwk': 0.0},
        'river': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.80, 'tptk': 0.60, 'tpgk': 0.50, 'tpwk': 0.0},
    }.get(street, {})
    
    if to_call == 0 or to_call is None:
        if strength >= 5:
            return ('bet', round(pot * s.get('nuts', 1.0), 2), f"{desc} - bet 100%")
        if strength == 4:
            return ('bet', round(pot * s.get('set', 0.85), 2), f"{desc} - bet 85%")
        if strength == 3:
            return ('bet', round(pot * s.get('twopair', 0.80), 2), f"{desc} - bet 80%")
        if "top pair good kicker" in desc:
            return ('bet', round(pot * s.get('tptk', 0.75), 2), f"{desc} - value bet")
        if "top pair weak kicker" in desc and street == 'flop':
            return ('bet', round(pot * s.get('tpwk', 0.65), 2), f"{desc} - bet flop")
        if combo_draw:
            return ('bet', round(pot * 0.70, 2), "combo draw - semi-bluff")
        return ('check', 0, f"{desc} - check")
    
    # Facing bet - default logic (from strategy files)
    # TPTK: 2-3 streets of value, call down
    # Two pair: call all streets except big river raises
    # Sets+: always call/raise
    if strength >= 5:
        return ('call', 0, f"{desc} - call")
    if strength == 4:
        return ('call', 0, f"{desc} - call")
    if strength == 3:
        return ('call', 0, f"{desc} - call")
    if "top pair good kicker" in desc:
        # TPTK calls flop and turn, folds to big river bets
        if street in ['flop', 'turn']:
            return ('call', 0, f"{desc} - call {street}")
        # River: call small, fold big
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.40:
            return ('call', 0, f"{desc} - call small river")
        return ('fold', 0, f"{desc} - fold big river bet")
    if "top pair" in desc:
        # Weak kicker: call flop only
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        return ('fold', 0, f"{desc} - fold {street}")
    if "pair" in desc and street == 'flop':
        return ('call', 0, f"{desc} - call flop")
    if has_flush_draw:
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.40:
            return ('call', 0, "flush draw - call")
    if has_oesd:
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.33:
            return ('call', 0, "OESD - call")
    return ('fold', 0, f"{desc} - fold")


# Preflop decision logic
def preflop_action(hand: str, position: str, strategy: Dict, 
                   facing: str, opener_pos: str = None) -> Tuple[str, str]:
    """
    Preflop decision based on strategy.
    facing: 'none', 'open', '3bet', '4bet'
    Returns (action, reasoning).
    """
    if position not in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
        position = 'BTN'
    
    # RFI
    if facing == 'none':
        if position == 'BB':
            return ('check', 'BB checks')
        open_range = strategy['open'].get(position, set())
        if hand in open_range:
            return ('raise', f'{hand} in {position} open range')
        return ('fold', f'{hand} not in {position} open range')
    
    # Facing open
    if facing == 'open':
        # 3-bet value
        three_bet_range = strategy.get('3bet_vs', {}).get(opener_pos, set())
        if hand in three_bet_range:
            return ('raise', f'{hand} 3-bet vs {opener_pos}')
        
        # 3-bet bluff
        if opener_pos in ['CO', 'BTN'] and hand in strategy.get('3bet_bluff', set()):
            if random.random() < 0.4:
                return ('raise', f'{hand} 3-bet bluff vs {opener_pos}')
        
        # Call IP
        if position in ['CO', 'BTN', 'BB']:
            if position == 'BB' and hand in strategy.get('bb_defend', set()):
                return ('call', f'{hand} BB defend')
            if hand in strategy.get('call_open_ip', set()):
                return ('call', f'{hand} call IP')
            # Fish calls wide
            if strategy.get('call_wide') and hand in strategy.get('bb_defend', set()):
                return ('call', f'{hand} call wide')
        
        return ('fold', f'{hand} fold vs open')
    
    # Facing 3-bet
    if facing == '3bet':
        if hand in strategy.get('4bet', set()):
            return ('raise', f'{hand} 4-bet')
        if hand in strategy.get('call_3bet', set()):
            return ('call', f'{hand} call 3-bet')
        if strategy.get('fold_wide'):
            return ('fold', f'{hand} nit folds to 3-bet')
        return ('fold', f'{hand} fold to 3-bet')
    
    # Facing 4-bet
    if facing == '4bet':
        if hand in expand_range('KK+'):
            return ('raise', f'{hand} 5-bet jam')
        if hand in expand_range('QQ,AKs'):
            return ('call', f'{hand} call 4-bet')
        return ('fold', f'{hand} fold to 4-bet')
    
    return ('fold', 'default fold')
