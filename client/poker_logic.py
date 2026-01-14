"""
Shared poker logic for both poker_sim.py and strategy_engine.py.
Contains hand evaluation, postflop decisions, and strategy definitions.
"""

from typing import Dict, List, Set, Tuple, Optional
import random
from itertools import combinations

# Card constants
RANKS = '23456789TJQKA'
SUITS = 'shdc'
RANK_VAL = {r: i for i, r in enumerate(RANKS)}


# =============================================================================
# HAND ANALYSIS HELPERS - Compute properties directly from cards, not strings
# =============================================================================

def analyze_hand(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]]) -> dict:
    """
    Analyze hand properties directly from cards.
    Returns dict with all relevant hand info for decision making.
    """
    from collections import Counter
    
    if not hole_cards or len(hole_cards) != 2:
        return {'valid': False}
    
    hero_ranks = [c[0] for c in hole_cards]
    hero_vals = sorted([RANK_VAL[r] for r in hero_ranks], reverse=True)
    board_ranks = [c[0] for c in board] if board else []
    board_vals = sorted([RANK_VAL[r] for r in board_ranks], reverse=True) if board else []
    
    # Is hero holding a pocket pair?
    is_pocket_pair = hero_ranks[0] == hero_ranks[1]
    pocket_val = hero_vals[0] if is_pocket_pair else None
    
    # Board pair detection
    board_rank_counts = Counter(board_ranks)
    board_pairs = [r for r, c in board_rank_counts.items() if c >= 2]
    board_trips = [r for r, c in board_rank_counts.items() if c >= 3]
    has_board_pair = len(board_pairs) > 0
    board_pair_val = max(RANK_VAL[r] for r in board_pairs) if board_pairs else None
    
    # All cards combined
    all_ranks = hero_ranks + board_ranks
    all_rank_counts = Counter(all_ranks)
    
    # What pairs/trips/quads do we have? (must include at least one hero card for pairs)
    # Exception: board pairs count for two pair detection
    hero_pairs = [r for r, c in all_rank_counts.items() if c >= 2 and r in hero_ranks]
    board_pair_ranks = [r for r, c in Counter(board_ranks).items() if c >= 2]
    our_pairs = list(set(hero_pairs + board_pair_ranks))  # Combine hero pairs + board pairs
    our_trips = [r for r, c in all_rank_counts.items() if c >= 3 and r in hero_ranks]
    our_quads = [r for r, c in all_rank_counts.items() if c >= 4]
    
    # Does hero actually have a pair (not just board paired)?
    hero_has_pair = len(hero_pairs) > 0
    
    # Did hero's cards hit the board?
    hero_hit_board = [r for r in hero_ranks if r in board_ranks]
    
    # Overpair: pocket pair higher than all board cards
    is_overpair = is_pocket_pair and board_vals and pocket_val > max(board_vals)
    
    # Underpair to ace: pocket pair but ace on board
    has_ace_on_board = 'A' in board_ranks
    is_underpair_to_ace = is_pocket_pair and has_ace_on_board and pocket_val < 12
    
    # Top pair detection
    top_board_val = board_vals[0] if board_vals else None
    has_top_pair = top_board_val is not None and any(RANK_VAL[r] == top_board_val for r in hero_ranks)
    
    # Kicker for top pair
    if has_top_pair:
        other_ranks = [RANK_VAL[r] for r in hero_ranks if RANK_VAL[r] != top_board_val]
        kicker_val = max(other_ranks) if other_ranks else hero_vals[0]
        has_good_kicker = kicker_val >= 9  # T or higher
    else:
        kicker_val = None
        has_good_kicker = False
    
    # Two pair analysis
    num_pairs = len(our_pairs)
    has_two_pair = num_pairs >= 2
    
    # Two pair type (only if we have two pair)
    two_pair_type = None
    if has_two_pair:
        if is_pocket_pair and has_board_pair:
            # Pocket pair + board pair
            if pocket_val > board_pair_val:
                two_pair_type = 'pocket_over_board'  # KK on JJ = strong
            else:
                two_pair_type = 'pocket_under_board'  # 66 on JJ = weak
        elif len(hero_hit_board) == 2:
            two_pair_type = 'both_cards_hit'  # A7 on A72 = strong
        elif has_board_pair:
            two_pair_type = 'one_card_board_pair'  # K2 on K22 = depends on board pair rank
    
    # Set detection
    has_set = len(our_trips) > 0 and is_pocket_pair  # Set = pocket pair hit board
    has_trips = len(our_trips) > 0 and not is_pocket_pair  # Trips = board pair + one card
    
    # Any pair at all (hero must have at least one card in a pair)
    has_any_pair = hero_has_pair
    
    # Middle/bottom pair detection
    has_middle_pair = False
    has_bottom_pair = False
    if has_any_pair and not has_top_pair and not is_overpair and len(board_vals) >= 2:
        for r in hero_ranks:
            rv = RANK_VAL[r]
            if r in board_ranks:
                if rv == board_vals[1]:  # Second highest board card
                    has_middle_pair = True
                elif rv == min(board_vals):  # Lowest board card
                    has_bottom_pair = True
    
    # Flush draw detection
    hero_suits = [c[1] for c in hole_cards]
    board_suits = [c[1] for c in board] if board else []
    all_suits = hero_suits + board_suits
    suit_counts = Counter(all_suits)
    has_flush_draw = any(c >= 4 for c in suit_counts.values()) and not any(c >= 5 for c in suit_counts.values())
    has_flush = any(c >= 5 for c in suit_counts.values())
    
    # Nut flush draw detection - do we have the Ace or King of the flush suit?
    is_nut_flush_draw = False
    if has_flush_draw:
        flush_suit = [s for s, c in suit_counts.items() if c >= 4][0]
        hero_flush_cards = [c for c in hole_cards if c[1] == flush_suit]
        hero_flush_vals = [RANK_VAL[c[0]] for c in hero_flush_cards]
        # Check if we have Ace or King of flush suit (nut or 2nd nut)
        board_flush_vals = [RANK_VAL[c[0]] for c in board if c[1] == flush_suit]
        # Nut if we have Ace, or King when Ace not on board
        if 12 in hero_flush_vals:  # Ace
            is_nut_flush_draw = True
        elif 11 in hero_flush_vals and 12 not in board_flush_vals:  # King, no Ace on board
            is_nut_flush_draw = True
    
    # Straight draw detection (simplified - OESD or gutshot)
    all_vals_unique = sorted(set(hero_vals + board_vals))
    has_straight_draw = False
    has_straight = False
    if len(all_vals_unique) >= 4:
        # Check for 4 in a row (OESD) or 4 out of 5 (gutshot)
        for i in range(len(all_vals_unique) - 3):
            window = all_vals_unique[i:i+4]
            if window[-1] - window[0] <= 4:  # 4 cards within 5 ranks = draw
                has_straight_draw = True
        # Check for made straight (5 in a row)
        if len(all_vals_unique) >= 5:
            for i in range(len(all_vals_unique) - 4):
                window = all_vals_unique[i:i+5]
                if window[-1] - window[0] == 4:
                    has_straight = True
                    has_straight_draw = False
    # Wheel straight check (A2345)
    if {12, 0, 1, 2, 3}.issubset(set(hero_vals + board_vals)):
        has_straight = True
        has_straight_draw = False
    elif len({12, 0, 1, 2, 3} & set(hero_vals + board_vals)) >= 4:
        has_straight_draw = True
    
    return {
        'valid': True,
        'is_pocket_pair': is_pocket_pair,
        'pocket_val': pocket_val,
        'has_board_pair': has_board_pair,
        'board_pair_val': board_pair_val,
        'is_overpair': is_overpair,
        'is_underpair_to_ace': is_underpair_to_ace,
        'has_top_pair': has_top_pair,
        'has_good_kicker': has_good_kicker,
        'kicker_val': kicker_val,
        'has_two_pair': has_two_pair,
        'two_pair_type': two_pair_type,
        'has_set': has_set,
        'has_trips': has_trips,
        'has_any_pair': has_any_pair,
        'has_middle_pair': has_middle_pair,
        'has_bottom_pair': has_bottom_pair,
        'has_ace_on_board': has_ace_on_board,
        'has_flush_draw': has_flush_draw,
        'is_nut_flush_draw': is_nut_flush_draw,
        'has_flush': has_flush,
        'has_straight_draw': has_straight_draw,
        'has_straight': has_straight,
        'hero_vals': hero_vals,
        'board_vals': board_vals,
        'top_board_val': top_board_val,
    }

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
            'BTN': expand_range('22+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,54s,A7o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A5s+,K9s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo'), 'MP': expand_range('QQ+,AKs,AKo'), 'CO': expand_range('JJ+,AQs+,AKo'), 'BTN': expand_range('TT+,AQs+,AKo')},
        '3bet_bluff': expand_range('A5s-A4s'),
        'call_open_ip': expand_range('JJ-66,AQs-ATs,KQs-KJs,QJs,JTs,T9s,98s'),
        'bb_defend': expand_range('TT-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A9o+,KJo,QJo'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'kiro5': {
        'name': 'Kiro5 Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A3s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T7s+,96s+,85s+,75s+,64s+,54s,A8o+,K9o+,QTo+,JTo'),
            'SB': expand_range('44+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo'), 'MP': expand_range('QQ+,AKs,AKo'), 'CO': expand_range('JJ+,AQs+,AKo'), 'BTN': expand_range('TT+,AQs+,AKo')},
        '3bet_bluff': expand_range('A5s-A4s,K9s'),
        'call_open_ip': expand_range('JJ-88,AQs-AJs,KQs,TT-66,AJs-ATs,KQs-KJs,QJs,JTs,T9s,99-44,ATs-A9s,KJs-KTs,QJs-QTs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('99-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A9o+,KJo,QJo'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'kiro_v2': {
        'name': 'Kiro V2 Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A3s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('55+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,87s,76s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T7s+,96s+,85s+,75s,65s,54s,A8o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo'), 'MP': expand_range('QQ+,AKs,AKo'), 'CO': expand_range('JJ+,AQs+,AKo'), 'BTN': expand_range('TT+,AQs+,AKo')},
        '3bet_bluff': expand_range('A5s-A4s,K9s'),
        'call_open_ip': expand_range('JJ-77,AQs-ATs,KQs-KJs,QJs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('99-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A9o+,KJo,QJo'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
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
    'aggressive': {
        'name': 'Aggressive 2NL',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AJo+'),
            'MP': expand_range('66+,A9s+,A5s-A2s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T7s+,96s+,85s+,75s+,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('JJ+,AKs,AKo,AQs'),
            'CO': expand_range('TT+,AQs+,AKo,AJs'),
            'BTN': expand_range('99+,AQs+,AKo,AJs,KQs'),
        },
        '3bet_bluff': expand_range('A5s-A2s,K9s'),
        'call_open_ip': expand_range('99-22,AJs-A9s,KQs-KTs,QJs-QTs,JTs,T9s,98s,87s,76s'),
        'bb_defend': expand_range('99-22,A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,54s,A8o+,KTo+,QTo+,JTo,T9o,98o'),
        'call_3bet': expand_range('JJ,TT,99,88,AQs,AQo,AJs,KQs'),
        '4bet': expand_range('QQ+,AKs,AKo'),
    },
    '2nl_exploit': {
        'name': '2NL Exploit',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AJo+'),
            'MP': expand_range('66+,A9s+,A5s-A2s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T7s+,96s+,85s+,75s+,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('JJ+,AKs,AKo,AQs'),
            'CO': expand_range('TT+,AQs+,AKo,AJs'),
            'BTN': expand_range('99+,AQs+,AKo,AJs,KQs'),
        },
        '3bet_bluff': expand_range('A5s-A2s,K9s'),
        'call_open_ip': expand_range('JJ-44,AJs-A7s,KQs-K9s,QJs-Q9s,JTs-J9s,T9s,98s,87s,76s'),
        'bb_defend': expand_range('99-22,A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,54s,A8o+,KTo+,QTo+,JTo,T9o,98o'),
        'call_3bet': expand_range('QQ,JJ,TT,99,88,AQs,AQo,AJs,KQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    # VALUE_MAX: Maniac-style ranges + aggressive postflop
    'value_max': {
        'name': 'Value Max',
        'open': {
            'UTG': expand_range('55+,A7s+,A5s-A2s,KTs+,QTs+,JTs,T9s,ATo+,KJo+'),
            'MP': expand_range('44+,A5s+,K8s+,Q9s+,J9s+,T8s+,97s+,87s,76s,A9o+,KTo+,QJo'),
            'CO': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A7o+,K9o+,QTo+,JTo'),
            'BTN': expand_range('22+,A2s+,K2s+,Q4s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A2o+,K7o+,Q9o+,J9o+,T9o'),
            'SB': expand_range('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A5o+,K8o+,QTo+,JTo'),
        },
        '3bet_vs': {'UTG': expand_range('TT+,AQs+,AKo,AJs,KQs'), 'MP': expand_range('99+,AJs+,AKo,AQo,KQs,QJs'), 'CO': expand_range('88+,ATs+,AJo+,KQs,KJs,QJs,JTs'), 'BTN': expand_range('77+,A9s+,ATo+,KJs+,KQo,QJs,JTs,T9s')},
        '3bet_bluff': expand_range('A5s-A2s,K9s-K6s,Q9s-Q8s,J9s,T9s,98s,87s,76s,65s,54s'),
        'call_open_ip': expand_range('TT-22,AJs-A5s,KQs-K9s,QJs-Q9s,JTs-J9s,T9s,98s,87s,76s'),
        'sb_defend': expand_range('TT-22,AJs-A2s,KQs-K8s,QJs-Q9s,JTs-J9s,T9s-T8s,98s,87s,76s,A5o+,KQo,KJo,QJo'),
        'bb_defend': expand_range('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
        'call_3bet': expand_range('JJ,TT,99,AKo,AQs,AQo,AJs,KQs'),
        '4bet': expand_range('QQ+,AKs,AKo'),
        'overbet': True,
    },
    # SONNET_MAX: Sonnet preflop + optimized postflop for 2NL fish-heavy tables
    'sonnet_max': {
        'name': 'Sonnet Max',
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

# MANIAC: Very aggressive, 3-bets wide, overbets postflop (based on real 2NL data)
STRATEGIES['maniac'] = {
    'name': 'Maniac',
    'open': {
        'UTG': expand_range('55+,A7s+,A5s-A2s,KTs+,QTs+,JTs,T9s,ATo+,KJo+'),
        'MP': expand_range('44+,A5s+,K8s+,Q9s+,J9s+,T8s+,97s+,87s,76s,A9o+,KTo+,QJo'),
        'CO': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A7o+,K9o+,QTo+,JTo'),
        'BTN': expand_range('22+,A2s+,K2s+,Q4s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A2o+,K7o+,Q9o+,J9o+,T9o'),
        'SB': expand_range('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A5o+,K8o+,QTo+,JTo'),
    },
    '3bet_vs': {'UTG': expand_range('TT+,AQs+,AKo,AJs,KQs'), 'MP': expand_range('99+,AJs+,AKo,AQo,KQs,QJs'), 'CO': expand_range('88+,ATs+,AJo+,KQs,KJs,QJs,JTs'), 'BTN': expand_range('77+,A9s+,ATo+,KJs+,KQo,QJs,JTs,T9s')},
    '3bet_bluff': expand_range('A5s-A2s,K9s-K6s,Q9s-Q8s,J9s,T9s,98s,87s,76s,65s,54s'),
    'call_open_ip': expand_range('TT-22,AJs-A5s,KQs-K9s,QJs-Q9s,JTs-J9s,T9s,98s,87s,76s,AQo,AJo,ATo,KQo,KJo,QJo'),
    'sb_defend': expand_range('TT-22,AJs-A2s,KQs-K8s,QJs-Q9s,JTs-J9s,T9s-T8s,98s,87s,76s,A5o+,KQo,KJo,QJo'),
    'bb_defend': expand_range('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
    'call_3bet': expand_range('JJ,TT,99,AKo,AQs,AQo,AJs,KQs'),
    '4bet': expand_range('QQ+,AKs,AKo'),
    'overbet': True,  # Flag for postflop overbetting
}

# value_maniac: Exact copy of maniac but as a bot strategy (uses maniac postflop logic)
STRATEGIES['value_maniac'] = STRATEGIES['maniac'].copy()
STRATEGIES['value_maniac']['name'] = 'Value Maniac'

# value_lord: value_maniac with Session 41 improvements
STRATEGIES['value_lord'] = STRATEGIES['maniac'].copy()
STRATEGIES['value_lord']['name'] = 'Value Lord'


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
    
    # Two pair - check if strong or weak
    pair_ranks = sorted([r for r, c in rank_counts.items() if c >= 2], key=lambda r: RANK_VAL[r], reverse=True)
    if len(pair_ranks) >= 2:
        # Check which pairs we contribute to
        hero_pairs = [pr for pr in pair_ranks if pr in hero_ranks]
        board_only_ranks = [c[0] for c in board] if board else []
        board_pairs = [pr for pr in pair_ranks if board_only_ranks.count(pr) >= 2]
        
        # Check if hero has a pocket pair
        is_pocket_pair = len(hole_cards) == 2 and hole_cards[0][0] == hole_cards[1][0]
        
        if len(hero_pairs) >= 1:
            # No board pair = strong (we made both pairs)
            if len(board_pairs) == 0:
                return (3, "two pair", RANK_VAL[pair_ranks[0]])
            
            # POCKET PAIR + BOARD PAIR - strength depends on which pair is higher
            if is_pocket_pair:
                pocket_val = RANK_VAL[hole_cards[0][0]]
                board_pair_val = max(RANK_VAL[p] for p in board_pairs)
                if pocket_val > board_pair_val:
                    # KK on JJ = strong (only JJ beats us)
                    return (3, "two pair (pocket+board strong)", RANK_VAL[pair_ranks[0]])
                else:
                    # 66 on JJ = weak (any Jx has trips)
                    return (3, "two pair (pocket+board weak)", RANK_VAL[pair_ranks[0]])
            
            # ONE CARD + BOARD PAIR = weak (K2 on J2 board)
            # Board pair exists - danger depends on board pair rank
            # HIGH board pair (T+): Many hands contain these, villain likely has trips
            # LOW board pair (2-9): Fewer hands contain these, less likely trips
            board_pair_val = max(RANK_VAL[p] for p in board_pairs)
            if board_pair_val >= 8:  # T=8, J=9, Q=10, K=11, A=12
                return (3, "two pair (board paired)", RANK_VAL[pair_ranks[0]])
            else:
                return (3, "two pair (low board pair)", RANK_VAL[pair_ranks[0]])
    
    # One pair
    if pair_ranks:
        pr = pair_ranks[0]
        board_ranks = [c[0] for c in board] if board else []
        board_vals = sorted([RANK_VAL[r] for r in board_ranks], reverse=True)
        hero_vals = [RANK_VAL[r] for r in hero_ranks]
        
        # Check for pocket pair (both hole cards same rank)
        is_pocket_pair = len(hole_cards) == 2 and hole_cards[0][0] == hole_cards[1][0]
        
        if pr in hero_ranks:
            # OVERPAIR: Pocket pair higher than all board cards
            if is_pocket_pair and board_vals and RANK_VAL[pr] > board_vals[0]:
                return (2, f"overpair {pr}{pr}", RANK_VAL[pr] * 100 + RANK_VAL[pr])
            
            # UNDERPAIR TO ACE: Big pocket pair (TT+) but ace on board
            if is_pocket_pair and board_vals and any(v == RANK_VAL['A'] for v in board_vals):
                if RANK_VAL[pr] >= RANK_VAL['T'] and RANK_VAL[pr] < RANK_VAL['A']:
                    return (2, f"underpair {pr}{pr} (ace on board)", RANK_VAL[pr] * 100 + RANK_VAL[pr])
            
            # TOP PAIR
            if board_vals and RANK_VAL[pr] >= board_vals[0]:
                kicker = max(RANK_VAL[r] for r in hero_ranks if r != pr) if len(hero_ranks) > 1 else 0
                if kicker >= RANK_VAL['T']:
                    return (2, "top pair good kicker", RANK_VAL[pr] * 100 + kicker)
                return (2, "top pair weak kicker", RANK_VAL[pr] * 100 + kicker)
            
            # POCKET PAIR (underpair) - stronger than board-made pairs
            if is_pocket_pair:
                return (2, f"pocket pair {pr}{pr}", RANK_VAL[pr])
            
            # MIDDLE PAIR (one card pairs middle board card)
            elif board_vals and len(board_vals) > 1 and RANK_VAL[pr] >= board_vals[1]:
                return (2, "middle pair", RANK_VAL[pr])
            
            # BOTTOM PAIR (one card pairs lowest board card)
            return (2, "bottom pair", RANK_VAL[pr])
        
        # Board pair only - we don't have it, just high card with board pair
        return (1, "high card (board paired)", RANK_VAL[max(hero_ranks, key=lambda r: RANK_VAL[r])])
    
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


def calculate_equity(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]], 
                     num_opponents: int = 1, simulations: int = 1000) -> float:
    """Monte Carlo equity calculation. Returns win probability 0-100."""
    if len(board) < 3:
        return 0.0  # Preflop - don't calculate
    
    # Build deck minus known cards
    deck = [(r, s) for r in RANKS for s in SUITS]
    known = set(hole_cards + board)
    deck = [c for c in deck if c not in known]
    
    wins = 0
    ties = 0
    
    for _ in range(simulations):
        # Deal remaining board cards
        cards_needed = 5 - len(board)
        random.shuffle(deck)
        full_board = board + deck[:cards_needed]
        remaining = deck[cards_needed:]
        
        # Deal opponent hands
        opp_hands = []
        idx = 0
        for _ in range(num_opponents):
            opp_hands.append([remaining[idx], remaining[idx+1]])
            idx += 2
        
        # Evaluate all hands
        hero_rank = evaluate_hand(hole_cards, full_board)
        opp_ranks = [evaluate_hand(oh, full_board) for oh in opp_hands]
        
        best_opp = max(opp_ranks, key=lambda x: (x[0], x[2]))
        
        if (hero_rank[0], hero_rank[2]) > (best_opp[0], best_opp[2]):
            wins += 1
        elif (hero_rank[0], hero_rank[2]) == (best_opp[0], best_opp[2]):
            ties += 0.5
    
    return round((wins + ties) / simulations * 100, 1)


def count_outs(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]]) -> Tuple[int, List[str]]:
    """Count outs to improve hand. Returns (num_outs, list of out types)."""
    if len(board) < 3:
        return (0, [])
    
    outs = 0
    out_types = []
    draws = check_draws(hole_cards, board)
    hand_info = analyze_hand(hole_cards, board)
    
    if "flush_draw" in draws:
        outs += 9
        out_types.append("9 flush")
    if "oesd" in draws:
        outs += 8 if "flush_draw" not in draws else 6  # Discount overlapping
        out_types.append("8 straight" if "flush_draw" not in draws else "6 straight")
    elif "gutshot" in draws:
        outs += 4
        out_types.append("4 gutshot")
    
    # Pair outs (5 outs to two pair/trips if we have top pair)
    if hand_info['has_top_pair']:
        outs += 5
        out_types.append("5 improve pair")
    
    return (outs, out_types)


def get_hand_info(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]], 
                  pot: float, to_call: float, num_opponents: int = 1) -> Dict:
    """Get comprehensive hand info for display."""
    rank, desc, kicker = evaluate_hand(hole_cards, board)
    draws = check_draws(hole_cards, board)
    outs, out_types = count_outs(hole_cards, board)
    
    # Equity (only postflop)
    equity = calculate_equity(hole_cards, board, num_opponents, 500) if board else 0
    
    # Pot odds
    pot_odds = round(to_call / (pot + to_call) * 100, 1) if to_call > 0 else 0
    
    # Implied odds needed
    implied_needed = 0
    if outs > 0 and to_call > 0:
        # Rule of 2 and 4
        draw_equity = outs * 2 if len(board) == 4 else outs * 4
        if draw_equity < pot_odds:
            # Need implied odds - how much more do we need to win?
            implied_needed = round((to_call / (draw_equity/100)) - pot, 2)
    
    return {
        'hand_rank': rank,
        'hand_desc': desc,
        'draws': draws,
        'outs': outs,
        'out_types': out_types,
        'equity': equity,
        'pot_odds': pot_odds,
        'implied_needed': implied_needed
    }


# Postflop decision logic - matches strategy files exactly
def postflop_action(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]], 
                    pot: float, to_call: float, street: str, is_ip: bool,
                    is_aggressor: bool, archetype: str = None, strategy: str = None,
                    num_opponents: int = 1, bb_size: float = 0.05) -> Tuple[str, float, str]:
    """
    Postflop decision based on strategy file rules.
    Returns (action, bet_size, reasoning).
    archetype: 'fish', 'nit', 'tag', 'lag' for special behavior
    strategy: 'gpt3', 'gpt4', 'sonnet', 'kiro_optimal' for bot-specific logic
    num_opponents: number of active opponents (1=heads-up, 2+=multiway)
    """
    strength, desc, kicker = evaluate_hand(hole_cards, board)
    draws = check_draws(hole_cards, board)
    
    has_flush_draw = "flush_draw" in draws
    has_oesd = "oesd" in draws
    has_gutshot = "gutshot" in draws
    combo_draw = has_flush_draw and (has_oesd or has_gutshot)
    has_any_draw = has_flush_draw or has_oesd or has_gutshot
    has_pair = strength >= 2
    
    # Multiway pot adjustments (3+ players)
    is_multiway = num_opponents >= 2
    
    # Check for overpair and pocket pair below ace
    if len(board) >= 3:
        board_ranks = [RANK_VAL[c[0]] for c in board]
        hole_ranks = [RANK_VAL[c[0]] for c in hole_cards]
        is_pocket_pair = (hole_ranks[0] == hole_ranks[1])
        is_overpair = (is_pocket_pair and hole_ranks[0] > max(board_ranks) and strength == 2)
        board_has_ace = any(c[0] == 'A' for c in board)
        # Big pocket pair (TT+) below ace on board
        is_underpair_to_ace = (is_pocket_pair and board_has_ace and 
                               hole_ranks[0] >= RANK_VAL['T'] and hole_ranks[0] < RANK_VAL['A'])
    else:
        is_overpair = False
        board_has_ace = False
        is_underpair_to_ace = False
    
    # ARCHETYPES TUNED TO REAL 2NL BLITZ DATA (886 hands):
    # - C-bet freq: 21% (very low!)
    # - Bet sizing: mostly 33-50% pot
    # - Players check A LOT (79% of flops checked through)
    
    # Get hand info for archetypes (no string matching)
    hand_info = analyze_hand(hole_cards, board)
    
    # FISH: Passive, checks a lot, calls with any pair/draw
    if archetype == 'fish':
        if to_call == 0 or to_call is None:
            if strength >= 4:
                return ('bet', round(pot * 0.4, 2), f"{desc} - fish bets small")
            if strength >= 3:
                if random.random() < 0.4:
                    return ('bet', round(pot * 0.35, 2), f"{desc} - fish bets small")
            return ('check', 0, "fish checks")
        else:
            if has_pair or has_any_draw:
                return ('call', 0, f"{desc} - fish calls")
            return ('fold', 0, "fish folds air")
    
    # NIT: Very passive, only bets nuts, folds to aggression
    if archetype == 'nit':
        if to_call == 0 or to_call is None:
            if strength >= 4:
                return ('bet', round(pot * 0.5, 2), f"{desc} - nit value bets")
            if strength == 3 or (hand_info['has_top_pair'] and hand_info['has_good_kicker']):
                if random.random() < 0.3:
                    return ('bet', round(pot * 0.4, 2), f"{desc} - nit bets")
            return ('check', 0, "nit checks")
        else:
            if strength >= 4:
                return ('call', 0, f"{desc} - nit calls")
            if strength == 3 and street == 'flop':
                return ('call', 0, f"{desc} - nit calls flop")
            return ('fold', 0, f"{desc} - nit folds")
    
    # TAG: C-bets 35%, small sizing, gives up without equity
    if archetype == 'tag':
        if to_call == 0 or to_call is None:
            if strength >= 3:
                return ('bet', round(pot * 0.45, 2), f"{desc} - tag value bets")
            if hand_info['has_top_pair'] or hand_info['is_overpair']:
                if street == 'flop' and random.random() < 0.35:
                    return ('bet', round(pot * 0.35, 2), f"{desc} - tag c-bets")
                if street == 'turn' and random.random() < 0.25:
                    return ('bet', round(pot * 0.4, 2), f"{desc} - tag barrels")
            if combo_draw and street == 'flop' and random.random() < 0.4:
                return ('bet', round(pot * 0.35, 2), "tag semi-bluffs")
            return ('check', 0, f"{desc} - tag checks")
        else:
            if strength >= 4:
                return ('call', 0, f"{desc} - tag calls")
            if strength == 3 and street != 'river':
                return ('call', 0, f"{desc} - tag calls")
            if hand_info['has_top_pair'] and street == 'flop':
                return ('call', 0, f"{desc} - tag calls flop")
            return ('fold', 0, f"{desc} - tag folds")
    
    # LAG: C-bets 50%, medium sizing, more aggressive than others
    if archetype == 'lag':
        if to_call == 0 or to_call is None:
            if strength >= 3:
                return ('bet', round(pot * 0.5, 2), f"{desc} - lag value bets")
            if hand_info['has_any_pair']:
                if street == 'flop' and random.random() < 0.50:
                    return ('bet', round(pot * 0.4, 2), f"{desc} - lag c-bets")
                if street == 'turn' and random.random() < 0.35:
                    return ('bet', round(pot * 0.45, 2), f"{desc} - lag barrels")
            if has_any_draw and random.random() < 0.5:
                return ('bet', round(pot * 0.4, 2), "lag semi-bluffs")
            if street == 'flop' and random.random() < 0.30:
                return ('bet', round(pot * 0.33, 2), "lag c-bets air")
            if street == 'river' and random.random() < 0.15:
                return ('bet', round(pot * 0.45, 2), "lag river bluff")
            return ('check', 0, f"{desc} - lag checks")
        else:
            if strength >= 3:
                return ('call', 0, f"{desc} - lag calls")
            if hand_info['has_any_pair'] and street != 'river':
                return ('call', 0, f"{desc} - lag floats")
            if has_flush_draw or has_oesd:
                return ('call', 0, "lag calls with draw")
            return ('fold', 0, f"{desc} - lag folds")
    
    # MANIAC: Most aggressive, overbets sometimes, but still realistic
    if archetype == 'maniac':
        if to_call == 0 or to_call is None:
            if strength >= 4:
                return ('bet', round(pot * 0.75, 2), f"{desc} - maniac bets big")
            if strength >= 3:
                return ('bet', round(pot * 0.6, 2), f"{desc} - maniac bets")
            if hand_info['has_any_pair']:
                if street == 'flop' and random.random() < 0.65:
                    return ('bet', round(pot * 0.5, 2), f"{desc} - maniac c-bets")
                if street == 'turn' and random.random() < 0.45:
                    return ('bet', round(pot * 0.55, 2), f"{desc} - maniac barrels")
                if street == 'river' and random.random() < 0.35:
                    return ('bet', round(pot * 0.6, 2), f"{desc} - maniac river bet")
            if has_any_draw:
                return ('bet', round(pot * 0.5, 2), "maniac semi-bluffs")
            if street == 'flop' and random.random() < 0.50:
                return ('bet', round(pot * 0.4, 2), "maniac c-bets air")
            if street == 'turn' and random.random() < 0.30:
                return ('bet', round(pot * 0.45, 2), "maniac barrels turn")
            if street == 'river' and random.random() < 0.20:
                return ('bet', round(pot * 0.5, 2), "maniac river bluff")
            return ('check', 0, f"{desc} - maniac checks")
        else:
            if strength >= 3:
                return ('call', 0, f"{desc} - maniac calls")
            if hand_info['has_any_pair']:
                return ('call', 0, f"{desc} - maniac calls any pair")
            if has_any_draw:
                return ('call', 0, "maniac calls with draw")
            if street == 'flop' and random.random() < 0.35:
                return ('call', 0, "maniac floats flop")
            return ('fold', 0, f"{desc} - maniac folds")
    
    # BOT STRATEGIES - strategy-specific postflop logic
    # gpt3/gpt4: Board texture aware, smaller c-bets, 3-bet pot adjustments
    # sonnet/kiro_optimal: Bigger value bets, overpair logic
    # value_max: Maniac-style big bets but smarter (doesn't bluff as much)
    # value_maniac: Exact maniac postflop (overbets, calls wide)
    # BUT with paired board protection (learned from KK on JJ disaster)
    
    if strategy == 'value_maniac':
        return _postflop_value_maniac(hole_cards, board, pot, to_call, street,
                                      strength, desc, has_any_draw, has_flush_draw, has_oesd, bb_size)
    
    if strategy == 'value_lord':
        return _postflop_value_lord(hole_cards, board, pot, to_call, street,
                                    strength, desc, has_any_draw, has_flush_draw, has_oesd, bb_size, is_aggressor)
    
    if strategy == 'sonnet_max':
        return _postflop_sonnet_max(hole_cards, board, pot, to_call, street, is_ip,
                                    is_aggressor, strength, desc, draws, combo_draw,
                                    has_flush_draw, has_oesd, has_any_draw)
    
    if strategy == 'value_max':
        # Calculate equity for smarter decisions
        equity = calculate_equity(hole_cards, board, num_opponents, 200) / 100.0  # 0-1 scale
        return _postflop_value_max(hole_cards, board, pot, to_call, street, is_ip,
                                   is_aggressor, strength, desc, draws, combo_draw,
                                   has_flush_draw, has_oesd, has_gutshot, has_any_draw, equity)
    
    if strategy in ['gpt3', 'gpt4']:
        return _postflop_gpt(hole_cards, board, pot, to_call, street, is_ip, 
                            is_aggressor, strength, desc, draws, combo_draw,
                            has_flush_draw, has_oesd, has_gutshot, is_overpair,
                            is_underpair_to_ace, is_multiway)
    
    # Sonnet-style strategies (big value bets)
    if strategy in ['sonnet', 'kiro_optimal', 'kiro5', 'kiro_v2', '2nl_exploit', 'aggressive']:
        return _postflop_sonnet(hole_cards, board, pot, to_call, street, is_ip,
                               is_aggressor, strength, desc, draws, combo_draw,
                               has_flush_draw, has_oesd, is_overpair, board_has_ace,
                               is_underpair_to_ace, is_multiway)
    
    # DEFAULT fallback (same as sonnet)
    return _postflop_sonnet(hole_cards, board, pot, to_call, street, is_ip,
                           is_aggressor, strength, desc, draws, combo_draw,
                           has_flush_draw, has_oesd, is_overpair, board_has_ace,
                           is_underpair_to_ace, is_multiway)


