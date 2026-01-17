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
    # Double-paired board: two different pairs on board (e.g., 3399, 7722)
    is_double_paired_board = len(board_pairs) >= 2
    
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
    
    # Underpair: pocket pair lower than highest board card
    is_underpair = is_pocket_pair and board_vals and pocket_val < max(board_vals)
    
    # Underpair to ace: pocket pair but ace on board (legacy, kept for compatibility)
    has_ace_on_board = 'A' in board_ranks
    is_underpair_to_ace = is_pocket_pair and has_ace_on_board and pocket_val < 12
    
    # Top pair detection
    top_board_val = board_vals[0] if board_vals else None
    has_top_pair = top_board_val is not None and any(RANK_VAL[r] == top_board_val for r in hero_ranks)
    
    # Kicker for top pair
    if has_top_pair:
        other_ranks = [RANK_VAL[r] for r in hero_ranks if RANK_VAL[r] != top_board_val]
        kicker_val = max(other_ranks) if other_ranks else hero_vals[0]
        has_good_kicker = kicker_val >= 8  # T or higher (T=8 in RANK_VAL)
    else:
        kicker_val = None
        has_good_kicker = False
    
    # Two pair analysis - hero must contribute to at least one pair
    num_pairs = len(our_pairs)
    has_two_pair = num_pairs >= 2 and hero_has_pair
    
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
        board_sorted_asc = sorted(board_vals)
        mid_idx = len(board_sorted_asc) // 2  # Middle index
        for r in hero_ranks:
            rv = RANK_VAL[r]
            if r in board_ranks:
                # Bottom pair = pairs with lower half of board
                # Middle pair = pairs with upper half (but not top)
                if rv < board_sorted_asc[mid_idx]:
                    has_bottom_pair = True
                else:
                    has_middle_pair = True
    
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
    
    # Board texture analysis - straight possibilities
    board_straight_combos = []
    if len(board_vals) >= 3:
        # Check all possible 2-card combinations that could make a straight
        board_vals_sorted = sorted(board_vals)
        # For each possible straight (5 consecutive cards), check if board has 3+ cards
        for low in range(0, 9):  # Straights from A-5 (low=0) to T-A (low=8)
            straight = list(range(low, low + 5))
            if low == 0:  # Wheel (A-2-3-4-5)
                straight = [12, 0, 1, 2, 3]
            board_in_straight = [v for v in board_vals if v in straight]
            if len(board_in_straight) >= 3:
                # Find what 2-card combos complete this straight
                missing = [v for v in straight if v not in board_vals]
                if len(missing) == 2:
                    # Need both missing cards
                    combo = ''.join([RANKS[v] for v in sorted(missing, reverse=True)])
                    if combo not in board_straight_combos:
                        board_straight_combos.append(combo)
    
    # Board texture analysis - flush possibilities
    board_flush_suit = None
    if len(board_suits) >= 3:
        board_suit_counts = Counter(board_suits)
        for suit, count in board_suit_counts.items():
            if count >= 3:
                board_flush_suit = suit
                break
    
    # Compute strength, desc, kicker (replaces evaluate_hand)
    strength, desc, kicker = 1, "high card", hero_vals[0]
    
    # Check for quads
    if our_quads:
        strength, desc, kicker = 8, f"quads {our_quads[0]}s", RANK_VAL[our_quads[0]]
    # Full house (trips + another pair)
    elif has_set and has_two_pair:
        strength, desc, kicker = 7, "full house", pocket_val
    elif has_trips and has_two_pair:
        strength, desc, kicker = 7, "full house", RANK_VAL[our_trips[0]]
    # Full house (board trips + hero pair)
    elif board_trips and is_pocket_pair:
        strength, desc, kicker = 7, "full house", RANK_VAL[board_trips[0]]
    # Flush
    elif has_flush:
        flush_suit = [s for s, c in suit_counts.items() if c >= 5][0]
        flush_high = max(RANK_VAL[c[0]] for c in (hole_cards + board) if c[1] == flush_suit)
        strength, desc, kicker = 6, "flush", flush_high
    # Straight - find the highest straight we can make
    elif has_straight:
        all_vals = sorted(set(hero_vals + board_vals))
        straight_high = 0
        # Check for wheel (A2345) - high card is 5 (val=3)
        if {12, 0, 1, 2, 3}.issubset(set(all_vals)):
            straight_high = 3  # 5-high
        # Find highest 5-card straight
        for i in range(len(all_vals) - 4):
            window = all_vals[i:i+5]
            if window[-1] - window[0] == 4:
                straight_high = max(straight_high, window[-1])
        strength, desc, kicker = 5, "straight", straight_high
    # Set
    elif has_set:
        strength, desc, kicker = 4, f"set of {our_trips[0]}s", RANK_VAL[our_trips[0]]
    # Trips
    elif has_trips:
        strength, desc, kicker = 4, f"trips {our_trips[0]}s", RANK_VAL[our_trips[0]]
    # Two pair
    elif has_two_pair:
        pair_vals = sorted([RANK_VAL[r] for r in our_pairs], reverse=True)
        if two_pair_type == 'pocket_over_board':
            desc = "two pair (pocket+board strong)"
        elif two_pair_type == 'pocket_under_board':
            desc = "two pair (pocket+board weak)"
        elif two_pair_type == 'both_cards_hit':
            desc = "two pair"
        elif board_pair_val and board_pair_val >= 8:
            desc = "two pair (board paired)"
        else:
            desc = "two pair (low board pair)"
        strength, kicker = 3, pair_vals[0]
    # Overpair
    elif is_overpair:
        strength, desc, kicker = 2, f"overpair {hero_ranks[0]}{hero_ranks[0]}", pocket_val
    # Underpair to ace
    elif is_underpair_to_ace and pocket_val >= 8:  # TT+
        strength, desc, kicker = 2, f"underpair {hero_ranks[0]}{hero_ranks[0]} (ace on board)", pocket_val
    # Top pair
    elif has_top_pair:
        if has_good_kicker:
            strength, desc, kicker = 2, "top pair good kicker", top_board_val * 100 + kicker_val
        else:
            strength, desc, kicker = 2, "top pair weak kicker", top_board_val * 100 + (kicker_val or 0)
    # Pocket pair (underpair)
    elif is_pocket_pair:
        strength, desc, kicker = 2, f"pocket pair {hero_ranks[0]}{hero_ranks[0]}", pocket_val
    # Middle pair
    elif has_middle_pair:
        strength, desc, kicker = 2, "middle pair", hero_vals[0]
    # Bottom pair
    elif has_bottom_pair:
        strength, desc, kicker = 2, "bottom pair", hero_vals[0]
    # Any other pair we contribute to
    elif has_any_pair:
        strength, desc, kicker = 2, "pair", hero_vals[0]
    # High card with board pair
    elif has_board_pair:
        strength, desc, kicker = 1, "high card (board paired)", hero_vals[0]
    
    return {
        'valid': True,
        'strength': strength,
        'desc': desc,
        'kicker': kicker,
        'is_pocket_pair': is_pocket_pair,
        'pocket_val': pocket_val,
        'has_board_pair': has_board_pair,
        'board_pair_val': board_pair_val,
        'is_double_paired_board': is_double_paired_board,
        'is_overpair': is_overpair,
        'is_underpair': is_underpair,
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
        'board_straight_combos': board_straight_combos,
        'board_flush_suit': board_flush_suit,
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
    'kiro_lord': {
        # Same preflop as kiro_optimal, improved postflop
        'name': 'Kiro Lord Strategy',
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
    # OPTIMAL_STATS: GTO-inspired strategy targeting winning player stats
    # VPIP 21%, PFR 18%, Gap 3%, 3-bet 8%, 4-bet 25%, AF 2.5, C-bet 70%
    'optimal_stats': {
        'name': 'Optimal Stats',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AJo+'),
            'MP': expand_range('66+,A9s+,A5s-A3s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T6s+,95s+,85s+,74s+,64s+,54s,A7o+,K9o+,QTo+,JTo'),
            'SB': expand_range('33+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,A8o+,KTo+,QJo'),
        },
        # VERY wide 3-bet ranges (target 8% overall) - 3-bet vs ALL positions
        '3bet_vs': {
            'UTG': expand_range('99+,AQs+,AKo,AJs'),
            'MP': expand_range('88+,AJs+,AKo,AQo,KQs,QJs'),
            'CO': expand_range('77+,ATs+,AJo+,KQs,KJs,QJs,JTs'),
            'BTN': expand_range('66+,A9s+,ATo+,KJs+,KQo,QJs,JTs,T9s'),
        },
        # Wide 3-bet bluffs vs late position (always 3-bet these)
        '3bet_bluff': expand_range('A5s-A2s,K9s-K5s,Q9s-Q7s,J9s-J7s,T9s-T7s,98s-97s,87s-86s,76s-75s,65s,54s'),
        # Minimal calling - prefer 3-bet or fold (low gap)
        'call_open_ip': expand_range('TT-77,AQs-ATs,KQs-KJs,QJs,JTs'),
        # BB defend 40%
        'bb_defend': expand_range('99-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A9o+,KJo,QJo'),
        # Wider call 3-bet
        'call_3bet': expand_range('QQ,JJ,TT,99,AKo,AQs,AQo,AJs,KQs'),
        # Wide 4-bet (target 25% of opens facing 3-bet)
        '4bet': expand_range('KK+,AKs,AKo,AQs,AQo'),
        # Flag to always 3-bet bluff (not 40%)
        '3bet_bluff_always': True,
    },
}

# Player archetypes - CALIBRATED TO REAL 2NL DATA (1036 hands, 122 opponents)
# Real data: FISH 55%, NIT 23%, TAG 12%, LAG 7%, MANIAC 3%

