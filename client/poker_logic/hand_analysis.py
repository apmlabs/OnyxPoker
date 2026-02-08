"""
Hand analysis functions - single source of truth for hand evaluation.

check_draws() - Flush and straight draw detection
analyze_hand() - Complete hand property analysis
"""

from typing import List, Tuple
from collections import Counter
from poker_logic.card_utils import RANKS, RANK_VAL


def check_draws(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]]) -> List[str]:
    """Check for flush and straight draws. No draws on river.
    
    Returns list of draw types: ["flush_draw"], ["oesd"], ["gutshot"], or combinations.
    Single source of truth for draw detection - used by analyze_hand() and postflop_action().
    """
    draws = []
    if len(board) < 3 or len(board) >= 5:  # No draws preflop or on river
        return draws
    
    all_cards = hole_cards + board
    suits = [c[1] for c in all_cards]
    hero_suits = [c[1] for c in hole_cards]
    
    suit_counts = {}
    hero_suit_counts = {}
    for s in suits:
        suit_counts[s] = suit_counts.get(s, 0) + 1
    for s in hero_suits:
        hero_suit_counts[s] = hero_suit_counts.get(s, 0) + 1
    
    # Flush draw: 4 of a suit AND hero has 2 of that suit
    for s, count in suit_counts.items():
        if count == 4 and hero_suit_counts.get(s, 0) >= 2:
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


def analyze_hand(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]]) -> dict:
    """
    Analyze hand properties directly from cards.
    Returns dict with all relevant hand info for decision making.
    """
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
    
    # Draw detection - use check_draws() as single source of truth
    draws = check_draws(hole_cards, board)
    has_flush_draw = "flush_draw" in draws
    has_oesd = "oesd" in draws
    has_gutshot = "gutshot" in draws
    has_straight_draw = has_oesd or has_gutshot
    
    # Flush detection (made flush)
    hero_suits = [c[1] for c in hole_cards]
    board_suits = [c[1] for c in board] if board else []
    all_suits = hero_suits + board_suits
    suit_counts = Counter(all_suits)
    hero_suit_counts = Counter(hero_suits)
    has_flush = any(c >= 5 for c in suit_counts.values())
    
    # Nut flush draw detection - do we have the Ace or King of the flush suit?
    is_nut_flush_draw = False
    if has_flush_draw:
        flush_suit = [s for s, c in suit_counts.items() if c >= 4][0]
        hero_flush_cards = [c for c in hole_cards if c[1] == flush_suit]
        hero_flush_vals = [RANK_VAL[c[0]] for c in hero_flush_cards]
        board_flush_vals = [RANK_VAL[c[0]] for c in board if c[1] == flush_suit]
        if 12 in hero_flush_vals:  # Ace
            is_nut_flush_draw = True
        elif 11 in hero_flush_vals and 12 not in board_flush_vals:  # King, no Ace on board
            is_nut_flush_draw = True
    
    # Made straight detection
    all_vals_unique = sorted(set(hero_vals + board_vals))
    has_straight = False
    if len(all_vals_unique) >= 5:
        for i in range(len(all_vals_unique) - 4):
            window = all_vals_unique[i:i+5]
            if window[-1] - window[0] == 4:
                has_straight = True
    # Wheel straight check (A2345)
    if {12, 0, 1, 2, 3}.issubset(set(hero_vals + board_vals)):
        has_straight = True
    
    # Board texture analysis - straight possibilities
    board_straight_combos = []
    if len(board_vals) >= 3:
        board_vals_sorted = sorted(board_vals)
        for low in range(0, 9):
            straight = list(range(low, low + 5))
            if low == 0:
                straight = [12, 0, 1, 2, 3]
            board_in_straight = [v for v in board_vals if v in straight]
            if len(board_in_straight) >= 3:
                missing = [v for v in straight if v not in board_vals]
                if len(missing) == 2:
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
    # Straight
    elif has_straight:
        all_vals = sorted(set(hero_vals + board_vals))
        straight_high = 0
        if {12, 0, 1, 2, 3}.issubset(set(all_vals)):
            straight_high = 3
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
        'has_oesd': has_oesd,
        'has_gutshot': has_gutshot,
        'has_straight': has_straight,
        'board_straight_combos': board_straight_combos,
        'board_flush_suit': board_flush_suit,
        'hero_vals': hero_vals,
        'board_vals': board_vals,
        'top_board_val': top_board_val,
    }