def _postflop_value_maniac(hole_cards, board, pot, to_call, street, strength, desc, has_any_draw, has_flush_draw=False, has_oesd=False, bb_size=0.05):
    """
    VALUE_MANIAC postflop - Overbets for value, calls wide, paired board protection.
    """
    hand_info = analyze_hand(hole_cards, board)
    bet_in_bb = to_call / bb_size if bb_size > 0 else 0
    # Use pot-relative sizing for "big bet" - 60%+ pot is big
    is_big_bet = to_call > 0 and pot > 0 and to_call >= pot * 0.5
    is_dangerous_board_pair = hand_info['board_pair_val'] is not None and hand_info['board_pair_val'] >= 8  # T+
    has_strong_draw = has_flush_draw or has_oesd  # 8+ outs
    
    if to_call == 0 or to_call is None:
        # No bet to call - bet for value
        if strength >= 4:  # Set+
            return ('bet', round(pot * 1.25, 2), f"{desc} - overbet value")
        if strength >= 3:  # Two pair
            if hand_info['two_pair_type'] == 'one_card_board_pair' and is_dangerous_board_pair:
                if street == 'flop':
                    return ('bet', round(pot * 0.33, 2), f"{desc} - small bet (pot control)")
                return ('check', 0, f"{desc} - check (vulnerable to trips)")
            return ('bet', round(pot * 1.1, 2), f"{desc} - bet big")
        if hand_info['has_any_pair']:
            if street in ['flop', 'turn'] and random.random() < 0.85:
                return ('bet', round(pot * 1.0, 2), f"{desc} - overbet")
            if street == 'river' and random.random() < 0.5:
                return ('bet', round(pot * 1.2, 2), f"{desc} - river overbet")
        if has_any_draw:
            return ('bet', round(pot * 1.0, 2), "overbet draw")
        if street == 'flop' and random.random() < 0.80:
            return ('bet', round(pot * 0.9, 2), "c-bet big")
        if street == 'turn' and random.random() < 0.60:
            return ('bet', round(pot * 1.0, 2), "barrel turn")
        if street == 'river' and random.random() < 0.35:
            return ('bet', round(pot * 1.1, 2), "river bluff")
        return ('check', 0, f"{desc} - check")
    else:
        # Facing bet - raise monsters, call pairs, fold air
        if strength >= 6:
            return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
        if strength >= 4:
            return ('raise', round(to_call * 2.5, 2), f"{desc} - raise strong")
        if strength == 3:
            if hand_info['two_pair_type'] == 'pocket_over_board':
                return ('raise', round(to_call * 2.5, 2), f"{desc} - raise strong")
            if hand_info['two_pair_type'] == 'pocket_under_board':
                if is_big_bet:
                    return ('fold', 0, f"{desc} - fold (weak two pair vs big bet)")
                return ('call', 0, f"{desc} - call (weak two pair)")
            if hand_info['two_pair_type'] == 'both_cards_hit':
                return ('raise', round(to_call * 2.5, 2), f"{desc} - raise strong")
            if hand_info['two_pair_type'] == 'one_card_board_pair' and is_dangerous_board_pair:
                if is_big_bet or street == 'river':
                    return ('fold', 0, f"{desc} - fold (two pair on dangerous board)")
                return ('call', 0, f"{desc} - call (but fold to more aggression)")
            return ('raise', round(to_call * 2.5, 2), f"{desc} - raise strong")
        # River defense based on hand strength and pot-relative bet size
        # 2NL villains under-bluff, so need strong hands to call big bets
        pot_pct = to_call / pot if pot > 0 else 0
        if street == 'river':
            # Overpairs can call up to pot-sized bets
            if hand_info['is_overpair']:
                if pot_pct > 1.0:  # Only fold overpair to overbet
                    return ('fold', 0, f"{desc} - fold overpair vs {pot_pct:.0%} pot bet")
                return ('call', 0, f"{desc} - call river")
            if is_big_bet and strength < 3:  # 60%+ pot bet needs two pair+
                return ('fold', 0, f"{desc} - fold vs {pot_pct:.0%} pot bet (need two pair+)")
            if strength >= 2:  # Top pair+ can call small river bets
                return ('call', 0, f"{desc} - call river")
            return ('fold', 0, f"{desc} - fold river")
        # Flop/turn: fold weak pairs to huge overbets
        if hand_info['is_pocket_pair'] or hand_info['has_any_pair']:
            pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1
            pot_pct = to_call / pot if pot > 0 else 0
            # Fold weak pairs (bottom/middle) to overbets (100%+ pot)
            if pot_pct > 1.0 and strength <= 2 and not hand_info['has_top_pair']:
                return ('fold', 0, f"{desc} - fold weak pair vs overbet")
            if pot_odds > 0.5 and not has_strong_draw:
                return ('fold', 0, f"{desc} - fold pair vs all-in")
            return ('call', 0, f"{desc} - call pair")
        # Draw calling with conservative thresholds
        # Math: flush=9 outs=18%, OESD=8 outs=16%, gutshot=4 outs=8%
        # Conservative: require ~1.5x better odds than pure math (villain has something)
        # Plus implied odds at 2NL (fish pay off when we hit)
        if has_any_draw and street != 'river':
            pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1
            is_nut_draw = hand_info.get('is_nut_flush_draw', False)
            # Nut flush draw: can call up to 40% (implied odds)
            # Non-nut flush draw: call up to 25% (conservative)
            # OESD: call up to 22%
            # Gutshot: call up to 12%
            if has_flush_draw and is_nut_draw and pot_odds <= 0.41:
                return ('call', 0, "call nut flush draw")
            if has_flush_draw and pot_odds <= 0.25:
                return ('call', 0, "call flush draw")
            if has_oesd and pot_odds <= 0.22:
                return ('call', 0, "call OESD")
            if has_any_draw and pot_odds <= 0.12:
                return ('call', 0, "call gutshot")
            return ('fold', 0, f"{desc} - fold (bad odds for draw)")
        # Overcards and floats - only with good odds
        pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1
        if street == 'flop' and hand_info['hero_vals'][0] >= 11 and pot_odds <= 0.30:
            return ('call', 0, "call overcards")
        if street == 'flop' and pot_odds <= 0.25 and random.random() < 0.4:
            return ('call', 0, "float flop")
        return ('fold', 0, f"{desc} - fold")