# FISH: VPIP 25.5%, PFR 14.6%, Limp 1.4%, AF 1.14
# Loose passive - plays many hands, rarely raises, calls a lot postflop
STRATEGIES['fish'] = {
    'name': 'Fish',
    'open': {
        # Even wider ranges to hit 25% VPIP
        'UTG': expand_range('55+,A6s+,K9s+,Q9s+,J9s+,T9s,98s,A9o+,KJo+,QJo'),
        'MP': expand_range('44+,A4s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,A7o+,KTo+,QTo+,JTo'),
        'CO': expand_range('33+,A2s+,K5s+,Q6s+,J7s+,T7s+,96s+,85s+,74s+,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
        'BTN': expand_range('22+,A2s+,K3s+,Q5s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A3o+,K8o+,Q9o+,J9o+,T9o,98o'),
        'SB': expand_range('33+,A3s+,K6s+,Q7s+,J7s+,T7s+,96s+,86s+,76s,65s,A5o+,K9o+,QTo+,JTo'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs'), 'MP': expand_range('QQ+,AKs'), 'CO': expand_range('QQ+,AKs'), 'BTN': expand_range('QQ+,AKs')},
    '3bet_bluff': set(),
    'call_open_ip': expand_range('22+,A2s+,K5s+,Q7s+,J8s+,T8s+,97s+,87s,76s,65s,A5o+,K9o+,QTo+,JTo'),
    'bb_defend': expand_range('22+,A2s+,K5s+,Q7s+,J8s+,T8s+,97s+,87s,76s,65s,A5o+,K9o+,QTo+,JTo,T9o'),
    'call_3bet': expand_range('QQ,JJ,TT,AKs,AKo,AQs,AQo,AJs,KQs'),
    '4bet': expand_range('AA,KK'),
    'call_wide': True,
    'limp_pct': 0.06,  # 1.4% of total actions = ~6% of opens
}

# NIT: VPIP 10.7%, PFR 7.5%, AF 1.32
# Very tight - only plays premium hands
STRATEGIES['nit'] = {
    'name': 'Nit',
    'open': {
        # Wider ranges to hit 10.7% VPIP
        'UTG': expand_range('88+,AJs+,KQs,AQo+'),
        'MP': expand_range('77+,ATs+,KJs+,QJs,AJo+,KQo'),
        'CO': expand_range('66+,A9s+,KTs+,QTs+,JTs,ATo+,KJo+,QJo'),
        'BTN': expand_range('55+,A7s+,K9s+,Q9s+,J9s+,T9s,98s,A9o+,KTo+,QJo'),
        'SB': expand_range('66+,A8s+,KTs+,QTs+,JTs,ATo+,KJo+'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs'), 'MP': expand_range('QQ+,AKs'), 'CO': expand_range('QQ+,AKs,AKo'), 'BTN': expand_range('QQ+,AKs,AKo')},
    '3bet_bluff': set(),
    'call_open_ip': expand_range('JJ-66,AQs-ATs,KQs,KJs'),
    'bb_defend': expand_range('TT-44,AQs-A8s,KQs,KJs,QJs,JTs'),
    'call_3bet': expand_range('QQ,AKs'),
    '4bet': expand_range('KK+'),
    'fold_wide': True,
}

# TAG: VPIP 20.2%, PFR 14.7%, AF 4.79
# Tight aggressive - selective but aggressive when playing
STRATEGIES['tag'] = {
    'name': 'TAG',
    'open': {
        # Wider ranges to hit 20% VPIP
        'UTG': expand_range('55+,A8s+,K9s+,Q9s+,J9s+,T9s,ATo+,KJo+,QJo'),
        'MP': expand_range('44+,A6s+,K8s+,Q8s+,J8s+,T8s+,97s+,87s,76s,A9o+,KTo+,QTo+,JTo'),
        'CO': expand_range('33+,A4s+,K6s+,Q7s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A7o+,K9o+,QTo+,JTo,T9o'),
        'BTN': expand_range('22+,A2s+,K4s+,Q6s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A5o+,K8o+,Q9o+,J9o+,T9o,98o'),
        'SB': expand_range('33+,A3s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,A7o+,K9o+,QTo+,JTo'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo'), 'MP': expand_range('QQ+,AKs,AKo'), 'CO': expand_range('JJ+,AQs+,AKo'), 'BTN': expand_range('TT+,AQs+,AKo')},
    '3bet_bluff': expand_range('A5s-A4s'),
    'call_open_ip': expand_range('JJ-44,AQs-A9s,KQs-KTs,QJs,JTs,T9s,98s'),
    'bb_defend': expand_range('TT-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A9o+,KJo,QJo'),
    'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
    '4bet': expand_range('KK+,AKs'),
}

# LAG: VPIP 28.7%, PFR 23.5%, AF 6.75
# Loose aggressive - plays many hands aggressively
STRATEGIES['lag'] = {
    'name': 'LAG',
    'open': {
        # Wider ranges to hit 28.7% VPIP
        'UTG': expand_range('44+,A5s+,K8s+,Q9s+,J9s+,T8s+,97s+,87s,76s,A8o+,KTo+,QJo'),
        'MP': expand_range('33+,A3s+,K6s+,Q7s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A6o+,K9o+,QTo+,JTo,T9o'),
        'CO': expand_range('22+,A2s+,K4s+,Q5s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A4o+,K8o+,Q9o+,J9o+,T9o,98o'),
        'BTN': expand_range('22+,A2s+,K2s+,Q3s+,J5s+,T5s+,94s+,83s+,73s+,62s+,52s+,42s+,A2o+,K6o+,Q8o+,J8o+,T8o+,98o,87o'),
        'SB': expand_range('22+,A2s+,K4s+,Q6s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A4o+,K8o+,Q9o+,J9o+,T9o'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo,JJ'), 'MP': expand_range('JJ+,AKs,AKo,AQs,TT'), 'CO': expand_range('TT+,AQs+,AKo,AJs'), 'BTN': expand_range('TT+,AQs+,AKo,AJs,KQs')},
    '3bet_bluff': expand_range('A5s-A2s,K9s-K7s,Q9s,J9s,T9s,98s,87s,76s'),
    'call_open_ip': expand_range('TT-22,AJs-A7s,KQs-KTs,QJs-QTs,JTs,T9s,98s,87s,76s'),
    'bb_defend': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,54s,A7o+,KTo+,QTo+,JTo,T9o'),
    'call_3bet': expand_range('JJ,TT,AKo,AQs,AQo,KQs'),
    '4bet': expand_range('QQ+,AKs'),
}

# MANIAC: VPIP 48.6%, PFR 39.2%, AF 7.00
# Very aggressive - plays almost half of hands, bets relentlessly
STRATEGIES['maniac'] = {
    'name': 'Maniac',
    'open': {
        # Very wide ranges to hit 48.6% VPIP
        'UTG': expand_range('33+,A3s+,K6s+,Q7s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
        'MP': expand_range('22+,A2s+,K4s+,Q5s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A3o+,K7o+,Q9o+,J9o+,T9o,98o'),
        'CO': expand_range('22+,A2s+,K2s+,Q3s+,J4s+,T5s+,94s+,83s+,73s+,62s+,52s+,42s+,A2o+,K5o+,Q8o+,J8o+,T8o+,98o,87o'),
        'BTN': expand_range('22+,A2s+,K2s+,Q2s+,J3s+,T4s+,93s+,82s+,72s+,62s+,52s+,42s+,32s,A2o+,K3o+,Q6o+,J7o+,T7o+,97o+,87o,76o'),
        'SB': expand_range('22+,A2s+,K2s+,Q4s+,J5s+,T5s+,94s+,83s+,73s+,62s+,52s+,42s+,A2o+,K5o+,Q8o+,J8o+,T8o+,98o,87o'),
    },
    '3bet_vs': {'UTG': expand_range('TT+,AQs+,AKo,AJs,KQs'), 'MP': expand_range('99+,AJs+,AKo,AQo,KQs,QJs'), 'CO': expand_range('88+,ATs+,AJo+,KQs,KJs,QJs,JTs'), 'BTN': expand_range('77+,A9s+,ATo+,KJs+,KQo,QJs,JTs,T9s')},
    '3bet_bluff': expand_range('A5s-A2s,K9s-K6s,Q9s-Q8s,J9s,T9s,98s,87s,76s,65s,54s'),
    'call_open_ip': expand_range('TT-22,AJs-A5s,KQs-K9s,QJs-Q9s,JTs-J9s,T9s,98s,97s,87s,76s,AQo,AJo,ATo,KQo,KJo,QJo'),
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
        hero_info = analyze_hand(hole_cards, full_board)
        hero_rank = (hero_info['strength'], hero_info['kicker'])
        opp_ranks = []
        for oh in opp_hands:
            oi = analyze_hand(oh, full_board)
            opp_ranks.append((oi['strength'], oi['kicker']))
        
        best_opp = max(opp_ranks)
        
        if hero_rank > best_opp:
            wins += 1
        elif hero_rank == best_opp:
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
    info = analyze_hand(hole_cards, board)
    rank, desc = info['strength'], info['desc']
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
                    num_opponents: int = 1, bb_size: float = 0.05,
                    is_facing_raise: bool = False) -> Tuple[str, float, str]:
    """
    Postflop decision based on strategy file rules.
    Returns (action, bet_size, reasoning).
    archetype: 'fish', 'nit', 'tag', 'lag' for special behavior
    strategy: 'gpt3', 'gpt4', 'sonnet', 'kiro_optimal' for bot-specific logic
    num_opponents: number of active opponents (1=heads-up, 2+=multiway)
    """
    hand_info = analyze_hand(hole_cards, board)
    strength, desc = hand_info['strength'], hand_info['desc']
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
    
    # ARCHETYPES TUNED TO REAL 2NL DATA (1036 hands, 122 opponents):
    # FISH: Check 43%, Bet 17.5%, Call 17.7%, Fold 18.8%, AF 1.14
    # NIT: Check 50.5%, Bet 14.9%, Call 13.5%, Fold 18.1%, AF 1.32
    # TAG: Check 35.4%, Bet 35.8%, Call 7.8%, Fold 19.3%, AF 4.79
    # LAG: Check 39.2%, Bet 36.0%, Call 6.4%, Fold 11.2%, AF 6.75
    # MANIAC: Check 25%, Bet 47.5%, Call 7.5%, Fold 15%, AF 7.00
    
    # Get hand info for archetypes (no string matching)
    hand_info = analyze_hand(hole_cards, board)
    
    # FISH: Target Check 40.7%, Bet 20.7%, Call 14.1%, Fold 23.0%, AF 1.58
    # Fish play loosely but decisions still depend on hand strength
    if archetype == 'fish':
        pot_pct = to_call / (pot + to_call) if to_call and pot else 0
        if to_call == 0 or to_call is None:
            # First to act - bet based on hand strength
            if strength >= 4:  # Sets+
                return ('bet', round(pot * 0.62, 2), f"{desc} - fish bets")
            if strength >= 3:  # Two pair
                return ('bet', round(pot * 0.55, 2), f"{desc} - fish bets two pair")
            if hand_info.get('has_top_pair'):
                if hand_info.get('has_good_kicker'):
                    return ('bet', round(pot * 0.50, 2), f"{desc} - fish bets TPGK")
                # TPWK - sometimes bet, sometimes check
                if random.random() < 0.40:
                    return ('bet', round(pot * 0.45, 2), f"{desc} - fish bets top pair")
                return ('check', 0, f"{desc} - fish checks top pair")
            if hand_info.get('is_overpair'):
                return ('bet', round(pot * 0.50, 2), f"{desc} - fish bets overpair")
            if strength >= 2:  # Weaker pairs - mostly check
                if random.random() < 0.15:
                    return ('bet', round(pot * 0.40, 2), f"{desc} - fish bets weak pair")
                return ('check', 0, f"{desc} - fish checks pair")
            if has_any_draw:
                if hand_info.get('is_nut_flush_draw') or hand_info.get('has_oesd'):
                    if random.random() < 0.25:
                        return ('bet', round(pot * 0.45, 2), f"{desc} - fish semi-bluffs")
                return ('check', 0, f"{desc} - fish checks draw")
            # Air - rarely bluff
            if random.random() < 0.03:
                return ('bet', round(pot * 0.35, 2), f"{desc} - fish donk bets air")
            return ('check', 0, "fish checks")
        else:
            # Facing bet - decisions based on hand strength vs bet size
            if strength >= 4:
                return ('call', 0, f"{desc} - fish calls strong")
            if strength >= 3:
                return ('call', 0, f"{desc} - fish calls two pair")
            if hand_info.get('has_top_pair'):
                if hand_info.get('has_good_kicker'):
                    if pot_pct > 0.50:
                        return ('fold', 0, f"{desc} - fish folds TPGK to big bet")
                    return ('call', 0, f"{desc} - fish calls TPGK")
                # TPWK - fold to smaller bets
                if pot_pct > 0.35:
                    return ('fold', 0, f"{desc} - fish folds TPWK")
                return ('call', 0, f"{desc} - fish calls top pair")
            if hand_info.get('is_overpair'):
                if pot_pct > 0.45:
                    return ('fold', 0, f"{desc} - fish folds overpair to big bet")
                return ('call', 0, f"{desc} - fish calls overpair")
            if strength >= 2:  # Weaker pairs
                if pot_pct > 0.30:
                    return ('fold', 0, f"{desc} - fish folds weak pair")
                if random.random() < 0.50:  # Increased from 0.35
                    return ('call', 0, f"{desc} - fish calls pair")
                return ('fold', 0, f"{desc} - fish folds pair")
            if has_any_draw:
                # Call draws with good odds
                if hand_info.get('is_nut_flush_draw') and pot_pct < 0.40:
                    return ('call', 0, f"{desc} - fish calls nut FD")
                if pot_pct < 0.25:
                    return ('call', 0, f"{desc} - fish calls draw")
                return ('fold', 0, f"{desc} - fish folds draw")
            return ('fold', 0, "fish folds")
    
    # NIT: Target Check 45.9%, Bet 16.9%, Call 18.6%, Fold 15.3%, AF 1.09
    # Nits are tight - only bet/call with strong hands
    if archetype == 'nit':
        pot_pct = to_call / (pot + to_call) if to_call and pot else 0
        if to_call == 0 or to_call is None:
            # First to act - only bet strong hands
            if strength >= 4:  # Sets+
                return ('bet', round(pot * 0.54, 2), f"{desc} - nit value bets")
            if strength >= 3:  # Two pair
                if hand_info.get('two_pair_type') == 'pocket_under_board':
                    return ('check', 0, f"{desc} - nit checks weak two pair")
                return ('bet', round(pot * 0.50, 2), f"{desc} - nit bets two pair")
            if hand_info.get('has_top_pair') and hand_info.get('has_good_kicker'):
                return ('bet', round(pot * 0.45, 2), f"{desc} - nit bets TPGK")
            if hand_info.get('is_overpair'):
                return ('bet', round(pot * 0.50, 2), f"{desc} - nit bets overpair")
            # Everything else - check (nits don't bluff much)
            return ('check', 0, "nit checks")
        else:
            # Facing bet - nits call with made hands, fold marginal
            if strength >= 4:
                if random.random() < 0.12:  # Occasionally raise nuts
                    return ('raise', round(to_call * 1.0, 2), f"{desc} - nit raises")
                return ('call', 0, f"{desc} - nit calls strong")
            if strength >= 3:
                if hand_info.get('two_pair_type') == 'pocket_under_board' and pot_pct > 0.40:
                    return ('fold', 0, f"{desc} - nit folds weak two pair")
                return ('call', 0, f"{desc} - nit calls two pair")
            if hand_info.get('has_top_pair'):
                if hand_info.get('has_good_kicker'):
                    if pot_pct > 0.55:
                        return ('fold', 0, f"{desc} - nit folds TPGK to big bet")
                    return ('call', 0, f"{desc} - nit calls TPGK")
                # TPWK - nits fold
                if pot_pct > 0.35:
                    return ('fold', 0, f"{desc} - nit folds TPWK")
                return ('call', 0, f"{desc} - nit calls top pair")
            if hand_info.get('is_overpair'):
                if pot_pct > 0.50:
                    return ('fold', 0, f"{desc} - nit folds overpair to big bet")
                return ('call', 0, f"{desc} - nit calls overpair")
            if strength >= 2:  # Weaker pairs - nits fold most
                if pot_pct > 0.35:
                    return ('fold', 0, f"{desc} - nit folds weak pair")
                if hand_info.get('has_middle_pair') and random.random() < 0.55:
                    return ('call', 0, f"{desc} - nit calls middle pair")
                if random.random() < 0.40:
                    return ('call', 0, f"{desc} - nit calls pair")
                return ('fold', 0, f"{desc} - nit folds pair")
            if has_any_draw:
                # Nits only call draws with good odds
                if hand_info.get('is_nut_flush_draw') and pot_pct < 0.35:
                    return ('call', 0, f"{desc} - nit calls nut FD")
                if pot_pct < 0.25:
                    return ('call', 0, f"{desc} - nit calls draw")
                return ('fold', 0, f"{desc} - nit folds draw")
            return ('fold', 0, f"{desc} - nit folds")
    
    # TAG: Target Check 43.5%, Bet 20.7%, Call 13.4%, Fold 19.4%, AF 1.77
    # TAGs are solid - bet value hands, fold marginal to aggression
    if archetype == 'tag':
        pot_pct = to_call / (pot + to_call) if to_call and pot else 0
        if to_call == 0 or to_call is None:
            # First to act - bet for value with strong hands
            if strength >= 4:  # Sets+
                return ('bet', round(pot * 0.68, 2), f"{desc} - tag value bets")
            if strength >= 3:  # Two pair
                if hand_info.get('two_pair_type') == 'pocket_under_board':
                    return ('check', 0, f"{desc} - tag checks weak two pair")
                return ('bet', round(pot * 0.60, 2), f"{desc} - tag bets two pair")
            if hand_info.get('has_top_pair'):
                if hand_info.get('has_good_kicker'):
                    return ('bet', round(pot * 0.55, 2), f"{desc} - tag bets TPGK")
                # TPWK - check more often
                if random.random() < 0.30:
                    return ('bet', round(pot * 0.45, 2), f"{desc} - tag bets top pair")
                return ('check', 0, f"{desc} - tag checks TPWK")
            if hand_info.get('is_overpair'):
                return ('bet', round(pot * 0.60, 2), f"{desc} - tag bets overpair")
            # Draws - semi-bluff with good draws
            if has_any_draw:
                if hand_info.get('is_nut_flush_draw') or hand_info.get('has_oesd'):
                    if random.random() < 0.35:
                        return ('bet', round(pot * 0.50, 2), f"{desc} - tag semi-bluffs")
                return ('check', 0, f"{desc} - tag checks draw")
            return ('check', 0, f"{desc} - tag checks")
        else:
            # Facing bet - TAGs fold marginal hands
            if strength >= 4:
                if random.random() < 0.15:
                    return ('raise', round(to_call * 1.0, 2), f"{desc} - tag raises")
                return ('call', 0, f"{desc} - tag calls strong")
            if strength >= 3:
                if hand_info.get('two_pair_type') == 'pocket_under_board':
                    if pot_pct > 0.35:
                        return ('fold', 0, f"{desc} - tag folds weak two pair")
                    return ('call', 0, f"{desc} - tag calls weak two pair")
                return ('call', 0, f"{desc} - tag calls two pair")
            if hand_info.get('has_top_pair'):
                if hand_info.get('has_good_kicker'):
                    if pot_pct > 0.50:
                        return ('fold', 0, f"{desc} - tag folds TPGK to big bet")
                    return ('call', 0, f"{desc} - tag calls TPGK")
                # TPWK - fold to aggression
                if pot_pct > 0.30:
                    return ('fold', 0, f"{desc} - tag folds TPWK")
                return ('call', 0, f"{desc} - tag calls top pair")
            if hand_info.get('is_overpair'):
                if pot_pct > 0.45:
                    return ('fold', 0, f"{desc} - tag folds overpair to big bet")
                return ('call', 0, f"{desc} - tag calls overpair")
            if strength >= 2:  # Weaker pairs - fold most
                if pot_pct > 0.30:
                    return ('fold', 0, f"{desc} - tag folds weak pair")
                if random.random() < 0.35:
                    return ('call', 0, f"{desc} - tag calls pair")
                return ('fold', 0, f"{desc} - tag folds pair")
            if has_any_draw:
                # Only call with good draws and odds
                if hand_info.get('is_nut_flush_draw') and pot_pct < 0.40:
                    return ('call', 0, f"{desc} - tag calls nut FD")
                if hand_info.get('has_oesd') and pot_pct < 0.30:
                    return ('call', 0, f"{desc} - tag calls OESD")
                if pot_pct < 0.20:
                    return ('call', 0, f"{desc} - tag calls draw")
                return ('fold', 0, f"{desc} - tag folds draw")
            return ('fold', 0, f"{desc} - tag folds")
    
    # LAG: Target Check 36.6%, Bet 28.0%, Call 16.7%, Fold 14.6%, AF 1.93
    # LAGs are aggressive but still hand-dependent
    if archetype == 'lag':
        pot_pct = to_call / (pot + to_call) if to_call and pot else 0
        if to_call == 0 or to_call is None:
            # First to act - bet wider range than TAG
            if strength >= 4:  # Sets+
                return ('bet', round(pot * 0.54, 2), f"{desc} - lag value bets")
            if strength >= 3:  # Two pair
                if hand_info.get('two_pair_type') == 'pocket_under_board':
                    if random.random() < 0.40:
                        return ('bet', round(pot * 0.40, 2), f"{desc} - lag bets weak two pair")
                    return ('check', 0, f"{desc} - lag checks weak two pair")
                return ('bet', round(pot * 0.50, 2), f"{desc} - lag bets two pair")
            if hand_info.get('has_top_pair'):
                # LAGs bet top pair more often
                if hand_info.get('has_good_kicker'):
                    return ('bet', round(pot * 0.50, 2), f"{desc} - lag bets TPGK")
                if random.random() < 0.50:
                    return ('bet', round(pot * 0.45, 2), f"{desc} - lag bets top pair")
                return ('check', 0, f"{desc} - lag checks TPWK")
            if hand_info.get('is_overpair'):
                return ('bet', round(pot * 0.55, 2), f"{desc} - lag bets overpair")
            if strength >= 2:  # Weaker pairs - bet sometimes
                if hand_info.get('has_middle_pair') and random.random() < 0.30:
                    return ('bet', round(pot * 0.40, 2), f"{desc} - lag bets middle pair")
                return ('check', 0, f"{desc} - lag checks pair")
            # Draws - semi-bluff more than TAG
            if has_any_draw:
                if hand_info.get('is_nut_flush_draw') or hand_info.get('has_oesd'):
                    if random.random() < 0.50:
                        return ('bet', round(pot * 0.45, 2), f"{desc} - lag semi-bluffs")
                if random.random() < 0.20:
                    return ('bet', round(pot * 0.35, 2), f"{desc} - lag semi-bluffs draw")
                return ('check', 0, f"{desc} - lag checks draw")
            # Air - occasional bluff
            if street == 'flop' and random.random() < 0.12:
                return ('bet', round(pot * 0.35, 2), "lag c-bets air")
            return ('check', 0, f"{desc} - lag checks")
        else:
            # Facing bet - LAGs call wider, fold less
            if strength >= 4:
                if random.random() < 0.20:
                    return ('raise', round(to_call * 1.0, 2), f"{desc} - lag raises")
                return ('call', 0, f"{desc} - lag calls strong")
            if strength >= 3:
                if hand_info.get('two_pair_type') == 'pocket_under_board':
                    if pot_pct > 0.50:
                        return ('fold', 0, f"{desc} - lag folds weak two pair")
                    return ('call', 0, f"{desc} - lag calls weak two pair")
                return ('call', 0, f"{desc} - lag calls two pair")
            if hand_info.get('has_top_pair'):
                if hand_info.get('has_good_kicker'):
                    if pot_pct > 0.55:
                        return ('fold', 0, f"{desc} - lag folds TPGK to big bet")
                    return ('call', 0, f"{desc} - lag calls TPGK")
                # TPWK - call more than TAG
                if pot_pct > 0.40:
                    return ('fold', 0, f"{desc} - lag folds TPWK")
                return ('call', 0, f"{desc} - lag calls top pair")
            if hand_info.get('is_overpair'):
                if pot_pct > 0.50:
                    return ('fold', 0, f"{desc} - lag folds overpair to big bet")
                return ('call', 0, f"{desc} - lag calls overpair")
            if strength >= 2:  # Weaker pairs - call more than TAG
                if pot_pct > 0.40:
                    return ('fold', 0, f"{desc} - lag folds weak pair")
                if random.random() < 0.60:
                    return ('call', 0, f"{desc} - lag calls pair")
                return ('fold', 0, f"{desc} - lag folds pair")
            if has_any_draw:
                # Call draws more liberally
                if hand_info.get('is_nut_flush_draw') and pot_pct < 0.50:
                    return ('call', 0, f"{desc} - lag calls nut FD")
                if hand_info.get('has_oesd') and pot_pct < 0.40:
                    return ('call', 0, f"{desc} - lag calls OESD")
                if pot_pct < 0.30:
                    return ('call', 0, f"{desc} - lag calls draw")
                return ('fold', 0, f"{desc} - lag folds draw")
            return ('fold', 0, f"{desc} - lag folds")
    
    # MANIAC: AF 7.00 - Most aggressive, but still folds weak hands to overbets
    if archetype == 'maniac':
        pot_pct = to_call / (pot + to_call) if to_call and pot else 0
        if to_call == 0 or to_call is None:
            if strength >= 4:
                return ('bet', round(pot * 0.75, 2), f"{desc} - maniac bets big")
            if strength >= 3:
                if hand_info.get('two_pair_type') == 'pocket_under_board':
                    if random.random() < 0.50:
                        return ('bet', round(pot * 0.40, 2), f"{desc} - maniac bets weak")
                    return ('check', 0, f"{desc} - maniac checks weak two pair")
                return ('bet', round(pot * 0.65, 2), f"{desc} - maniac bets")
            if hand_info['has_any_pair'] and random.random() < 0.75:
                return ('bet', round(pot * 0.55, 2), f"{desc} - maniac bets pair")
            if has_any_draw and street != 'river' and random.random() < 0.70:
                return ('bet', round(pot * 0.55, 2), "maniac semi-bluffs")
            if street == 'flop' and random.random() < 0.50:
                return ('bet', round(pot * 0.50, 2), "maniac c-bets air")
            if street == 'turn' and random.random() < 0.30:
                return ('bet', round(pot * 0.45, 2), "maniac barrels turn")
            if street == 'river' and random.random() < 0.20:
                return ('bet', round(pot * 0.5, 2), "maniac river bluff")
            return ('check', 0, f"{desc} - maniac checks")
        else:
            if hand_info.get('two_pair_type') == 'pocket_under_board':
                if street == 'flop' and random.random() < 0.60:
                    return ('call', 0, f"{desc} - maniac calls flop")
                if random.random() < 0.30:
                    return ('call', 0, f"{desc} - maniac calls weak")
                return ('fold', 0, f"{desc} - maniac folds weak two pair")
            if strength >= 4:
                if random.random() < 0.70:
                    return ('raise', round(to_call * 1.5, 2), f"{desc} - maniac raises big")
                return ('call', 0, f"{desc} - maniac calls strong")
            if strength >= 3:
                if random.random() < 0.50:
                    return ('raise', round(to_call * 1.0, 2), f"{desc} - maniac raises two pair")
                return ('call', 0, f"{desc} - maniac calls two pair")
            # Top pair: call any size, sometimes raise
            if hand_info.get('has_top_pair'):
                if random.random() < 0.40:
                    return ('raise', round(to_call * 1.0, 2), f"{desc} - maniac raises")
                return ('call', 0, f"{desc} - maniac calls top pair")
            # Weaker pairs: fold to 80%+ pot overbets
            if strength >= 2:
                if pot_pct > 0.55:
                    return ('fold', 0, f"{desc} - maniac folds to overbet")
                if random.random() < 0.40:
                    return ('raise', round(to_call * 1.0, 2), f"{desc} - maniac raises pair")
                return ('call', 0, f"{desc} - maniac calls pair")
            if has_any_draw and street != 'river':
                if random.random() < 0.40:
                    return ('raise', round(to_call * 1.0, 2), "maniac raises draw")
                return ('call', 0, "maniac calls draw")
            if random.random() < 0.15:
                return ('call', 0, "maniac floats")
            return ('fold', 0, f"{desc} - maniac folds")
    
    # BOT STRATEGIES - strategy-specific postflop logic
    # gpt3/gpt4: Board texture aware, smaller c-bets, 3-bet pot adjustments
    # sonnet/kiro_optimal: Bigger value bets, overpair logic
    # value_max: Maniac-style big bets but smarter (doesn't bluff as much)
    # value_maniac: Exact maniac postflop (overbets, calls wide)
    # BUT with paired board protection (learned from KK on JJ disaster)
    
    # value_lord and value_maniac - unchanged
    if strategy == 'value_maniac':
        return _postflop_value_maniac(hole_cards, board, pot, to_call, street,
                                      strength, desc, has_any_draw, has_flush_draw, has_oesd, bb_size)
    
    if strategy == 'value_lord':
        return _postflop_value_lord(hole_cards, board, pot, to_call, street,
                                    strength, desc, has_any_draw, has_flush_draw, has_oesd, bb_size, is_aggressor, is_facing_raise)
    
    if strategy == 'optimal_stats':
        return _postflop_optimal_stats(hole_cards, board, pot, to_call, street, is_ip,
                                       is_aggressor, strength, desc, draws, combo_draw,
                                       has_flush_draw, has_oesd, has_gutshot, has_any_draw)
    
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
    
    # kiro_lord - kiro preflop + improved postflop
    if strategy == 'kiro_lord':
        return _postflop_kiro_lord(hole_cards, board, pot, to_call, street, is_ip,
                                   is_aggressor, strength, desc, draws, combo_draw,
                                   has_flush_draw, has_oesd, is_overpair, board_has_ace,
                                   is_underpair_to_ace, is_multiway)
    
    # Kiro strategies - use pot_pct for bet sizing decisions
    if strategy in ['kiro_optimal', 'kiro5', 'kiro_v2']:
        return _postflop_kiro(hole_cards, board, pot, to_call, street, is_ip,
                             is_aggressor, strength, desc, draws, combo_draw,
                             has_flush_draw, has_oesd, is_overpair, board_has_ace,
                             is_underpair_to_ace, is_multiway)
    
    # Sonnet-style strategies - use pot_pct for bet sizing decisions
    if strategy in ['sonnet', '2nl_exploit', 'aggressive']:
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
            # Top pair / overpair: overbet for value
            if hand_info['has_top_pair'] or hand_info['is_overpair']:
                if street in ['flop', 'turn'] and random.random() < 0.85:
                    return ('bet', round(pot * 1.0, 2), f"{desc} - overbet")
                if street == 'river' and random.random() < 0.5:
                    return ('bet', round(pot * 1.2, 2), f"{desc} - river overbet")
            # Middle pair: bet flop only, then pot control
            elif hand_info['has_middle_pair']:
                if street == 'flop':
                    return ('bet', round(pot * 0.5, 2), f"{desc} - bet middle pair")
                return ('check', 0, f"{desc} - check middle pair")
            # Bottom pair: small bet flop only
            elif hand_info['has_bottom_pair']:
                if street == 'flop' and random.random() < 0.6:
                    return ('bet', round(pot * 0.33, 2), f"{desc} - bet bottom pair")
                return ('check', 0, f"{desc} - check bottom pair")
        if has_any_draw and street != 'river':
            return ('bet', round(pot * 1.0, 2), "overbet draw")
        # C-bet with air - but NOT on dangerous boards
        is_monotone = hand_info.get('board_flush_suit') is not None
        is_paired = hand_info.get('board_pair_val') is not None
        if is_monotone and not has_flush_draw:
            return ('check', 0, f"{desc} - check (monotone board)")
        if is_paired:
            return ('check', 0, f"{desc} - check (paired board)")
        if street == 'flop' and random.random() < 0.80:
            return ('bet', round(pot * 0.9, 2), "c-bet big")
        if street == 'turn' and random.random() < 0.60:
            return ('bet', round(pot * 1.0, 2), "barrel turn")
        if street == 'river' and random.random() < 0.35:
            return ('bet', round(pot * 1.1, 2), "river bluff")
        return ('check', 0, f"{desc} - check")
    else:
        # Facing bet - raise monsters, call pairs, fold air
        pot_pct = to_call / pot if pot > 0 else 0
        if strength >= 6:
            return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
        if strength >= 4:
            return ('raise', round(to_call * 1.0, 2), f"{desc} - raise strong")
        if strength == 3:
            # Pocket pair on paired board - differentiate over vs under
            if hand_info['two_pair_type'] == 'pocket_under_board':
                # 66 on TT = weak, but call small bets (villain may bluff)
                if pot_pct <= 0.5:
                    return ('call', 0, f"{desc} - call (pocket under board vs {pot_pct:.0%} pot)")
                return ('fold', 0, f"{desc} - fold (pocket under board vs big bet)")
            if hand_info['two_pair_type'] == 'pocket_over_board':
                # QQ on TT = only Tx beats us, call reasonable bets
                if street == 'river' and pot_pct > 1.0:
                    return ('fold', 0, f"{desc} - fold pocket over vs overbet")
                return ('call', 0, f"{desc} - call (pocket over board)")
            if hand_info['two_pair_type'] == 'both_cards_hit':
                return ('raise', round(to_call * 1.0, 2), f"{desc} - raise strong")
            if hand_info['two_pair_type'] == 'one_card_board_pair' and is_dangerous_board_pair:
                if is_big_bet or street == 'river':
                    return ('fold', 0, f"{desc} - fold (two pair on dangerous board)")
                return ('call', 0, f"{desc} - call (but fold to more aggression)")
            return ('raise', round(to_call * 1.0, 2), f"{desc} - raise strong")
        # River defense based on hand strength and pot-relative bet size
        # 2NL villains under-bluff, so need strong hands to call big bets
        pot_pct = to_call / pot if pot > 0 else 0
        if street == 'river':
            # UNDERPAIR CHECK: Fold underpairs on river vs any bet
            if hand_info['is_pocket_pair'] and not hand_info['is_overpair']:
                return ('fold', 0, f"{desc} - fold underpair vs river bet")
            
            # Overpairs can call up to pot-sized bets
            if hand_info['is_overpair']:
                if pot_pct > 1.0:  # Only fold overpair to overbet
                    return ('fold', 0, f"{desc} - fold overpair vs {pot_pct:.0%} pot bet")
                return ('call', 0, f"{desc} - call river")
            if is_big_bet and strength < 3:  # 60%+ pot bet needs two pair+
                return ('fold', 0, f"{desc} - fold vs {pot_pct:.0%} pot bet (need two pair+)")
            # Bottom pair: fold river (too weak)
            if hand_info['has_bottom_pair']:
                return ('fold', 0, f"{desc} - fold bottom pair on river")
            # Middle pair: fold to 40%+ pot bets
            if hand_info['has_middle_pair'] and pot_pct > 0.4:
                return ('fold', 0, f"{desc} - fold middle pair vs {pot_pct:.0%} pot")
            if strength >= 2:  # Top pair+ can call small river bets
                return ('call', 0, f"{desc} - call river")
            return ('fold', 0, f"{desc} - fold river")
        # Flop/turn: fold weak pairs to huge overbets
        if hand_info['is_pocket_pair'] or hand_info['has_any_pair']:
            pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1
            pot_pct = to_call / pot if pot > 0 else 0
            
            # UNDERPAIR DEFENSE: Fold underpairs to aggression on scary boards
            if hand_info['is_pocket_pair'] and not hand_info['is_overpair']:
                pocket_val = hand_info.get('pocket_val', 0)
                is_strong_underpair = pocket_val >= 8  # TT+ (T=8, J=9, Q=10, K=11)
                
                # Flop: Check-call once (see if villain slows down)
                if street == 'flop' and pot_pct <= 0.5:
                    return ('call', 0, f"{desc} - call once (underpair)")
                # Flop overbet: Fold immediately
                if street == 'flop' and pot_pct > 0.5:
                    return ('fold', 0, f"{desc} - fold underpair vs overbet")
                # Turn: Strong underpairs (JJ+) call small bets
                if street == 'turn':
                    if is_strong_underpair and pot_pct <= 0.5:
                        return ('call', 0, f"{desc} - call strong underpair")
                    return ('fold', 0, f"{desc} - fold underpair vs aggression")
                # River: Fold all underpairs
                if street == 'river':
                    return ('fold', 0, f"{desc} - fold underpair river")
            
            # Fold weak pairs (bottom/middle) to overbets (100%+ pot)
            if pot_pct > 1.0 and strength <= 2 and not hand_info['has_top_pair'] and not hand_info['is_overpair']:
                return ('fold', 0, f"{desc} - fold weak pair vs overbet")
            # Fold weak pairs to all-in (but NOT overpairs)
            if pot_odds > 0.5 and not has_strong_draw and not hand_info['is_overpair']:
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
                         has_flush_draw=False, has_oesd=False, bb_size=0.05, is_aggressor=False, is_facing_raise=False):
    """
    VALUE_LORD postflop - value_maniac with Session 41 improvements.
    Fixes: c-bet discipline, overpair aggression, bottom pair caution.
    Session 48: Paired board discipline - don't bet into paired/double-paired boards without strong hand.
    """
    hand_info = analyze_hand(hole_cards, board)
    bet_in_bb = to_call / bb_size if bb_size > 0 else 0
    is_big_bet = to_call > 0 and pot > 0 and to_call >= pot * 0.5
    is_dangerous_board_pair = hand_info['board_pair_val'] is not None and hand_info['board_pair_val'] >= 8  # T+
    has_strong_draw = has_flush_draw or has_oesd
    is_paired_board = hand_info['has_board_pair']
    is_double_paired = hand_info.get('is_double_paired_board', False)
    
    # SESSION 48: Paired board discipline
    # On double-paired boards (3399, 7722), hero's "two pair" is just the board - worthless
    # Any villain with a 3, 9, 7, or 2 has full house
    # Only bet if we have full house or better (strength >= 5)
    if is_double_paired and strength < 5:
        # Hero has no real hand on double-paired board
        if to_call == 0:
            return ('check', 0, f"{desc} - check (double-paired board, need full house+)")
        else:
            # Facing bet on double-paired board without full house = fold
            return ('fold', 0, f"{desc} - fold (double-paired board, villain likely has full house)")
    
    # SESSION 48: Single paired board discipline (77x, 33x)
    # On turn/river, if villain called flop on paired board, they likely have trips
    # Only continue betting with set+ (strength >= 4)
    if is_paired_board and not is_double_paired and street in ['turn', 'river']:
        # If we don't have set or better, check (don't bet into likely trips)
        if strength < 4 and to_call == 0:
            # Exception: overpair can still bet for thin value on turn
            if hand_info['is_overpair'] and street == 'turn':
                pass  # Let normal overpair logic handle it
            else:
                return ('check', 0, f"{desc} - check (paired board turn/river, villain may have trips)")
    
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
            # pocket_under_board (88 on TT): Any Tx has trips, any 99+ beats us - pot control
            if hand_info['two_pair_type'] == 'pocket_under_board':
                if street == 'flop':
                    return ('bet', round(pot * 0.33, 2), f"{desc} - small bet (pot control)")
                return ('check', 0, f"{desc} - check (pocket under board)")
            # pocket_over_board (88 on 77): Any 7x has trips - pot control
            if hand_info['two_pair_type'] == 'pocket_over_board':
                if street == 'flop':
                    return ('bet', round(pot * 0.5, 2), f"{desc} - bet (pot control)")
                return ('check', 0, f"{desc} - check (pocket over board)")
            # one_card_board_pair on dangerous board (K2 on K99): CHECK
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
        # Pairs - differentiate by strength
        if hand_info['has_any_pair']:
            # Top pair: overbet for value
            if hand_info['has_top_pair']:
                if street in ['flop', 'turn']:
                    return ('bet', round(pot * 1.0, 2), f"{desc} - overbet")
                if street == 'river':
                    if hand_info['has_good_kicker']:
                        return ('bet', round(pot * 1.0, 2), f"{desc} - TPGK value")
                    else:
                        return ('bet', round(pot * 0.5, 2), f"{desc} - TPWK thin value")
            # Middle pair: bet flop only, then pot control
            elif hand_info['has_middle_pair']:
                if street == 'flop':
                    return ('bet', round(pot * 0.5, 2), f"{desc} - bet middle pair")
                return ('check', 0, f"{desc} - check middle pair")
            # Bottom pair: small bet flop only (always bet - sizing is defensive)
            elif hand_info['has_bottom_pair']:
                if street == 'flop':
                    return ('bet', round(pot * 0.33, 2), f"{desc} - bet bottom pair")
                return ('check', 0, f"{desc} - check bottom pair")
        if has_any_draw and street != 'river':
            return ('bet', round(pot * 1.0, 2), "overbet draw")
        # Only c-bet when aggressor - but NOT on dangerous boards
        if is_aggressor and street == 'flop':
            is_monotone = hand_info.get('board_flush_suit') is not None
            is_paired = hand_info.get('board_pair_val') is not None
            if is_monotone and not has_flush_draw:
                return ('check', 0, f"{desc} - check (monotone board)")
            if is_paired:
                return ('check', 0, f"{desc} - check (paired board)")
            return ('bet', round(pot * 0.9, 2), "c-bet big")
        return ('check', 0, f"{desc} - check")
    else:
        # Facing bet - same as value_maniac
        pot_pct = to_call / pot if pot > 0 else 0
        if strength >= 6:
            return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
        if strength >= 4:
            return ('raise', round(to_call * 1.0, 2), f"{desc} - raise strong")
        if strength == 3:
            # Pocket pair on paired board - differentiate over vs under
            if hand_info['two_pair_type'] == 'pocket_under_board':
                # 66 on TT = weak, but call small bets (villain may bluff)
                if pot_pct <= 0.5:
                    return ('call', 0, f"{desc} - call (pocket under board vs {pot_pct:.0%} pot)")
                return ('fold', 0, f"{desc} - fold (pocket under board vs big bet)")
            if hand_info['two_pair_type'] == 'pocket_over_board':
                # QQ on TT = only Tx beats us, but check-raise = trips
                if is_facing_raise:
                    return ('fold', 0, f"{desc} - fold pocket over vs check-raise (likely trips)")
                if street == 'river' and pot_pct > 1.0:
                    return ('fold', 0, f"{desc} - fold pocket over vs river overbet")
                return ('call', 0, f"{desc} - call (pocket over board)")
            if hand_info['two_pair_type'] == 'both_cards_hit':
                # Two pair is strong but fold to extreme aggression (likely set/boat)
                # Check-raise or 4-bet = monster at 2NL
                if is_facing_raise:
                    return ('fold', 0, f"{desc} - fold two pair vs check-raise (likely set+)")
                if pot_pct > 1.0:
                    return ('fold', 0, f"{desc} - fold two pair vs overbet (likely set+)")
                return ('raise', round(to_call * 1.0, 2), f"{desc} - raise strong")
            if hand_info['two_pair_type'] == 'one_card_board_pair':
                # Check-raise = trips/set at 2NL
                if is_facing_raise:
                    return ('fold', 0, f"{desc} - fold one_card two pair vs check-raise (likely trips)")
                if is_dangerous_board_pair:
                    if is_big_bet or street == 'river':
                        return ('fold', 0, f"{desc} - fold (two pair on dangerous board)")
                    return ('call', 0, f"{desc} - call (but fold to more aggression)")
            return ('raise', round(to_call * 1.0, 2), f"{desc} - raise strong")
        pot_pct = to_call / pot if pot > 0 else 0
        if street == 'river':
            # UNDERPAIR CHECK: Fold underpairs on river vs any bet
            if hand_info['is_pocket_pair'] and not hand_info['is_overpair']:
                return ('fold', 0, f"{desc} - fold underpair vs river bet")
            
            if hand_info['is_overpair']:
                # Check-raise on river = trips/boat at 2NL
                if is_facing_raise:
                    return ('fold', 0, f"{desc} - fold overpair vs check-raise (likely trips+)")
                if pot_pct > 1.0:
                    return ('fold', 0, f"{desc} - fold overpair vs {pot_pct:.0%} pot bet")
                return ('call', 0, f"{desc} - call river")
            
            # TOP PAIR: Differentiate by kicker on river
            if hand_info['has_top_pair']:
                if hand_info['has_good_kicker']:
                    if pot_pct <= 0.5:
                        return ('call', 0, f"{desc} - call TPGK river")
                    return ('fold', 0, f"{desc} - fold TPGK vs big river bet")
                else:
                    return ('fold', 0, f"{desc} - fold TPWK river")
            
            if is_big_bet and strength < 3:
                return ('fold', 0, f"{desc} - fold vs {pot_pct:.0%} pot bet (need two pair+)")
            # Bottom pair: fold river (too weak)
            if hand_info['has_bottom_pair']:
                return ('fold', 0, f"{desc} - fold bottom pair on river")
            # Middle pair: fold to 40%+ pot bets
            if hand_info['has_middle_pair'] and pot_pct > 0.4:
                return ('fold', 0, f"{desc} - fold middle pair vs {pot_pct:.0%} pot")
            if strength >= 2:
                return ('call', 0, f"{desc} - call river")
            return ('fold', 0, f"{desc} - fold river")
        if hand_info['is_pocket_pair'] or hand_info['has_any_pair']:
            pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1
            pot_pct = to_call / pot if pot > 0 else 0
            
            # UNDERPAIR DEFENSE: Fold underpairs to aggression on scary boards
            if hand_info['is_pocket_pair'] and not hand_info['is_overpair']:
                pocket_val = hand_info.get('pocket_val', 0)
                is_strong_underpair = pocket_val >= 8  # TT+ (T=8, J=9, Q=10, K=11)
                
                # Flop: Check-call once (see if villain slows down)
                if street == 'flop' and pot_pct <= 0.5:
                    return ('call', 0, f"{desc} - call once (underpair)")
                # Flop overbet: Fold immediately
                if street == 'flop' and pot_pct > 0.5:
                    return ('fold', 0, f"{desc} - fold underpair vs overbet")
                # Turn: Strong underpairs (JJ+) call small bets
                if street == 'turn':
                    if is_strong_underpair and pot_pct <= 0.5:
                        return ('call', 0, f"{desc} - call strong underpair")
                    return ('fold', 0, f"{desc} - fold underpair vs aggression")
                # River: Fold all underpairs
                if street == 'river':
                    return ('fold', 0, f"{desc} - fold underpair river")
            
            # TOP PAIR: Differentiate by kicker strength
            if hand_info['has_top_pair']:
                if hand_info['has_good_kicker']:
                    # TPGK: Call normal bets, fold to huge overbets (shove = overpair/set)
                    # But always call if we have a flush draw (extra equity)
                    if hand_info.get('has_flush_draw'):
                        return ('call', 0, f"{desc} - call TPGK + flush draw")
                    # Calculate effective bet size: to_call / (pot - to_call) for raise sizing
                    effective_pct = to_call / (pot - to_call) if pot > to_call else pot_pct
                    if street == 'flop':
                        if effective_pct > 1.0:  # Fold to pot+ raise on flop (shove)
                            return ('fold', 0, f"{desc} - fold TPGK vs {effective_pct:.0%} pot shove")
                        return ('call', 0, f"{desc} - call TPGK")
                    if street == 'turn':
                        if effective_pct > 0.8:  # Fold to 80%+ raise on turn
                            return ('fold', 0, f"{desc} - fold TPGK vs {effective_pct:.0%} pot")
                        return ('call', 0, f"{desc} - call TPGK")
                    # River: only call small bets
                    if pot_pct <= 0.5:
                        return ('call', 0, f"{desc} - call TPGK river")
                    return ('fold', 0, f"{desc} - fold TPGK vs big river bet")
                else:
                    # TPWK: Call flop vs normal bets, fold turn/river
                    if street == 'flop' and pot_pct <= 0.5:
                        return ('call', 0, f"{desc} - call TPWK flop")
                    return ('fold', 0, f"{desc} - fold TPWK")
            
            # MIDDLE vs BOTTOM PAIR: Different thresholds
            if hand_info['has_middle_pair']:
                if street == 'flop' and pot_pct <= 0.35:
                    return ('call', 0, f"{desc} - call middle pair")
                return ('fold', 0, f"{desc} - fold middle pair")
            
            if hand_info['has_bottom_pair']:
                if street == 'flop' and pot_pct <= 0.25:
                    return ('call', 0, f"{desc} - call bottom pair")
                return ('fold', 0, f"{desc} - fold bottom pair")
            
            # Generic pair logic (overpairs, pocket pairs)
            if pot_pct > 1.0 and strength <= 2 and not hand_info['is_overpair']:
                return ('fold', 0, f"{desc} - fold weak pair vs overbet")
            if pot_odds > 0.5 and not has_strong_draw and not hand_info['is_overpair']:
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


def _postflop_optimal_stats(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                            strength, desc, draws, combo_draw, has_flush_draw, has_oesd, has_gutshot, has_any_draw):
    """
    OPTIMAL_STATS postflop - Balanced aggression targeting AF 2.5, C-bet 70%.
    Key: More checking and calling than other strategies to achieve balanced AF.
    """
    hand_info = analyze_hand(hole_cards, board)
    pot_pct = to_call / pot if pot > 0 and to_call else 0
    
    # Board texture analysis
    board_vals = [RANK_VAL[c[0]] for c in board] if board else []
    board_suits = [c[1] for c in board] if board else []
    is_wet_board = len(set(board_suits)) <= 2 or (max(board_vals) - min(board_vals) <= 4 if board_vals else False)
    is_dry_board = not is_wet_board
    
    # === CHECKED TO US (betting decisions) ===
    if to_call == 0 or to_call is None:
        
        # Monsters: bet for value (but not always - balance)
        if strength >= 5:  # Flush, straight, full house+
            if random.random() < 0.85:  # Bet 85%, check 15%
                bet = round(pot * 0.70, 2)
                return ('bet', bet, f"{desc} - bet 70% for value")
            return ('check', 0, f"{desc} - slowplay monster")
        
        # Sets: bet for value
        if strength == 4 or hand_info.get('has_set'):
            if random.random() < 0.80:  # Bet 80%, check 20%
                bet = round(pot * 0.65, 2)
                return ('bet', bet, f"{desc} - bet 65% with set")
            return ('check', 0, f"{desc} - slowplay set")
        
        # Two pair: bet for value
        if strength == 3 or hand_info.get('has_two_pair'):
            bet = round(pot * 0.60, 2)
            return ('bet', bet, f"{desc} - bet 60% with two pair")
        
        # Overpair: bet flop/turn, check river sometimes
        if hand_info.get('is_overpair'):
            if street == 'river' and random.random() < 0.40:
                return ('check', 0, f"{desc} - check overpair river")
            bet = round(pot * 0.55, 2)
            return ('bet', bet, f"{desc} - bet 55% with overpair")
        
        # Top pair good kicker: bet flop, check turn/river more
        if hand_info.get('has_top_pair') and hand_info.get('has_good_kicker'):
            if street == 'flop':
                bet = round(pot * 0.50, 2)
                return ('bet', bet, f"{desc} - bet 50% TPGK")
            if street == 'turn' and random.random() < 0.50:
                bet = round(pot * 0.50, 2)
                return ('bet', bet, f"{desc} - bet 50% TPGK turn")
            return ('check', 0, f"{desc} - check TPGK")
        
        # Top pair weak kicker: bet flop only, sometimes
        if hand_info.get('has_top_pair'):
            if street == 'flop' and random.random() < 0.60:
                bet = round(pot * 0.45, 2)
                return ('bet', bet, f"{desc} - bet 45% TPWK")
            return ('check', 0, f"{desc} - check TPWK")
        
        # Middle/bottom pair: check
        if hand_info.get('has_middle_pair') or hand_info.get('has_bottom_pair') or hand_info.get('has_any_pair'):
            return ('check', 0, f"{desc} - check weak pair")
        
        # Draws: semi-bluff sometimes (not always)
        if combo_draw and random.random() < 0.70:
            bet = round(pot * 0.55, 2)
            return ('bet', bet, "semi-bluff combo draw")
        if has_flush_draw and random.random() < 0.55:
            bet = round(pot * 0.45, 2)
            return ('bet', bet, "semi-bluff flush draw")
        if has_oesd and random.random() < 0.50:
            bet = round(pot * 0.45, 2)
            return ('bet', bet, "semi-bluff OESD")
        
        # C-bet with air (only if aggressor, ~65% frequency)
        if is_aggressor:
            if street == 'flop':
                if is_dry_board and random.random() < 0.65:
                    bet = round(pot * 0.40, 2)
                    return ('bet', bet, "c-bet dry board")
                if is_wet_board and random.random() < 0.45:
                    bet = round(pot * 0.50, 2)
                    return ('bet', bet, "c-bet wet board")
            if street == 'turn' and random.random() < 0.30:
                bet = round(pot * 0.50, 2)
                return ('bet', bet, "barrel turn")
        
        return ('check', 0, f"{desc} - check")
    
    # === FACING BET (calling/folding decisions) ===
    else:
        # Monsters: mostly call to keep AF balanced
        if strength >= 5:
            if random.random() < 0.35:  # Raise 35%, call 65%
                raise_amt = round(to_call * 1.0, 2)
                return ('raise', raise_amt, f"{desc} - raise monster")
            return ('call', 0, f"{desc} - call monster")
        
        # Sets: mostly call
        if strength == 4 or hand_info.get('has_set'):
            if random.random() < 0.25:  # Raise 25%, call 75%
                raise_amt = round(to_call * 1.0, 2)
                return ('raise', raise_amt, f"{desc} - raise set")
            return ('call', 0, f"{desc} - call set")
        
        # Two pair: call
        if strength == 3 or hand_info.get('has_two_pair'):
            return ('call', 0, f"{desc} - call two pair")
        
        # Overpair: call flop/turn, fold river to big bets
        if hand_info.get('is_overpair'):
            if street == 'river' and pot_pct > 0.75:
                return ('fold', 0, f"{desc} - fold overpair to big river bet")
            return ('call', 0, f"{desc} - call overpair")
        
        # Top pair good kicker: call one street
        if hand_info.get('has_top_pair') and hand_info.get('has_good_kicker'):
            if street == 'flop':
                return ('call', 0, f"{desc} - call TPGK flop")
            if street == 'turn' and pot_pct <= 0.50:
                return ('call', 0, f"{desc} - call TPGK turn small bet")
            return ('fold', 0, f"{desc} - fold TPGK to aggression")
        
        # Top pair weak kicker: call flop only
        if hand_info.get('has_top_pair'):
            if street == 'flop' and pot_pct <= 0.50:
                return ('call', 0, f"{desc} - call TPWK flop")
            return ('fold', 0, f"{desc} - fold TPWK")
        
        # Middle pair: call flop small bets only
        if hand_info.get('has_middle_pair'):
            if street == 'flop' and pot_pct <= 0.40:
                return ('call', 0, f"{desc} - call middle pair flop")
            return ('fold', 0, f"{desc} - fold middle pair")
        
        # Bottom pair: fold
        if hand_info.get('has_bottom_pair'):
            return ('fold', 0, f"{desc} - fold bottom pair")
        
        # Draws: call if pot odds justify
        if combo_draw and pot_pct <= 0.45:
            return ('call', 0, "call combo draw")
        if has_flush_draw and pot_pct <= 0.35:
            return ('call', 0, "call flush draw")
        if has_oesd and pot_pct <= 0.30:
            return ('call', 0, "call OESD")
        if has_gutshot and pot_pct <= 0.20:
            return ('call', 0, "call gutshot")
        
        # Air: fold (don't hero call)
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
        
        # Underpair (pocket pair below board high card) - very careful
        if hand_info.get('is_underpair'):
            # Only call flop with small bet, fold turn/river
            if street == 'flop' and pot_odds <= 0.30:
                return ('call', 0, f"{desc} - call flop (underpair)")
            return ('fold', 0, f"{desc} - fold underpair")
        
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
    
    # === FACING BET ===
    # Per gpt3/gpt4 files:
    # "Turn raises: fold most one-pair"
    # "River raises: fold almost all one-pair"
    # Use pot_pct for smarter bet-size decisions
    
    pot_pct = to_call / pot if pot > 0 else 0
    
    if strength >= 6:
        return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
    if strength >= 5:
        return ('raise', round(to_call * 1.0, 2), f"{desc} - raise strong")
    if strength == 4:
        return ('raise', round(to_call * 1.0, 2), f"{desc} - raise set/trips")
    if strength == 3:
        return ('call', 0, f"{desc} - call two pair")
    
    # Overpair - call small bets, fold big bets on turn/river
    if hand_info['is_overpair']:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        if pot_pct <= 0.4:
            return ('call', 0, f"{desc} - call small {street} bet")
        return ('fold', 0, f"{desc} - fold vs {pot_pct:.0%} pot")
    
    # Underpair to ace - call small flop bets only
    if hand_info['is_underpair_to_ace']:
        if street == 'flop' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call flop")
        return ('fold', 0, f"{desc} - fold (ace on board)")
    
    # TPGK - call flop/turn small bets, fold big bets and river
    if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        if street == 'turn' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call small turn bet")
        return ('fold', 0, f"{desc} - fold {street}")
    
    # TPWK - call small flop bets only
    if hand_info['has_top_pair']:
        if street == 'flop' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call flop")
        return ('fold', 0, f"{desc} - fold {street}")
    
    # Middle pair - call small flop bets only
    if hand_info['has_middle_pair']:
        if street == 'flop' and pot_pct <= 0.4:
            return ('call', 0, f"{desc} - call flop")
        return ('fold', 0, f"{desc} - fold")
    
    # Bottom pair - fold
    if hand_info['has_bottom_pair']:
        return ('fold', 0, f"{desc} - fold bottom pair")
    
    # Draws - conservative thresholds
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


def _postflop_kiro(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                   strength, desc, draws, combo_draw, has_flush_draw, has_oesd,
                   is_overpair, board_has_ace, is_underpair_to_ace=False, is_multiway=False):
    """
    Kiro strategies (kiro_optimal, kiro5, kiro_v2): Slightly smaller sizings.
    Per strategy files: TPGK 65%/55%/40%, Overpair 65%/55%/45%, etc.
    Uses pot_pct for bet-size aware decisions.
    """
    hand_info = analyze_hand(hole_cards, board)
    
    # Sizings per kiro_v2 file (slightly smaller than sonnet)
    s = {
        'flop': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.75, 'tptk': 0.70, 'tpgk': 0.65, 'tpwk': 0.60, 'overpair': 0.65},
        'turn': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.75, 'tptk': 0.60, 'tpgk': 0.55, 'tpwk': 0.0, 'overpair': 0.55},
        'river': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.75, 'tptk': 0.50, 'tpgk': 0.40, 'tpwk': 0.0, 'overpair': 0.45},
    }.get(street, {})
    
    if to_call == 0 or to_call is None:
        # Multiway: only bet strong value + strong draws
        if is_multiway:
            if strength >= 4:
                return ('bet', round(pot * s.get('set', 0.85), 2), f"{desc} - multiway value")
            if strength == 3:
                return ('bet', round(pot * 0.65, 2), f"{desc} - multiway value")
            if combo_draw:
                return ('bet', round(pot * 0.60, 2), "combo draw - multiway semi-bluff")
            return ('check', 0, f"{desc} - check multiway")
        
        # Strong hands
        if strength >= 5:
            return ('bet', round(pot * s.get('nuts', 1.0), 2), f"{desc} - bet 100%")
        if strength == 4:
            return ('bet', round(pot * s.get('set', 0.85), 2), f"{desc} - bet 85%")
        if strength == 3:
            return ('bet', round(pot * s.get('twopair', 0.75), 2), f"{desc} - bet 75%")
        
        # Underpair to ace - check-call only
        if hand_info['is_underpair_to_ace']:
            return ('check', 0, f"{desc} - check (pocket pair below ace)")
        
        # True overpair
        if hand_info['is_overpair']:
            return ('bet', round(pot * s.get('overpair', 0.65), 2), f"{desc} overpair - bet")
        
        # Top pair top kicker
        if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
            return ('bet', round(pot * s.get('tptk', 0.70), 2), f"{desc} - value bet")
        
        # Top pair good kicker (8+)
        if hand_info['has_top_pair'] and hand_info.get('kicker_val', 0) >= 6:
            return ('bet', round(pot * s.get('tpgk', 0.65), 2), f"{desc} - value bet")
        
        # Top pair weak kicker - bet flop only
        if hand_info['has_top_pair'] and street == 'flop':
            return ('bet', round(pot * s.get('tpwk', 0.60), 2), f"{desc} - bet flop")
        
        # Draws
        if combo_draw:
            return ('bet', round(pot * 0.65, 2), "combo draw - semi-bluff 65%")
        if hand_info.get('has_flush_draw') and is_aggressor:
            return ('bet', round(pot * 0.45, 2), "flush draw - semi-bluff")
        
        return ('check', 0, f"{desc} - check")
    
    # === FACING BET ===
    # Use pot_pct for smarter bet-size decisions
    # Per kiro files: "Turn raises: fold one pair", "River raises: fold two pair"
    
    pot_pct = to_call / pot if pot > 0 else 0
    
    if strength >= 6:
        return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
    if strength >= 5:
        return ('raise', round(to_call * 1.0, 2), f"{desc} - raise strong")
    if strength == 4:
        return ('raise', round(to_call * 1.0, 2), f"{desc} - raise set/trips")
    if strength == 3:
        # Two pair: call, but fold to big river bets
        if street == 'river' and pot_pct > 0.75:
            return ('fold', 0, f"{desc} - fold two pair vs {pot_pct:.0%} pot")
        return ('call', 0, f"{desc} - call two pair")
    
    # Underpair to ace - call small flop bets only
    if hand_info['is_underpair_to_ace']:
        if street == 'flop' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call flop (pocket pair below ace)")
        return ('fold', 0, f"{desc} - fold (ace on board)")
    
    # Overpair - call small/medium bets, fold big bets on turn/river
    if hand_info['is_overpair']:
        if street == 'flop':
            return ('call', 0, f"{desc} overpair - call")
        if pot_pct <= 0.5:
            return ('call', 0, f"{desc} overpair - call {street}")
        return ('fold', 0, f"{desc} overpair - fold vs {pot_pct:.0%} pot")
    
    # TPGK - call flop/turn, fold big river bets
    if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        if street == 'turn' and pot_pct <= 0.6:
            return ('call', 0, f"{desc} - call turn")
        if street == 'river' and pot_pct <= 0.4:
            return ('call', 0, f"{desc} - call small river")
        return ('fold', 0, f"{desc} - fold vs {pot_pct:.0%} pot")
    
    # TPWK - call small flop bets only
    if hand_info['has_top_pair']:
        if street == 'flop' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call flop")
        return ('fold', 0, f"{desc} - fold {street}")
    
    # Middle pair - call small flop bets only
    if hand_info['has_middle_pair']:
        if street == 'flop' and pot_pct <= 0.4:
            return ('call', 0, f"{desc} - call flop once")
        return ('fold', 0, f"{desc} - fold {street}")
    
    # Bottom pair - fold
    if hand_info['has_bottom_pair']:
        return ('fold', 0, f"{desc} - fold (bottom pair)")
    
    # Draws - conservative thresholds
    pot_odds = to_call / (pot + to_call) if pot > 0 else 1
    if hand_info.get('has_flush_draw'):
        if pot_odds <= 0.40:
            return ('call', 0, "flush draw - call")
    if hand_info.get('has_straight_draw'):
        # Per file: "call ≤33% pot"
        if pot_odds <= 0.33:
            return ('call', 0, "straight draw - call")
    
    return ('fold', 0, f"{desc} - fold")


def _postflop_kiro_lord(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                        strength, desc, draws, combo_draw, has_flush_draw, has_oesd,
                        is_overpair, board_has_ace, is_underpair_to_ace=False, is_multiway=False):
    """
    kiro_lord: kiro_optimal preflop + improved postflop.
    Fixes 5 mistakes from kiro_optimal:
    1. pocket_under_board: FOLD to any bet
    2. pocket_over_board river vs 100%+: FOLD
    3. Underpair vs 50% flop: CALL once
    4. TPGK vs 75%+ turn: FOLD
    5. Nut FD vs 100%: FOLD
    """
    hand_info = analyze_hand(hole_cards, board)
    
    # Sizings (same as kiro)
    s = {
        'flop': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.75, 'tptk': 0.70, 'tpgk': 0.65, 'tpwk': 0.60, 'overpair': 0.65},
        'turn': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.75, 'tptk': 0.60, 'tpgk': 0.55, 'tpwk': 0.0, 'overpair': 0.55},
        'river': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.75, 'tptk': 0.50, 'tpgk': 0.40, 'tpwk': 0.0, 'overpair': 0.45},
    }.get(street, {})
    
    if to_call == 0 or to_call is None:
        # === NOT FACING BET (same as kiro) ===
        if is_multiway:
            if strength >= 4:
                return ('bet', round(pot * s.get('set', 0.85), 2), f"{desc} - multiway value")
            if strength == 3:
                return ('bet', round(pot * 0.65, 2), f"{desc} - multiway value")
            if combo_draw:
                return ('bet', round(pot * 0.60, 2), "combo draw - multiway semi-bluff")
            return ('check', 0, f"{desc} - check multiway")
        
        if strength >= 5:
            return ('bet', round(pot * s.get('nuts', 1.0), 2), f"{desc} - bet 100%")
        if strength == 4:
            return ('bet', round(pot * s.get('set', 0.85), 2), f"{desc} - bet 85%")
        if strength == 3:
            return ('bet', round(pot * s.get('twopair', 0.75), 2), f"{desc} - bet 75%")
        
        if hand_info['is_underpair_to_ace']:
            return ('check', 0, f"{desc} - check (pocket pair below ace)")
        
        if hand_info['is_overpair']:
            return ('bet', round(pot * s.get('overpair', 0.65), 2), f"{desc} overpair - bet")
        
        if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
            return ('bet', round(pot * s.get('tptk', 0.70), 2), f"{desc} - value bet")
        
        if hand_info['has_top_pair'] and hand_info.get('kicker_val', 0) >= 6:
            return ('bet', round(pot * s.get('tpgk', 0.65), 2), f"{desc} - value bet")
        
        if hand_info['has_top_pair'] and street == 'flop':
            return ('bet', round(pot * s.get('tpwk', 0.60), 2), f"{desc} - bet flop")
        
        if combo_draw:
            return ('bet', round(pot * 0.65, 2), "combo draw - semi-bluff 65%")
        if hand_info.get('has_flush_draw') and is_aggressor:
            return ('bet', round(pot * 0.45, 2), "flush draw - semi-bluff")
        
        return ('check', 0, f"{desc} - check")
    
    # === FACING BET - IMPROVED LOGIC ===
    pot_pct = to_call / pot if pot > 0 else 0
    
    # Monsters - always continue
    if strength >= 6:
        return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
    if strength >= 5:
        return ('raise', round(to_call * 1.0, 2), f"{desc} - raise strong")
    if strength == 4:
        return ('raise', round(to_call * 1.0, 2), f"{desc} - raise set/trips")
    
    # Two pair - check for paired board types
    if strength == 3:
        # FIX #1: pocket_under_board - FOLD to ANY bet
        if hand_info.get('two_pair_type') == 'pocket_under_board':
            return ('fold', 0, f"{desc} - fold (pocket under board)")
        
        # FIX #2: pocket_over_board - fold river vs 100%+ (pot_pct > 0.50)
        if hand_info.get('two_pair_type') == 'pocket_over_board':
            if street == 'river' and pot_pct > 0.50:
                return ('fold', 0, f"{desc} - fold pocket over vs {pot_pct:.0%} river")
            return ('call', 0, f"{desc} - call (pocket over board)")
        
        # Other two pair - call, fold big river
        if street == 'river' and pot_pct > 0.75:
            return ('fold', 0, f"{desc} - fold two pair vs {pot_pct:.0%} pot")
        return ('call', 0, f"{desc} - call two pair")
    
    # Underpair to ace - call small flop only
    if hand_info['is_underpair_to_ace']:
        if street == 'flop' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call flop (pocket pair below ace)")
        return ('fold', 0, f"{desc} - fold (ace on board)")
    
    # Overpair - call most, fold big turn/river
    if hand_info['is_overpair']:
        if street == 'flop':
            return ('call', 0, f"{desc} overpair - call")
        if pot_pct <= 0.5:
            return ('call', 0, f"{desc} overpair - call {street}")
        return ('fold', 0, f"{desc} overpair - fold vs {pot_pct:.0%} pot")
    
    # FIX #3: Underpair (99 on K-high) - call flop once
    if hand_info.get('is_pocket_pair') and not hand_info.get('is_overpair'):
        if street == 'flop' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call underpair flop once")
        return ('fold', 0, f"{desc} - fold underpair")
    
    # FIX #4: TPGK - tighter thresholds (fold vs 100%+ turn, 75%+ river)
    if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        if street == 'turn':
            if pot_pct <= 0.43:  # Up to 75% pot bet
                return ('call', 0, f"{desc} - call turn")
            return ('fold', 0, f"{desc} - fold TPGK vs {pot_pct:.0%} turn")
        if street == 'river':
            if pot_pct <= 0.40:  # Up to ~66% pot bet
                return ('call', 0, f"{desc} - call small river")
            return ('fold', 0, f"{desc} - fold TPGK vs {pot_pct:.0%} river")
    
    # TPWK - call small flop only
    if hand_info['has_top_pair']:
        if street == 'flop' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call flop")
        return ('fold', 0, f"{desc} - fold {street}")
    
    # Middle pair - call small flop only
    if hand_info['has_middle_pair']:
        if street == 'flop' and pot_pct <= 0.4:
            return ('call', 0, f"{desc} - call flop once")
        return ('fold', 0, f"{desc} - fold {street}")
    
    # Bottom pair - fold
    if hand_info['has_bottom_pair']:
        return ('fold', 0, f"{desc} - fold (bottom pair)")
    
    # FIX #5: Draws - tighter thresholds
    pot_odds = to_call / (pot + to_call) if pot > 0 else 1
    if hand_info.get('has_flush_draw'):
        # Nut FD: call up to 35% pot odds (~66% pot bet)
        # Non-nut: call up to 25% pot odds (~33% pot bet)
        if hand_info.get('is_nut_flush_draw'):
            if pot_odds <= 0.35:
                return ('call', 0, "nut flush draw - call")
        else:
            if pot_odds <= 0.25:
                return ('call', 0, "flush draw - call")
        return ('fold', 0, f"flush draw - fold vs {pot_pct:.0%} pot")
    
    if hand_info.get('has_straight_draw'):
        # OESD: call up to 33% pot odds (~50% pot bet)
        if pot_odds <= 0.33:
            return ('call', 0, "straight draw - call")
        return ('fold', 0, f"straight draw - fold vs {pot_pct:.0%} pot")
    
    return ('fold', 0, f"{desc} - fold")


def _postflop_sonnet(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                     strength, desc, draws, combo_draw, has_flush_draw, has_oesd,
                     is_overpair, board_has_ace, is_underpair_to_ace=False, is_multiway=False):
    """
    Sonnet postflop: Bigger value bets, overpair logic.
    Uses pot_pct for bet-size aware decisions.
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
    
    # === FACING BET ===
    # Use pot_pct for smarter bet-size decisions
    # Per sonnet file: "Turn raises 95% value, river raises 98% value → fold one pair"
    
    pot_pct = to_call / pot if pot > 0 else 0
    
    if strength >= 6:
        return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
    if strength >= 5:
        return ('raise', round(to_call * 1.0, 2), f"{desc} - raise strong")
    if strength == 4:
        return ('raise', round(to_call * 1.0, 2), f"{desc} - raise set/trips")
    if strength == 3:
        # Two pair: call, but fold to big river bets
        if street == 'river' and pot_pct > 0.75:
            return ('fold', 0, f"{desc} - fold two pair vs {pot_pct:.0%} pot")
        return ('call', 0, f"{desc} - call two pair")
    
    # Underpair to ace - call small flop bets only
    if hand_info['is_underpair_to_ace']:
        if street == 'flop' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call flop (pocket pair below ace)")
        return ('fold', 0, f"{desc} - fold (ace on board)")
    
    # Overpair - call small/medium bets, fold big bets on turn/river
    if hand_info['is_overpair']:
        if street == 'flop':
            return ('call', 0, f"{desc} overpair - call")
        if pot_pct <= 0.5:
            return ('call', 0, f"{desc} overpair - call {street}")
        return ('fold', 0, f"{desc} overpair - fold vs {pot_pct:.0%} pot")
    
    # TPGK - call flop/turn, fold big river bets
    if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        if street == 'turn' and pot_pct <= 0.6:
            return ('call', 0, f"{desc} - call turn")
        if street == 'river' and pot_pct <= 0.45:
            return ('call', 0, f"{desc} - call small river")
        return ('fold', 0, f"{desc} - fold vs {pot_pct:.0%} pot")
    
    # TPWK - call small flop bets only
    if hand_info['has_top_pair']:
        if street == 'flop' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call flop")
        return ('fold', 0, f"{desc} - fold {street}")
    
    # Middle pair - call small flop bets only
    if hand_info['has_middle_pair']:
        if street == 'flop' and pot_pct <= 0.4:
            return ('call', 0, f"{desc} - call flop once")
        return ('fold', 0, f"{desc} - fold {street}")
    
    # Bottom pair - fold
    if hand_info['has_bottom_pair']:
        return ('fold', 0, f"{desc} - fold (bottom pair)")
    
    # Draws - conservative thresholds
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
            return ('raise', round(to_call * 1.0, 2), f"{desc} - raise strong")
        if strength == 4:
            return ('raise', round(to_call * 1.0, 2), f"{desc} - raise set/trips")
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
        
        # 3-bet bluff (always or 40% depending on strategy)
        if opener_pos in ['CO', 'BTN'] and hand in strategy.get('3bet_bluff', set()):
            if strategy.get('3bet_bluff_always') or random.random() < 0.4:
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
