"""
poker_logic package - Re-exports everything from submodules and monolith.

All existing imports like `from poker_logic import analyze_hand` continue to work.
Code is being incrementally extracted into submodules.
"""

# Submodules (extracted from monolith)
from poker_logic.card_utils import RANKS, SUITS, RANK_VAL, parse_card, hand_to_str
from poker_logic.hand_analysis import check_draws, analyze_hand
from poker_logic.preflop import expand_range, STRATEGIES, THE_LORD_VS_RAISE, preflop_action

# Everything else from the monolith
from poker_logic._monolith import *
from poker_logic._monolith import (
    calculate_equity, count_outs, get_hand_info,
    postflop_action,
)