def _postflop_value_lord(hole_cards, board, pot, to_call, street, strength, desc, has_any_draw, 
                         has_flush_draw=False, has_oesd=False, bb_size=0.05, is_aggressor=False):
    """
    VALUE_LORD postflop - value_maniac with Session 41 improvements.
    Fixes: c-bet discipline, overpair aggression, bottom pair caution.
    """
    hand_info = analyze_hand(hole_cards, board)
    bet_in_bb = to_call / bb_size if bb_size > 0 else 0
    is_big_bet = to_call > 0 and pot > 0 and to_call >= pot * 0.5
    is_dangerous_board_pair = hand_info['board_pair_val'] is not None and hand_info['board_pair_val'] >= 8  # T+
    has_strong_draw = has_flush_draw or has_oesd
    
    # Check for straight board (4+ cards within 5-rank span = straight possible)
    board_vals = sorted([RANK_VAL[c[0]] for c in board], reverse=True) if board else []
    is_straight_board = False
    if len(board_vals) >= 4:
        # Check if any 4 cards are within a 5-rank span
        for i in range(len(board_vals) - 3):
            window = board_vals[i:i+4]
            if max(window) - min(window) <= 5:  # 4 cards within 5 ranks = straight possible
                is_straight_board = True
                break
    
    if to_call == 0 or to_call is None:
        # No bet to call - bet for value
        if strength >= 4:  # Set+
            return ('bet', round(pot * 1.25, 2), f"{desc} - overbet value")
        if strength >= 3:  # Two pair
            if hand_info['two_pair_type'] == 'one_card_board_pair' and is_dangerous_board_pair:
                if street == 'flop':
                    return ('bet', round(pot * 0.33, 2), f"{desc} - small bet (pot control)")
                return ('check', 0, f"{desc} - check (vulnerable to trips)")
            return ('bet', round(pot * 1.1, 2), f"{desc} - bet big")
        # FIX 1: Overpairs ALWAYS bet (don't check)
        if hand_info['is_overpair']:
            if street in ['flop', 'turn']:
                return ('bet', round(pot * 1.0, 2), f"{desc} - overbet")
            if street == 'river':
                return ('bet', round(pot * 1.2, 2), f"{desc} - river overbet")
        # FIX 2: Weak pairs on straight board = CHECK (not top pair, not overpair)
        if hand_info['has_any_pair'] and not hand_info['has_top_pair'] and not hand_info['is_overpair'] and is_straight_board:
            return ('check', 0, f"{desc} - check (weak pair on straight board)")
        # Pairs - bet normally
        if hand_info['has_any_pair']:
            if street in ['flop', 'turn'] and random.random() < 0.85:
                return ('bet', round(pot * 1.0, 2), f"{desc} - overbet")
            if street == 'river' and random.random() < 0.5:
                return ('bet', round(pot * 1.2, 2), f"{desc} - river overbet")
        if has_any_draw:
            return ('bet', round(pot * 1.0, 2), "overbet draw")
        # FIX 3: Only c-bet high card when we were aggressor (opened preflop)
        if is_aggressor:
            if street == 'flop' and random.random() < 0.80:
                return ('bet', round(pot * 0.9, 2), "c-bet big")
            if street == 'turn' and random.random() < 0.60:
                return ('bet', round(pot * 1.0, 2), "barrel turn")
            if street == 'river' and random.random() < 0.35:
                return ('bet', round(pot * 1.1, 2), "river bluff")
        return ('check', 0, f"{desc} - check")
    else:
        # Facing bet - same as value_maniac
        if strength >= 6:
            return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
        if strength >= 4:
            return ('raise', round(to_call * 2.5, 2), f"{desc} - raise strong")
        if strength == 3:
            if hand_info['two_pair_type'] == 'pocket_over_board':
                return ('raise', round(to_call * 2.5, 2), f"{desc} - raise strong")
            if hand_info['two_pair_type'] == 'pocket_under_board':
                if is_big_bet:
                    return ('fold', 0, f"{desc} - fold (weak two pair vs big bet)")
                return ('call', 0, f"{desc} - call (weak two pair)")
            if hand_info['two_pair_type'] == 'both_cards_hit':
                return ('raise', round(to_call * 2.5, 2), f"{desc} - raise strong")
            if hand_info['two_pair_type'] == 'one_card_board_pair' and is_dangerous_board_pair:
                if is_big_bet or street == 'river':
                    return ('fold', 0, f"{desc} - fold (two pair on dangerous board)")
                return ('call', 0, f"{desc} - call (but fold to more aggression)")
            return ('raise', round(to_call * 2.5, 2), f"{desc} - raise strong")
        pot_pct = to_call / pot if pot > 0 else 0
        if street == 'river':
            if hand_info['is_overpair']:
                if pot_pct > 1.0:
                    return ('fold', 0, f"{desc} - fold overpair vs {pot_pct:.0%} pot bet")
                return ('call', 0, f"{desc} - call river")
            if is_big_bet and strength < 3:
                return ('fold', 0, f"{desc} - fold vs {pot_pct:.0%} pot bet (need two pair+)")
            if strength >= 2:
                return ('call', 0, f"{desc} - call river")
            return ('fold', 0, f"{desc} - fold river")
        if hand_info['is_pocket_pair'] or hand_info['has_any_pair']:
            pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1
            pot_pct = to_call / pot if pot > 0 else 0
            if pot_pct > 1.0 and strength <= 2 and not hand_info['has_top_pair']:
                return ('fold', 0, f"{desc} - fold weak pair vs overbet")
            if pot_odds > 0.5 and not has_strong_draw:
                return ('fold', 0, f"{desc} - fold pair vs all-in")
            return ('call', 0, f"{desc} - call pair")
        if has_any_draw and street != 'river':
            pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1
            is_nut_draw = hand_info.get('is_nut_flush_draw', False)
            if has_flush_draw and is_nut_draw and pot_odds <= 0.41:
                return ('call', 0, "call nut flush draw")
            if has_flush_draw and pot_odds <= 0.25:
                return ('call', 0, "call flush draw")
            if has_oesd and pot_odds <= 0.22:
                return ('call', 0, "call OESD")
            if has_any_draw and pot_odds <= 0.12:
                return ('call', 0, "call gutshot")
            return ('fold', 0, f"{desc} - fold (bad odds for draw)")
        pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1
        if street == 'flop' and hand_info['hero_vals'][0] >= 11 and pot_odds <= 0.30:
            return ('call', 0, "call overcards")
        if street == 'flop' and pot_odds <= 0.25 and random.random() < 0.4:
            return ('call', 0, "float flop")
        return ('fold', 0, f"{desc} - fold")


