"""Card constants and utility functions."""

from typing import List, Tuple

RANKS = '23456789TJQKA'
SUITS = 'shdc'
RANK_VAL = {r: i for i, r in enumerate(RANKS)}


def parse_card(card: str) -> Tuple[str, str]:
    """Parse card string like 'As' to ('A', 's')."""
    if not card or len(card) < 2:
        return (None, None)
    rank = card[:-1].upper()
    suit = card[-1].lower()
    if rank == '10':
        rank = 'T'
    return (rank, suit)


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


import random
from typing import Dict


def calculate_equity(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]],
                     num_opponents: int = 1, simulations: int = 1000) -> float:
    """Monte Carlo equity calculation. Returns win probability 0-100."""
    from poker_logic.hand_analysis import analyze_hand
    if len(board) < 3:
        return 0.0
    deck = [(r, s) for r in RANKS for s in SUITS]
    known = set(hole_cards + board)
    deck = [c for c in deck if c not in known]
    wins = 0
    ties = 0
    for _ in range(simulations):
        cards_needed = 5 - len(board)
        random.shuffle(deck)
        full_board = board + deck[:cards_needed]
        remaining = deck[cards_needed:]
        opp_hands = []
        idx = 0
        for _ in range(num_opponents):
            opp_hands.append([remaining[idx], remaining[idx+1]])
            idx += 2
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
    from poker_logic.hand_analysis import check_draws, analyze_hand
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
        outs += 8 if "flush_draw" not in draws else 6
        out_types.append("8 straight" if "flush_draw" not in draws else "6 straight")
    elif "gutshot" in draws:
        outs += 4
        out_types.append("4 gutshot")
    if hand_info['has_top_pair']:
        outs += 5
        out_types.append("5 improve pair")
    return (outs, out_types)


def get_hand_info(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]],
                  pot: float, to_call: float, num_opponents: int = 1) -> Dict:
    """Get comprehensive hand info for display."""
    from poker_logic.hand_analysis import check_draws, analyze_hand
    info = analyze_hand(hole_cards, board)
    rank, desc = info['strength'], info['desc']
    draws = check_draws(hole_cards, board)
    outs, out_types = count_outs(hole_cards, board)
    equity = calculate_equity(hole_cards, board, num_opponents, 500) if board else 0
    pot_odds = round(to_call / (pot + to_call) * 100, 1) if to_call > 0 else 0
    implied_needed = 0
    if outs > 0 and to_call > 0:
        draw_equity = outs * 2 if len(board) == 4 else outs * 4
        if draw_equity < pot_odds:
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
