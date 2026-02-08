"""
poker_logic package - Re-exports everything from the original monolith.

All existing imports like `from poker_logic import analyze_hand` continue to work.
Code is being incrementally extracted into submodules.
"""

# Re-export everything from the monolith so existing imports work unchanged
from poker_logic._monolith import *
from poker_logic._monolith import (
    RANKS, SUITS, RANK_VAL,
    check_draws, analyze_hand, expand_range,
    hand_to_str, parse_card,
    calculate_equity, count_outs, get_hand_info,
    postflop_action, preflop_action,
    STRATEGIES, THE_LORD_VS_RAISE,
)