def _postflop_value_max(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                        strength, desc, draws, combo_draw, has_flush_draw, has_oesd, has_gutshot, has_any_draw, equity=0):
    """
    VALUE_MAX postflop - Uses analyze_hand() for all hand analysis.
    """
    # Use analyze_hand() for all hand analysis
    hand_info = analyze_hand(hole_cards, board)
    
    # Board analysis
    from collections import Counter
    board_ranks = sorted([RANK_VAL[c[0]] for c in board], reverse=True) if board else []
    board_suits = [c[1] for c in board] if board else []
    board_rank_counts = Counter([c[0] for c in board]) if board else Counter()
    num_board_pairs = sum(1 for c in board_rank_counts.values() if c >= 2)
    is_paired_board = num_board_pairs >= 1
    is_double_paired = num_board_pairs >= 2
    
    is_monotone = len(set(board_suits)) == 1 if len(board_suits) >= 3 else False
    is_two_tone = len(set(board_suits)) == 2 if len(board_suits) >= 3 else False
    is_vulnerable = is_two_tone or (len(board_ranks) >= 3 and board_ranks[0] - board_ranks[-1] <= 4)
    is_scary_board = is_monotone or is_paired_board or (board_ranks and board_ranks[0] >= RANK_VAL['Q'])
    
    # 4-flush detection
    suit_counts = Counter(board_suits)
    board_has_4flush = any(c >= 4 for c in suit_counts.values())
    hero_suits = [c[1] for c in hole_cards]
    hero_has_flush_card = board_has_4flush and any(s in hero_suits for s in [k for k, v in suit_counts.items() if v >= 4])
    
    # Pot odds
    pot_odds = to_call / (pot + to_call) if to_call and pot > 0 else 0
    is_big_bet = to_call and pot > 0 and to_call >= pot * 0.6
    
    if to_call == 0 or to_call is None:
        # === BETTING ===
        if strength >= 5:
            return ('bet', round(pot * 1.0, 2), f"{desc} - bet for value")
        if strength == 4:
            return ('bet', round(pot * (0.85 if is_vulnerable else 0.75), 2), f"{desc} - value bet")
        if strength == 3:  # Two pair
            # Weak two pair types = pot control
            if hand_info['two_pair_type'] in ['pocket_under_board', 'one_card_board_pair']:
                if street == 'flop':
                    return ('bet', round(pot * 0.33, 2), f"{desc} - small bet (pot control)")
                return ('check', 0, f"{desc} - check (vulnerable)")
            return ('bet', round(pot * 0.7, 2), f"{desc} - value bet")
        if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
            if is_paired_board and street != 'flop':
                return ('check', 0, f"{desc} - check (board paired)")
            if street in ['flop', 'turn']:
                return ('bet', round(pot * 0.55, 2), f"{desc} - value bet")
            return ('check', 0, f"{desc} - check river")
        if hand_info['has_top_pair'] and not hand_info['has_good_kicker']:
            if street == 'flop':
                return ('bet', round(pot * 0.35, 2), f"{desc} - small c-bet")
            return ('check', 0, f"{desc} - check (weak kicker)")
        if hand_info['is_overpair']:
            if is_paired_board:
                return ('check', 0, f"{desc} - check (board paired)")
            return ('bet', round(pot * 0.55, 2), f"{desc} - value bet")
        if hand_info['is_underpair_to_ace']:
            if combo_draw:
                return ('bet', round(pot * 0.55, 2), f"{desc} + draw - semi-bluff")
            return ('check', 0, f"{desc} - check underpair")
        # Middle/bottom pair - check, don't bet for "thin value"
        if hand_info['has_any_pair']:
            return ('check', 0, f"{desc} - check weak pair")
        # Draws
        if combo_draw:
            return ('bet', round(pot * 0.65, 2), "combo draw - semi-bluff")
        if has_flush_draw and street in ['flop', 'turn']:
            return ('bet', round(pot * 0.55, 2), "flush draw - semi-bluff")
        if has_oesd and street in ['flop', 'turn']:
            return ('bet', round(pot * 0.5, 2), "OESD - semi-bluff")
        # C-bet
        if is_aggressor and street == 'flop' and not is_scary_board:
            return ('bet', round(pot * 0.33, 2), "c-bet dry board")
        return ('check', 0, "check - no equity on scary board")
    
    else:
        # === FACING BET ===
        
        # HIGH CARD ON PAIRED BOARD = FOLD
        if strength <= 1 and is_paired_board:
            return ('fold', 0, f"{desc} - fold (high card on paired board)")
        
        # DOUBLE PAIRED BOARD = need full house+
        if is_double_paired and strength < 7:
            return ('fold', 0, f"{desc} - fold (double paired board)")
        
        # 4-flush without flush = fold
        if board_has_4flush and not hero_has_flush_card and strength < 7:
            return ('fold', 0, f"{desc} - fold (4-flush on board)")
        
        # Monsters
        if strength >= 5:
            return ('raise', round(pot * 2.0, 2), f"{desc} - raise for value")
        if strength == 4:
            return ('call', 0, f"{desc} - call") if street == 'river' else ('raise', round(pot * 2.0, 2), f"{desc} - raise")
        
        # Two pair
        if strength == 3:
            # Weak two pair types on paired board = careful
            if hand_info['two_pair_type'] in ['pocket_under_board', 'one_card_board_pair']:
                if is_big_bet or street == 'river':
                    return ('fold', 0, f"{desc} - fold (weak two pair)")
                return ('call', 0, f"{desc} - call (but fold to more aggression)")
            return ('call', 0, f"{desc} - call")
        
        # Top pair good kicker - call flop/turn, careful on river
        if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
            if street in ['flop', 'turn']:
                return ('call', 0, f"{desc} - call {street}")
            if pot_odds <= 0.35:
                return ('call', 0, f"{desc} - call small river")
            return ('fold', 0, f"{desc} - fold big river bet")
        
        # Top pair weak kicker - call flop only
        if hand_info['has_top_pair'] and not hand_info['has_good_kicker']:
            if street == 'flop' and pot_odds <= 0.35:
                return ('call', 0, f"{desc} - call flop")
            return ('fold', 0, f"{desc} - fold")
        
        # Overpair/underpair - call down reasonably
        if hand_info['is_overpair']:
            if street == 'river' and is_big_bet:
                return ('fold', 0, f"{desc} - fold big river bet")
            return ('call', 0, f"{desc} - call")
        if hand_info['is_underpair_to_ace']:
            if street == 'flop' and pot_odds <= 0.30:
                return ('call', 0, f"{desc} - call flop")
            return ('fold', 0, f"{desc} - fold")
        
        # Pocket pair (not overpair/underpair) - call flop
        if hand_info['is_pocket_pair']:
            if street == 'flop' and pot_odds <= 0.30:
                return ('call', 0, f"{desc} - call flop")
            return ('fold', 0, f"{desc} - fold")
        
        # Any other pair - call flop only
        if hand_info['has_any_pair']:
            if street == 'flop' and pot_odds <= 0.30:
                return ('call', 0, f"{desc} - call flop")
            return ('fold', 0, f"{desc} - fold")
        
        # Draws - conservative thresholds (villain has something)
        if combo_draw and pot_odds <= 0.35:
            return ('call', 0, "combo draw - call")
        if has_flush_draw:
            threshold = 0.41 if hand_info.get('is_nut_flush_draw') else 0.25
            if pot_odds <= threshold:
                return ('call', 0, f"{'nut ' if hand_info.get('is_nut_flush_draw') else ''}flush draw - call")
        if has_oesd and pot_odds <= 0.22:
            return ('call', 0, "OESD - call")
        if has_gutshot and pot_odds <= 0.12:
            return ('call', 0, "gutshot - call")
        
        # Overcards on flop - float with good odds
        if street == 'flop' and strength == 1:
            hero_high = max(hand_info['hero_vals'])
            board_high = hand_info['top_board_val']
            # Two overcards = 6 outs (~24% by river)
            if hero_high > board_high and min(hand_info['hero_vals']) > board_high:
                if pot_odds <= 0.25:
                    return ('call', 0, f"{desc} - float with overcards")
            # One overcard = 3 outs (~12% by river)
            elif hero_high > board_high and pot_odds <= 0.15:
                return ('call', 0, f"{desc} - float with overcard")
        
        return ('fold', 0, f"{desc} - fold")


def _postflop_gpt(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                  strength, desc, draws, combo_draw, has_flush_draw, has_oesd, has_gutshot,
                  is_overpair=False, is_underpair_to_ace=False, is_multiway=False):
    """
    GPT3/GPT4 postflop: Board texture aware, smaller c-bets on dry boards.
    Uses analyze_hand() for all hand property checks.
    """
    hand_info = analyze_hand(hole_cards, board)
    
    # Check board texture
    board_ranks = sorted([RANK_VAL[c[0]] for c in board], reverse=True)
    board_suits = [c[1] for c in board]
    is_dry = (board_ranks[0] >= RANK_VAL['Q'] and
              len(set(board_suits)) >= 2 and
              (len(board_ranks) < 2 or board_ranks[0] - board_ranks[-1] > 4))
    
    if to_call == 0 or to_call is None:
        # Multiway: only bet strong value + strong draws
        if is_multiway:
            if strength >= 4:
                return ('bet', round(pot * 0.75, 2), f"{desc} - multiway value")
            if strength == 3:
                return ('bet', round(pot * 0.65, 2), f"{desc} - multiway value")
            if combo_draw:
                return ('bet', round(pot * 0.60, 2), "combo draw - multiway semi-bluff")
            return ('check', 0, f"{desc} - check multiway")
        
        # Strong hands
        if strength >= 5:
            return ('bet', round(pot * 1.0, 2), f"{desc} - bet 100%")
        if strength == 4:
            return ('bet', round(pot * 0.75, 2), f"{desc} - bet 75%")
        if strength == 3:
            return ('bet', round(pot * 0.70, 2), f"{desc} - bet 70%")
        
        # Overpair - bet for value
        if hand_info['is_overpair']:
            size = 0.65 if street == 'flop' else (0.60 if street == 'turn' else 0.50)
            return ('bet', round(pot * size, 2), f"{desc} - overpair value bet")
        
        # Underpair to ace - check-call
        if hand_info['is_underpair_to_ace']:
            return ('check', 0, f"{desc} - check (ace on board)")
        
        # Top pair good kicker
        if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
            if is_dry:
                size = 0.33 if street == 'flop' else 0.50
            else:
                size = 0.55 if street == 'flop' else 0.60
            if street != 'river':
                return ('bet', round(pot * size, 2), f"{desc} - value bet")
            return ('check', 0, f"{desc} - check river")
        
        # Top pair weak kicker - c-bet flop only
        if hand_info['has_top_pair'] and street == 'flop':
            size = 0.30 if is_dry else 0.50
            return ('bet', round(pot * size, 2), f"{desc} - c-bet")
        
        # Draws - semi-bluff with equity
        if combo_draw:
            return ('bet', round(pot * 0.65, 2), "combo draw - semi-bluff")
        if hand_info.get('has_flush_draw') and is_aggressor and street == 'flop':
            return ('bet', round(pot * 0.50, 2), "flush draw - semi-bluff")
        if hand_info.get('has_straight_draw') and is_aggressor and street == 'flop':
            return ('bet', round(pot * 0.45, 2), "straight draw - semi-bluff")
        
        # C-bet air on dry boards only
        if is_aggressor and street == 'flop' and is_dry and random.random() < 0.55:
            return ('bet', round(pot * 0.30, 2), "c-bet dry board")
        
        return ('check', 0, f"{desc} - check")
    
    # Facing bet
    if strength >= 6:
        return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
    if strength >= 5:
        return ('raise', round(to_call * 2.5, 2), f"{desc} - raise strong")
    if strength == 4:
        return ('raise', round(to_call * 2.5, 2), f"{desc} - raise set/trips")
    if strength == 3:
        return ('call', 0, f"{desc} - call two pair")
    
    # Overpair facing bet - call down
    if hand_info['is_overpair']:
        if street != 'river':
            return ('call', 0, f"{desc} - call {street}")
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.35:
            return ('call', 0, f"{desc} - call small river")
        return ('fold', 0, f"{desc} - fold big river")
    
    # Underpair to ace - call flop, fold later
    if hand_info['is_underpair_to_ace']:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.25:
            return ('call', 0, f"{desc} - call small bet")
        return ('fold', 0, f"{desc} - fold (ace on board)")
    
    # Top pair good kicker - call flop/turn
    if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
        if street in ['flop', 'turn']:
            return ('call', 0, f"{desc} - call {street}")
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.40:
            return ('call', 0, f"{desc} - call small river")
        return ('fold', 0, f"{desc} - fold big river")
    
    # Top pair weak kicker - call flop only
    if hand_info['has_top_pair']:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        return ('fold', 0, f"{desc} - fold {street}")
    
    # Any pair - call flop
    if hand_info['has_any_pair'] and street == 'flop':
        return ('call', 0, f"{desc} - call flop")
    
    # Draws - conservative thresholds (villain has something)
    pot_odds = to_call / (pot + to_call) if pot > 0 else 1
    if hand_info.get('has_flush_draw'):
        threshold = 0.41 if hand_info.get('is_nut_flush_draw') else 0.25
        if pot_odds <= threshold:
            return ('call', 0, f"{'nut ' if hand_info.get('is_nut_flush_draw') else ''}flush draw - call")
    if has_oesd and pot_odds <= 0.22:
        return ('call', 0, "OESD - call")
    if has_gutshot and pot_odds <= 0.12:
        return ('call', 0, "gutshot - call")
    
    return ('fold', 0, f"{desc} - fold")


def _postflop_sonnet(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                     strength, desc, draws, combo_draw, has_flush_draw, has_oesd,
                     is_overpair, board_has_ace, is_underpair_to_ace=False, is_multiway=False):
    """
    Sonnet/Kiro_optimal postflop: Bigger value bets, overpair logic.
    Uses analyze_hand() for all hand property checks.
    """
    hand_info = analyze_hand(hole_cards, board)
    
    s = {
        'flop': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.80, 'tptk': 0.75, 'tpgk': 0.70, 'tpwk': 0.65, 'overpair': 0.70},
        'turn': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.80, 'tptk': 0.70, 'tpgk': 0.60, 'tpwk': 0.0, 'overpair': 0.60},
        'river': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.80, 'tptk': 0.60, 'tpgk': 0.50, 'tpwk': 0.0, 'overpair': 0.50},
    }.get(street, {})
    
    if to_call == 0 or to_call is None:
        # Multiway: only bet strong value + strong draws
        if is_multiway:
            if strength >= 4:
                return ('bet', round(pot * s.get('set', 0.85), 2), f"{desc} - multiway value")
            if strength == 3:
                return ('bet', round(pot * 0.70, 2), f"{desc} - multiway value")
            if combo_draw:
                return ('bet', round(pot * 0.65, 2), "combo draw - multiway semi-bluff")
            return ('check', 0, f"{desc} - check multiway")
        
        # Strong hands
        if strength >= 5:
            return ('bet', round(pot * s.get('nuts', 1.0), 2), f"{desc} - bet 100%")
        if strength == 4:
            return ('bet', round(pot * s.get('set', 0.85), 2), f"{desc} - bet 85%")
        if strength == 3:
            return ('bet', round(pot * s.get('twopair', 0.80), 2), f"{desc} - bet 80%")
        
        # Underpair to ace - check-call only
        if hand_info['is_underpair_to_ace']:
            return ('check', 0, f"{desc} - check (pocket pair below ace)")
        
        # True overpair
        if hand_info['is_overpair']:
            return ('bet', round(pot * s.get('overpair', 0.70), 2), f"{desc} overpair - bet")
        
        # Top pair good kicker
        if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
            return ('bet', round(pot * s.get('tptk', 0.75), 2), f"{desc} - value bet")
        
        # Top pair medium kicker
        if hand_info['has_top_pair'] and hand_info.get('kicker_val', 0) >= 6:  # 8+
            return ('bet', round(pot * s.get('tpgk', 0.70), 2), f"{desc} - value bet")
        
        # Top pair weak kicker - bet flop only
        if hand_info['has_top_pair'] and street == 'flop':
            return ('bet', round(pot * s.get('tpwk', 0.65), 2), f"{desc} - bet flop")
        
        # Draws
        if combo_draw:
            return ('bet', round(pot * 0.70, 2), "combo draw - semi-bluff 70%")
        if hand_info.get('has_flush_draw') and is_aggressor:
            return ('bet', round(pot * 0.50, 2), "flush draw - semi-bluff")
        
        return ('check', 0, f"{desc} - check")
    
    # Facing bet
    if strength >= 6:
        return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
    if strength >= 5:
        return ('raise', round(to_call * 2.5, 2), f"{desc} - raise strong")
    if strength == 4:
        return ('raise', round(to_call * 2.5, 2), f"{desc} - raise set/trips")
    if strength == 3:
        return ('call', 0, f"{desc} - call two pair")
    
    # Underpair to ace - check-call
    if hand_info['is_underpair_to_ace']:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop (pocket pair below ace)")
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.35:
            return ('call', 0, f"{desc} - call small bet")
        return ('fold', 0, f"{desc} - fold big bet (ace on board)")
    
    # True overpair facing bet
    if hand_info['is_overpair']:
        if street != 'river':
            return ('call', 0, f"{desc} overpair - call")
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.35:
            return ('call', 0, f"{desc} overpair - call small river")
        return ('fold', 0, f"{desc} overpair - fold big river")
    
    # Top pair good kicker - call flop/turn
    if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
        if street in ['flop', 'turn']:
            return ('call', 0, f"{desc} - call {street}")
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.40:
            return ('call', 0, f"{desc} - call small river")
        return ('fold', 0, f"{desc} - fold big river bet")
    
    # Top pair weak kicker - call flop only
    if hand_info['has_top_pair']:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        return ('fold', 0, f"{desc} - fold {street}")
    
    # Middle pair: check-call once, fold turn
    if hand_info['has_middle_pair']:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop once")
        return ('fold', 0, f"{desc} - fold {street}")
    
    # Any pair - call flop
    if hand_info['has_any_pair'] and street == 'flop':
        return ('call', 0, f"{desc} - call flop")
    
    # Draws - conservative thresholds (villain has something)
    pot_odds = to_call / (pot + to_call) if pot > 0 else 1
    if hand_info.get('has_flush_draw'):
        threshold = 0.41 if hand_info.get('is_nut_flush_draw') else 0.25
        if pot_odds <= threshold:
            return ('call', 0, f"{'nut ' if hand_info.get('is_nut_flush_draw') else ''}flush draw - call")
    if hand_info.get('has_straight_draw'):
        if pot_odds <= 0.22:
            return ('call', 0, "straight draw - call")
    
    return ('fold', 0, f"{desc} - fold")


def _postflop_sonnet_max(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                         strength, desc, draws, combo_draw, has_flush_draw, has_oesd, has_any_draw):
    """
    SONNET_MAX: Sonnet postflop + Session 33 fixes for 2NL fish-heavy tables.
    Uses analyze_hand() for all hand property checks.
    """
    hand_info = analyze_hand(hole_cards, board)
    
    is_paired_board = hand_info['has_board_pair']
    # Double paired = two different pairs on board
    from collections import Counter
    board_rank_counts = Counter([c[0] for c in board]) if board else Counter()
    is_double_paired = sum(1 for c in board_rank_counts.values() if c >= 2) >= 2
    
    pot_odds = to_call / (pot + to_call) if to_call and pot > 0 else 0
    is_big_bet = to_call and pot > 0 and to_call >= pot * 0.6
    
    s = {
        'flop': {'nuts': 1.0, 'set': 0.80, 'twopair': 0.70, 'tptk': 0.65, 'tpgk': 0.55, 'tpwk': 0.45, 'overpair': 0.60},
        'turn': {'nuts': 1.0, 'set': 0.80, 'twopair': 0.70, 'tptk': 0.55, 'tpgk': 0.45, 'tpwk': 0.0, 'overpair': 0.50},
        'river': {'nuts': 1.0, 'set': 0.80, 'twopair': 0.65, 'tptk': 0.45, 'tpgk': 0.0, 'tpwk': 0.0, 'overpair': 0.40},
    }.get(street, {})
    
    if to_call == 0 or to_call is None:
        # === BETTING ===
        if strength >= 5:
            return ('bet', round(pot * s.get('nuts', 1.0), 2), f"{desc} - bet for value")
        if strength == 4:
            return ('bet', round(pot * s.get('set', 0.80), 2), f"{desc} - value bet")
        if strength == 3:
            # Weak two pair on river - check
            if hand_info['two_pair_type'] == 'pocket_under_board' and street == 'river':
                return ('check', 0, f"{desc} - check (weak two pair)")
            return ('bet', round(pot * s.get('twopair', 0.70), 2), f"{desc} - value bet")
        
        # Overpair
        if hand_info['is_overpair']:
            if is_paired_board:
                return ('check', 0, f"{desc} - check (board paired)")
            return ('bet', round(pot * s.get('overpair', 0.60), 2), f"{desc} - value bet")
        
        # Underpair to ace
        if hand_info['is_underpair_to_ace']:
            return ('check', 0, f"{desc} - check underpair")
        
        # Top pair good kicker
        if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
            if is_paired_board and street != 'flop':
                return ('check', 0, f"{desc} - check (board paired)")
            return ('bet', round(pot * s.get('tptk', 0.65), 2), f"{desc} - value bet")
        
        # Top pair medium kicker
        if hand_info['has_top_pair'] and hand_info.get('kicker_val', 0) >= 6:
            if street != 'river':
                return ('bet', round(pot * s.get('tpgk', 0.55), 2), f"{desc} - value bet")
            return ('check', 0, f"{desc} - check river")
        
        # Top pair weak kicker - bet flop only
        if hand_info['has_top_pair'] and street == 'flop':
            return ('bet', round(pot * s.get('tpwk', 0.45), 2), f"{desc} - small bet")
        
        # Draws
        if combo_draw:
            return ('bet', round(pot * 0.60, 2), "combo draw - semi-bluff")
        if hand_info.get('has_flush_draw') and street in ['flop', 'turn']:
            return ('bet', round(pot * 0.50, 2), "flush draw - semi-bluff")
        if hand_info.get('has_straight_draw') and street == 'flop':
            return ('bet', round(pot * 0.45, 2), "straight draw - semi-bluff")
        
        return ('check', 0, f"{desc} - check")
    
    else:
        # === FACING BET ===
        
        # High card on paired board = FOLD
        if strength <= 1 and is_paired_board:
            return ('fold', 0, f"{desc} - fold (high card on paired board)")
        
        # Double paired board = need full house+
        if is_double_paired and strength < 7:
            return ('fold', 0, f"{desc} - fold (double paired board)")
        
        # Strong hands - RAISE for value
        if strength >= 6:
            return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
        if strength >= 5:
            return ('raise', round(to_call * 2.5, 2), f"{desc} - raise strong")
        if strength == 4:
            return ('raise', round(to_call * 2.5, 2), f"{desc} - raise set/trips")
        if strength == 3:
            # Weak two pair vs big bet on river
            if hand_info['two_pair_type'] == 'pocket_under_board' and street == 'river' and is_big_bet:
                return ('fold', 0, f"{desc} - fold (weak two pair vs big bet)")
            return ('call', 0, f"{desc} - call")
        
        # Top pair good kicker
        if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
            if street in ['flop', 'turn']:
                return ('call', 0, f"{desc} - call {street}")
            if pot_odds <= 0.35:
                return ('call', 0, f"{desc} - call small river")
            return ('fold', 0, f"{desc} - fold big river")
        
        # Top pair / overpair
        if hand_info['has_top_pair'] or hand_info['is_overpair']:
            if street == 'flop':
                return ('call', 0, f"{desc} - call flop")
            if street == 'turn' and pot_odds <= 0.35:
                return ('call', 0, f"{desc} - call small turn")
            return ('fold', 0, f"{desc} - fold")
        
        # Middle/bottom pair - call flop only
        if hand_info['has_any_pair']:
            if street == 'flop' and pot_odds <= 0.30:
                return ('call', 0, f"{desc} - call flop")
            return ('fold', 0, f"{desc} - fold")
        
        # Draws - conservative thresholds (villain has something)
        if hand_info.get('has_flush_draw'):
            threshold = 0.41 if hand_info.get('is_nut_flush_draw') else 0.25
            if pot_odds <= threshold:
                return ('call', 0, f"{'nut ' if hand_info.get('is_nut_flush_draw') else ''}flush draw - call")
        if hand_info.get('has_straight_draw') and pot_odds <= 0.22:
            return ('call', 0, "straight draw - call")
        
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
        
        # SB defend - 3bet or call strong hands (SB is OOP so tighter than BB)
        if position == 'SB':
            sb_defend = strategy.get('sb_defend', strategy.get('call_open_ip', set()))
            if hand in sb_defend:
                return ('call', f'{hand} SB defend')
        
        # Call IP (CO, BTN) or BB defend
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
