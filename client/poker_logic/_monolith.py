"""
Shared poker logic for both poker_sim.py and strategy_engine.py.
Contains postflop decisions and equity calculation.
"""

from typing import Dict, List, Set, Tuple, Optional
import random
from itertools import combinations

# Re-export from submodules so internal references still work
from poker_logic.card_utils import RANKS, SUITS, RANK_VAL, parse_card, hand_to_str, calculate_equity, count_outs, get_hand_info
from poker_logic.hand_analysis import check_draws, analyze_hand
from poker_logic.preflop import expand_range, STRATEGIES, THE_LORD_VS_RAISE, preflop_action

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
    
    # THE_LORD: Check strategy first - it uses archetype for adjustments, not simulation
    if strategy == 'the_lord':
        return _postflop_the_lord(hole_cards, board, pot, to_call, street,
                                  strength, desc, has_any_draw, has_flush_draw, has_oesd, bb_size, is_aggressor, is_facing_raise, archetype, is_multiway)
    
    # ARCHETYPES TUNED TO REAL 2NL DATA (1036 hands, 122 opponents):
    # Real data Jan 17 2026 (2018 hands):
    # FISH: Check 41%, Bet 21%, Call 16%, Fold 20%, AF 1.55
    # NIT: Check 48%, Bet 18%, Call 15%, Fold 17%, AF 1.40
    # TAG: Check 39%, Bet 23%, Call 17%, Fold 19%, AF 1.45
    # LAG: Check 38%, Bet 25%, Call 17%, Fold 17%, AF 1.69
    # MANIAC: Check 29%, Bet 43%, Call 0%, Fold 29%, AF 99
    
    # Get hand info for archetypes (no string matching)
    hand_info = analyze_hand(hole_cards, board)
    
    # FISH: Target Check 41%, Bet 21%, Call 16%, Fold 20%
    # Fish play loosely - bet more, call more than old sim
    if archetype == 'fish':
        # Real data Jan 20 2026: Check 42%, Bet 21%, Call 17%, Fold 18%
        # Fish are calling stations - they call too much, fold too little
        pot_pct = to_call / pot if pot > 0 else 0
        if to_call == 0 or to_call is None:
            # First to act - bet value hands, check most else
            if strength >= 4:  # Sets+
                return ('bet', round(pot * 0.60, 2), f"{desc} - fish bets")
            if strength >= 3:  # Two pair
                return ('bet', round(pot * 0.55, 2), f"{desc} - fish bets two pair")
            if hand_info.get('has_top_pair'):
                if random.random() < 0.45:  # bet 45% of top pair (was 60%)
                    return ('bet', round(pot * 0.55, 2), f"{desc} - fish bets top pair")
                return ('check', 0, f"{desc} - fish checks top pair")
            if hand_info.get('is_overpair'):
                return ('bet', round(pot * 0.55, 2), f"{desc} - fish bets overpair")
            if strength >= 2:  # Weaker pairs - bet 20% (was 30%)
                if random.random() < 0.20:
                    return ('bet', round(pot * 0.45, 2), f"{desc} - fish bets weak pair")
                return ('check', 0, f"{desc} - fish checks pair")
            if has_any_draw:
                if random.random() < 0.15:  # semi-bluff 15% (was 25%)
                    return ('bet', round(pot * 0.45, 2), f"{desc} - fish semi-bluffs")
                return ('check', 0, f"{desc} - fish checks draw")
            # Air - bluff 5%
            if random.random() < 0.05:
                return ('bet', round(pot * 0.40, 2), f"{desc} - fish bluffs")
            return ('check', 0, "fish checks")
        else:
            # Facing bet - fish are STATIONS, they call way too much
            if strength >= 3:  # Two pair+ always call
                return ('call', 0, f"{desc} - fish calls strong")
            if hand_info.get('has_top_pair') or hand_info.get('is_overpair'):
                if pot_pct > 1.0:  # only fold to overbets
                    return ('fold', 0, f"{desc} - fish folds to overbet")
                return ('call', 0, f"{desc} - fish calls top pair")
            if strength >= 2:  # Any pair - call most of the time
                if pot_pct > 0.80:  # fold to big bets
                    return ('fold', 0, f"{desc} - fish folds weak pair to big bet")
                if random.random() < 0.75:  # call 75% of the time
                    return ('call', 0, f"{desc} - fish calls pair")
                return ('fold', 0, f"{desc} - fish folds pair")
            if has_any_draw:
                if pot_pct < 0.50:  # call draws with any odds
                    return ('call', 0, f"{desc} - fish calls draw")
                if random.random() < 0.40:  # still call 40% even bad odds
                    return ('call', 0, f"{desc} - fish chases draw")
                return ('fold', 0, f"{desc} - fish folds draw")
            # Air - still call sometimes (they're fish!)
            if pot_pct < 0.40 and random.random() < 0.25:
                return ('call', 0, f"{desc} - fish floats")
            return ('fold', 0, "fish folds")
    
    # NIT: Real data Jan 20 2026: Check 44%, Bet 23%, Call 14%, Fold 17%
    if archetype == 'nit':
        pot_pct = to_call / pot if pot > 0 else 0
        if to_call == 0 or to_call is None:
            # First to act - nits bet value hands, occasional semi-bluff
            if strength >= 4:  # Sets+
                return ('bet', round(pot * 0.65, 2), f"{desc} - nit value bets")
            if strength >= 3:  # Two pair
                return ('bet', round(pot * 0.60, 2), f"{desc} - nit bets two pair")
            if hand_info.get('has_top_pair'):
                if hand_info.get('has_good_kicker'):
                    return ('bet', round(pot * 0.60, 2), f"{desc} - nit bets TPGK")
                if random.random() < 0.55:  # bet TPWK 55%
                    return ('bet', round(pot * 0.50, 2), f"{desc} - nit bets top pair")
                return ('check', 0, f"{desc} - nit checks top pair")
            if hand_info.get('is_overpair'):
                return ('bet', round(pot * 0.60, 2), f"{desc} - nit bets overpair")
            if strength >= 2:  # Weaker pairs - bet 30%
                if random.random() < 0.30:
                    return ('bet', round(pot * 0.45, 2), f"{desc} - nit bets pair")
                return ('check', 0, f"{desc} - nit checks pair")
            # Draws - semi-bluff 15%
            if has_any_draw and random.random() < 0.15:
                return ('bet', round(pot * 0.45, 2), f"{desc} - nit semi-bluffs")
            return ('check', 0, "nit checks")
        else:
            # Facing bet - nits call value hands, fold marginal
            if strength >= 3:  # Two pair+
                return ('call', 0, f"{desc} - nit calls strong")
            if hand_info.get('has_top_pair') or hand_info.get('is_overpair'):
                if pot_pct > 0.75:  # fold to big bets
                    return ('fold', 0, f"{desc} - nit folds to big bet")
                return ('call', 0, f"{desc} - nit calls top pair")
            if strength >= 2:  # Weaker pairs
                if pot_pct > 0.50:
                    return ('fold', 0, f"{desc} - nit folds weak pair")
                if random.random() < 0.55:  # call 55%
                    return ('call', 0, f"{desc} - nit calls pair")
                return ('fold', 0, f"{desc} - nit folds pair")
            if has_any_draw and pot_pct < 0.35:
                return ('call', 0, f"{desc} - nit calls draw")
            return ('fold', 0, f"{desc} - nit folds")
    
    # TAG: Real data Jan 20 2026: Check 36%, Bet 32%, Call 10%, Fold 20%
    # TAGs bet A LOT more than old sim - biggest gap to fix
    if archetype == 'tag':
        # Real data Jan 20 2026: Check 36%, Bet 32%, Call 10%, Fold 20%
        pot_pct = to_call / pot if pot > 0 else 0
        if to_call == 0 or to_call is None:
            # First to act - TAGs bet value, selective bluffs
            if strength >= 4:  # Sets+
                return ('bet', round(pot * 0.65, 2), f"{desc} - tag value bets")
            if strength >= 3:  # Two pair
                return ('bet', round(pot * 0.60, 2), f"{desc} - tag bets two pair")
            if hand_info.get('has_top_pair') or hand_info.get('is_overpair'):
                return ('bet', round(pot * 0.55, 2), f"{desc} - tag bets top pair")
            if strength >= 2:  # Any pair - bet 35% (was 50%)
                if random.random() < 0.35:
                    return ('bet', round(pot * 0.50, 2), f"{desc} - tag bets pair")
                return ('check', 0, f"{desc} - tag checks pair")
            # Draws - semi-bluff 40% (was 60%)
            if has_any_draw:
                if random.random() < 0.40:
                    return ('bet', round(pot * 0.50, 2), f"{desc} - tag semi-bluffs")
                return ('check', 0, f"{desc} - tag checks draw")
            # Air - bluff 8% (was 15%)
            if random.random() < 0.08:
                return ('bet', round(pot * 0.45, 2), f"{desc} - tag bluffs")
            return ('check', 0, f"{desc} - tag checks")
        else:
            # Facing bet - TAGs are tighter callers (10% call rate)
            if strength >= 3:  # Two pair+
                return ('call', 0, f"{desc} - tag calls strong")
            if hand_info.get('has_top_pair') or hand_info.get('is_overpair'):
                if pot_pct > 0.65:
                    return ('fold', 0, f"{desc} - tag folds to big bet")
                return ('call', 0, f"{desc} - tag calls top pair")
            if strength >= 2:  # Weaker pairs - fold more
                if pot_pct > 0.50:
                    return ('fold', 0, f"{desc} - tag folds weak pair")
                if random.random() < 0.40:
                    return ('call', 0, f"{desc} - tag calls pair")
                return ('fold', 0, f"{desc} - tag folds pair")
            if has_any_draw and pot_pct < 0.35:
                return ('call', 0, f"{desc} - tag calls draw")
            return ('fold', 0, f"{desc} - tag folds")
    
    # LAG: Real data Jan 20 2026: Check 38%, Bet 27%, Call 15%, Fold 17%
    if archetype == 'lag':
        pot_pct = to_call / pot if pot > 0 else 0
        if to_call == 0 or to_call is None:
            # First to act - LAGs bet value, some bluffs (target 27%)
            if strength >= 4:  # Sets+
                return ('bet', round(pot * 0.65, 2), f"{desc} - lag value bets")
            if strength >= 3:  # Two pair
                return ('bet', round(pot * 0.60, 2), f"{desc} - lag bets two pair")
            if hand_info.get('has_top_pair') or hand_info.get('is_overpair'):
                return ('bet', round(pot * 0.55, 2), f"{desc} - lag bets top pair")
            if strength >= 2:  # Any pair - bet 25% (was 40%)
                if random.random() < 0.25:
                    return ('bet', round(pot * 0.50, 2), f"{desc} - lag bets pair")
                return ('check', 0, f"{desc} - lag checks pair")
            # Draws - semi-bluff 30% (was 50%)
            if has_any_draw:
                if random.random() < 0.30:
                    return ('bet', round(pot * 0.50, 2), f"{desc} - lag semi-bluffs")
                return ('check', 0, f"{desc} - lag checks draw")
            # Air - bluff 8% (was 12%)
            if random.random() < 0.08:
                return ('bet', round(pot * 0.45, 2), f"{desc} - lag bluffs")
            return ('check', 0, f"{desc} - lag checks")
        else:
            # Facing bet - LAGs call wider than TAG
            if strength >= 3:  # Two pair+
                return ('call', 0, f"{desc} - lag calls strong")
            if hand_info.get('has_top_pair') or hand_info.get('is_overpair'):
                if pot_pct > 0.75:
                    return ('fold', 0, f"{desc} - lag folds to big bet")
                return ('call', 0, f"{desc} - lag calls top pair")
            if strength >= 2:  # Weaker pairs
                if pot_pct > 0.60:
                    return ('fold', 0, f"{desc} - lag folds weak pair")
                if random.random() < 0.55:
                    return ('call', 0, f"{desc} - lag calls pair")
                return ('fold', 0, f"{desc} - lag folds pair")
            if has_any_draw and pot_pct < 0.45:
                return ('call', 0, f"{desc} - lag calls draw")
            return ('fold', 0, f"{desc} - lag folds")
    
    # MANIAC: Real data Jan 20 2026: Check 38%, Bet 28%, Call 15%, Fold 15%
    # MANIAC: Real data Jan 20 2026: Check 38%, Bet 28%, Call 15%, Fold 15%
    if archetype == 'maniac':
        pot_pct = to_call / pot if pot > 0 else 0
        if to_call == 0 or to_call is None:
            # First to act - maniacs bet value + some bluffs (target 28%)
            if strength >= 4:  # Sets+
                return ('bet', round(pot * 0.70, 2), f"{desc} - maniac bets big")
            if strength >= 3:  # Two pair
                return ('bet', round(pot * 0.60, 2), f"{desc} - maniac bets two pair")
            if hand_info.get('has_top_pair') or hand_info.get('is_overpair'):
                if random.random() < 0.80:  # bet 80% of top pair
                    return ('bet', round(pot * 0.55, 2), f"{desc} - maniac bets top pair")
                return ('check', 0, f"{desc} - maniac checks top pair")
            if strength >= 2:  # Any pair - bet 25% (was 35%)
                if random.random() < 0.25:
                    return ('bet', round(pot * 0.50, 2), f"{desc} - maniac bets pair")
                return ('check', 0, f"{desc} - maniac checks pair")
            # Draws - semi-bluff 18% (was 25%)
            if has_any_draw:
                if random.random() < 0.18:
                    return ('bet', round(pot * 0.50, 2), f"{desc} - maniac semi-bluffs")
                return ('check', 0, f"{desc} - maniac checks draw")
            # Air - bluff 6% (was 10%)
            if random.random() < 0.06:
                return ('bet', round(pot * 0.45, 2), f"{desc} - maniac bluffs")
            return ('check', 0, f"{desc} - maniac checks")
        else:
            # Facing bet - maniacs call/raise a lot
            if strength >= 3:  # Two pair+
                if random.random() < 0.30:
                    return ('raise', round(to_call * 2.5, 2), f"{desc} - maniac raises")
                return ('call', 0, f"{desc} - maniac calls strong")
            if hand_info.get('has_top_pair') or hand_info.get('is_overpair'):
                if random.random() < 0.20:
                    return ('raise', round(to_call * 2.5, 2), f"{desc} - maniac raises")
                return ('call', 0, f"{desc} - maniac calls top pair")
            if strength >= 2:  # Weaker pairs
                if pot_pct > 0.80:
                    return ('fold', 0, f"{desc} - maniac folds to overbet")
                if random.random() < 0.65:
                    return ('call', 0, f"{desc} - maniac calls pair")
                return ('fold', 0, f"{desc} - maniac folds pair")
            if has_any_draw:
                if random.random() < 0.60:
                    return ('call', 0, f"{desc} - maniac calls draw")
                return ('fold', 0, f"{desc} - maniac folds draw")
            # Float with air sometimes
            if random.random() < 0.20:
                return ('call', 0, f"{desc} - maniac floats")
            return ('fold', 0, f"{desc} - maniac folds")
    
    # ROCK: Tight passive - checks a lot, rarely bets, folds to aggression
    # Real data: median bet 55%, but rarely bets (only with strong hands)
    if archetype == 'rock':
        pot_pct = to_call / pot if pot > 0 else 0
        if to_call == 0 or to_call is None:
            # First to act - only bet with very strong hands
            if strength >= 4:  # Sets+
                return ('bet', round(pot * 0.55, 2), f"{desc} - rock value bets")
            if strength >= 3 and hand_info.get('two_pair_type') != 'pocket_under_board':
                return ('bet', round(pot * 0.50, 2), f"{desc} - rock bets two pair")
            if hand_info.get('has_top_pair') and hand_info.get('has_good_kicker'):
                if random.random() < 0.30:  # rarely bets TPGK
                    return ('bet', round(pot * 0.50, 2), f"{desc} - rock bets TPGK")
            # Everything else: check
            return ('check', 0, f"{desc} - rock checks")
        else:
            # Facing bet - folds a lot, only continues with strong hands
            if strength >= 4:
                return ('call', 0, f"{desc} - rock calls strong")
            if strength >= 3:
                if pot_pct > 0.60:
                    return ('fold', 0, f"{desc} - rock folds two pair to big bet")
                return ('call', 0, f"{desc} - rock calls two pair")
            if hand_info.get('has_top_pair'):
                if pot_pct > 0.50:
                    return ('fold', 0, f"{desc} - rock folds top pair")
                return ('call', 0, f"{desc} - rock calls top pair")
            if hand_info.get('is_overpair'):
                if pot_pct > 0.60:
                    return ('fold', 0, f"{desc} - rock folds overpair to big bet")
                return ('call', 0, f"{desc} - rock calls overpair")
            # Weak hands: fold
            return ('fold', 0, f"{desc} - rock folds")
    
    # BOT STRATEGIES - strategy-specific postflop logic
    # gpt3/gpt4: Board texture aware, smaller c-bets, 3-bet pot adjustments
    # sonnet/kiro_optimal: Bigger value bets, overpair logic
    # value_max: Maniac-style big bets but smarter (doesn't bluff as much)
    # value_maniac: Exact maniac postflop (overbets, calls wide)
    # BUT with paired board protection (learned from KK on JJ disaster)
    
    # NOTE: the_lord is checked earlier (before archetype handlers) since it uses archetype for adjustments
    
    if strategy == 'value_lord':
        return _postflop_value_lord(hole_cards, board, pot, to_call, street,
                                    strength, desc, has_any_draw, has_flush_draw, has_oesd, bb_size, is_aggressor, is_facing_raise, is_multiway)
    
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
        from poker_logic.postflop_base import postflop_config_driven
        return postflop_config_driven(hole_cards, board, pot, to_call, street, is_ip,
                                      is_aggressor, strength, desc, draws, combo_draw,
                                      has_flush_draw, has_oesd, has_gutshot, has_any_draw,
                                      is_overpair, board_has_ace, is_underpair_to_ace,
                                      is_multiway, config_name='kiro_lord')
    
    # Kiro strategies
    if strategy in ['kiro_optimal', 'kiro5', 'kiro_v2']:
        from poker_logic.postflop_base import postflop_config_driven
        return postflop_config_driven(hole_cards, board, pot, to_call, street, is_ip,
                                      is_aggressor, strength, desc, draws, combo_draw,
                                      has_flush_draw, has_oesd, has_gutshot, has_any_draw,
                                      is_overpair, board_has_ace, is_underpair_to_ace,
                                      is_multiway, config_name='kiro')
    
    # Sonnet-style strategies
    if strategy in ['sonnet', '2nl_exploit', 'aggressive']:
        from poker_logic.postflop_base import postflop_config_driven
        return postflop_config_driven(hole_cards, board, pot, to_call, street, is_ip,
                                      is_aggressor, strength, desc, draws, combo_draw,
                                      has_flush_draw, has_oesd, has_gutshot, has_any_draw,
                                      is_overpair, board_has_ace, is_underpair_to_ace,
                                      is_multiway, config_name='sonnet')
    
    # DEFAULT fallback (sonnet)
    from poker_logic.postflop_base import postflop_config_driven
    return postflop_config_driven(hole_cards, board, pot, to_call, street, is_ip,
                                  is_aggressor, strength, desc, draws, combo_draw,
                                  has_flush_draw, has_oesd, has_gutshot, has_any_draw,
                                  is_overpair, board_has_ace, is_underpair_to_ace,
                                  is_multiway, config_name='sonnet')


def _postflop_value_lord(hole_cards, board, pot, to_call, street, strength, desc, has_any_draw, 
                         has_flush_draw=False, has_oesd=False, bb_size=0.05, is_aggressor=False, 
                         is_facing_raise=False, is_multiway=False):
    """
    VALUE_LORD postflop - Data-driven betting from 2,018 real hands analysis.
    
    BETTING (checked to us):
    - Flop bluffs: only as aggressor, max 4BB (67% win as agg, 33% as non-agg >4BB)
    - Top pair+: 50% pot any size (78-89% win rate)
    - Two pair: 50% pot max on flop (bigger bets fold out worse hands)
    - Turn: only bet with TPWK+ (high card turn bets = 36% win)
    - River: big with nuts (full house+ = 100% win)
    
    CALLING (facing bet):
    - River high card: NEVER call (0% win on 6 calls)
    - Flop high card: fold >4BB (33% win rate)
    - Turn weak hands: fold (29-33% win rate)
    
    MULTIWAY (3+ players):
    - Bet smaller (50% max) to keep multiple callers
    - Only bet strong value (two pair+) or strong draws
    - Check everything else - too many opponents to bluff
    """
    # ~~~ VALUE_LORD SETUP ~~~
    hand_info = analyze_hand(hole_cards, board)
    bet_in_bb = to_call / bb_size if bb_size > 0 else 0
    pot_in_bb = pot / bb_size if bb_size > 0 else 0
    is_big_bet = to_call > 0 and pot > 0 and to_call >= pot * 0.5
    is_dangerous_board_pair = hand_info['board_pair_val'] is not None and hand_info['board_pair_val'] >= 8
    has_strong_draw = has_flush_draw or has_oesd
    is_paired_board = hand_info['has_board_pair']
    is_double_paired = hand_info.get('is_double_paired_board', False)
    combo_draw = has_flush_draw and has_oesd
    
    # ~~~ PAIRED BOARD DISCIPLINE ~~~
    if is_double_paired and strength < 5:
        # Pocket pair on double-paired = two pair (pocket + higher board pair)
        # 2NL villains bluff too much - call unless huge bet
        if hand_info['is_pocket_pair'] and strength == 3:
            pct = to_call / pot if pot > 0 else 0
            if pct > 0.75:
                return ('fold', 0, f"{desc} - fold pocket pair on double-paired vs big bet")
            return ('call', 0, f"{desc} - call pocket pair on double-paired")
        if to_call == 0:
            return ('check', 0, f"{desc} - check (double-paired board, need full house+)")
        return ('fold', 0, f"{desc} - fold (double-paired board, villain likely has full house)")
    
    if is_paired_board and not is_double_paired and street in ['turn', 'river']:
        if strength < 4 and to_call == 0:
            if not (hand_info['is_overpair'] and street == 'turn'):
                return ('check', 0, f"{desc} - check (paired board turn/river)")
    
    # Straight board detection
    board_vals = sorted([RANK_VAL[c[0]] for c in board], reverse=True) if board else []
    is_straight_board = False
    if len(board_vals) >= 4:
        for i in range(len(board_vals) - 3):
            window = board_vals[i:i+4]
            if max(window) - min(window) <= 5:
                is_straight_board = True
                break
    
    if to_call == 0 or to_call is None:
        # ~~~ VALUE_LORD: BETTING (checked to us) ~~~
        
        # MULTIWAY: bet smaller, only strong hands, no bluffs
        if is_multiway:
            # Nuts (full house+): 50% to keep callers
            if strength >= 5:
                return ('bet', round(pot * 0.5, 2), f"{desc} - 50% multiway value")
            # Set: 50% for value + protection
            if strength == 4:
                return ('bet', round(pot * 0.5, 2), f"{desc} - 50% multiway set")
            # Two pair: 40% pot control
            if strength == 3:
                return ('bet', round(pot * 0.4, 2), f"{desc} - 40% multiway two pair")
            # Overpair: 40% for value
            if hand_info['is_overpair']:
                return ('bet', round(pot * 0.4, 2), f"{desc} - 40% multiway overpair")
            # Top pair good kicker: 33% thin value
            if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
                return ('bet', round(pot * 0.33, 2), f"{desc} - 33% multiway TPGK")
            # Combo draw: 33% semi-bluff
            if combo_draw:
                return ('bet', round(pot * 0.33, 2), f"combo draw - 33% multiway semi-bluff")
            # Everything else: check (too many opponents to bluff)
            return ('check', 0, f"{desc} - check multiway")
        
        # MONSTERS (set+): bet big, 100% win rate
        if strength >= 4:
            if street == 'river':
                return ('bet', round(pot * 1.0, 2), f"{desc} - pot river value")
            return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot value")
        
        # TWO PAIR: 50% pot max (bigger bets fold out worse)
        if strength >= 3:
            if hand_info['two_pair_type'] in ['pocket_under_board', 'pocket_over_board']:
                if street == 'flop':
                    return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot (pot control)")
                return ('check', 0, f"{desc} - check (vulnerable two pair)")
            if hand_info['two_pair_type'] == 'one_card_board_pair' and is_dangerous_board_pair:
                if street == 'flop':
                    return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot (pot control)")
                return ('check', 0, f"{desc} - check (vulnerable to trips)")
            # Strong two pair (both cards hit)
            if street == 'turn':
                return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot turn")
            if street == 'river':
                return ('bet', round(pot * 1.0, 2), f"{desc} - pot river")
            return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot")
        
        # OVERPAIR: always bet (71-75% win rate)
        if hand_info['is_overpair']:
            return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot overpair")
        
        # TOP PAIR: 50% pot (78-89% win rate)
        if hand_info['has_top_pair']:
            if street == 'flop':
                return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot top pair")
            if street == 'turn':
                return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot turn")
            if street == 'river' and hand_info['has_good_kicker']:
                return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot TPGK river")
            return ('check', 0, f"{desc} - check (TPWK river)")
        
        # MIDDLE/BOTTOM PAIR: small bet flop only (36-73% win)
        if hand_info['has_middle_pair'] or hand_info['has_bottom_pair']:
            if street == 'flop':
                return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot flop")
            return ('check', 0, f"{desc} - check (weak pair turn/river)")
        
        # UNDERPAIR: bet flop only (89% win as agg on flop)
        if hand_info['is_pocket_pair']:
            if street == 'flop':
                return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot underpair")
            return ('check', 0, f"{desc} - check underpair")
        
        # DRAWS: semi-bluff flop only
        if has_any_draw and street == 'flop':
            bet_bb = pot_in_bb * 0.5
            if bet_bb <= 4 or is_aggressor:
                return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot draw")
            return ('check', 0, f"{desc} - check draw (too big)")
        
        # HIGH CARD C-BET: only as aggressor, max 4BB (67% win as agg, 0% as non-agg >10BB)
        if is_aggressor and street == 'flop':
            is_monotone = hand_info.get('board_flush_suit') is not None
            is_paired = hand_info.get('board_pair_val') is not None
            if is_monotone and not has_flush_draw:
                return ('check', 0, f"{desc} - check (monotone board)")
            if is_paired:
                return ('check', 0, f"{desc} - check (paired board)")
            # Cap c-bet at 4BB
            bet_amt = min(round(pot * 0.5, 2), bb_size * 4)
            return ('bet', bet_amt, f"{desc} - c-bet (max 4BB)")
        
        return ('check', 0, f"{desc} - check")
    else:
        # ~~~ VALUE_LORD: CALLING (facing bet) ~~~
        # Data: River high card = 0% win, Flop high card >4BB = 33%, Turn weak = 29-33%
        pot_pct = to_call / pot if pot > 0 else 0
        
        # MONSTERS: raise
        if strength >= 6:
            return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
        if strength >= 4:
            return ('raise', round(to_call * 2, 2), f"{desc} - raise set+")
        
        # TWO PAIR: call or fold based on type and aggression
        # 2NL villains check-raise bluff - only fold to >40% pot check-raises
        if strength == 3:
            if hand_info['two_pair_type'] == 'pocket_under_board':
                if pot_pct <= 0.5:
                    return ('call', 0, f"{desc} - call pocket under vs {pot_pct:.0%}")
                return ('fold', 0, f"{desc} - fold pocket under vs big bet")
            if hand_info['two_pair_type'] == 'pocket_over_board':
                if is_facing_raise and pot_pct > 0.6:
                    return ('fold', 0, f"{desc} - fold pocket over vs check-raise")
                return ('call', 0, f"{desc} - call pocket over")
            if hand_info['two_pair_type'] == 'both_cards_hit':
                if is_facing_raise and pot_pct > 0.6:
                    return ('fold', 0, f"{desc} - fold two pair vs check-raise")
                if pot_pct > 1.0:
                    return ('fold', 0, f"{desc} - fold two pair vs overbet")
                return ('call', 0, f"{desc} - call two pair")
            if hand_info['two_pair_type'] == 'one_card_board_pair':
                if is_facing_raise and pot_pct > 0.6:
                    return ('fold', 0, f"{desc} - fold one_card two pair vs check-raise")
                if street == 'river' and pot_pct > 0.66:
                    return ('fold', 0, f"{desc} - fold one_card two pair river")
                return ('call', 0, f"{desc} - call one_card two pair")
            return ('call', 0, f"{desc} - call two pair")
        
        # === RIVER CALLING (most critical - data shows clear patterns) ===
        if street == 'river':
            # HIGH CARD: NEVER call river (0% win on 6 calls)
            if strength < 2 and not hand_info['has_any_pair']:
                return ('fold', 0, f"{desc} - fold high card river (0% win rate)")
            
            # UNDERPAIR: fold river (50% but small sample, too risky)
            if hand_info['is_pocket_pair'] and not hand_info['is_overpair']:
                return ('fold', 0, f"{desc} - fold underpair river")
            
            # OVERPAIR: call small, fold big (50% overall)
            if hand_info['is_overpair']:
                if is_facing_raise and pot_pct > 0.6:
                    return ('fold', 0, f"{desc} - fold overpair vs check-raise")
                if pot_pct <= 0.5:
                    return ('call', 0, f"{desc} - call overpair river")
                return ('fold', 0, f"{desc} - fold overpair vs {pot_pct:.0%}")
            
            # TOP PAIR: 67% win rate on river, call reasonable bets
            if hand_info['has_top_pair']:
                if hand_info['has_good_kicker']:
                    if pot_pct <= 0.75:
                        return ('call', 0, f"{desc} - call TPGK river")
                    return ('fold', 0, f"{desc} - fold TPGK vs {pot_pct:.0%}")
                return ('fold', 0, f"{desc} - fold TPWK river")
            
            # WEAK PAIR: 50% win but risky
            if hand_info['has_middle_pair']:
                if pot_pct <= 0.33:
                    return ('call', 0, f"{desc} - call middle pair river small")
                return ('fold', 0, f"{desc} - fold middle pair river")
            
            # BOTTOM PAIR: fold river always
            if hand_info['has_bottom_pair']:
                return ('fold', 0, f"{desc} - fold bottom pair river")
            
            return ('fold', 0, f"{desc} - fold river")
        
        # === TURN CALLING (29-50% win for weak hands) ===
        if street == 'turn':
            # HIGH CARD: fold turn (29% win rate)
            if strength < 2 and not hand_info['has_any_pair']:
                if has_strong_draw:
                    pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1
                    if has_flush_draw and pot_odds <= 0.25:
                        return ('call', 0, f"{desc} - call flush draw turn")
                    if has_oesd and pot_odds <= 0.18:
                        return ('call', 0, f"{desc} - call OESD turn")
                return ('fold', 0, f"{desc} - fold high card turn (29% win)")
            
            # UNDERPAIR: fold turn (33% win rate)
            if hand_info['is_pocket_pair'] and not hand_info['is_overpair']:
                return ('fold', 0, f"{desc} - fold underpair turn")
            
            # OVERPAIR: call (67% win rate)
            if hand_info['is_overpair']:
                if is_facing_raise and pot_pct > 0.6:
                    return ('fold', 0, f"{desc} - fold overpair vs check-raise")
                return ('call', 0, f"{desc} - call overpair turn")
            
            # TOP PAIR: 50% win rate, but 0% vs raise >60%
            if hand_info['has_top_pair']:
                if is_facing_raise and pot_pct > 0.6:
                    return ('fold', 0, f"{desc} - fold top pair vs raise >{pot_pct:.0%}")
                if pot_pct <= 0.75:
                    return ('call', 0, f"{desc} - call top pair turn")
                return ('fold', 0, f"{desc} - fold top pair vs {pot_pct:.0%}")
            
            # WEAK PAIR: fold turn (33-50% win)
            if hand_info['has_middle_pair']:
                if pot_pct <= 0.33:
                    return ('call', 0, f"{desc} - call middle pair turn small")
                return ('fold', 0, f"{desc} - fold middle pair turn")
            
            # BOTTOM PAIR: fold turn always
            if hand_info['has_bottom_pair']:
                return ('fold', 0, f"{desc} - fold bottom pair turn")
            
            return ('fold', 0, f"{desc} - fold turn")
        
        # === FLOP CALLING (33-71% depending on strength) ===
        # HIGH CARD: fold >4BB (33% win rate)
        if strength < 2 and not hand_info['has_any_pair']:
            if has_strong_draw:
                pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1
                if has_flush_draw and pot_odds <= 0.30:
                    return ('call', 0, f"{desc} - call flush draw")
                if has_oesd and pot_odds <= 0.22:
                    return ('call', 0, f"{desc} - call OESD")
            if bet_in_bb <= 4:
                return ('call', 0, f"{desc} - call high card flop (small)")
            return ('fold', 0, f"{desc} - fold high card flop >4BB")
        
        # UNDERPAIR: call small flop only (43% win)
        if hand_info['is_pocket_pair'] and not hand_info['is_overpair']:
            if pot_pct <= 0.4:
                return ('call', 0, f"{desc} - call underpair flop")
            return ('fold', 0, f"{desc} - fold underpair vs {pot_pct:.0%}")
        
        # OVERPAIR: call (50% but small sample)
        if hand_info['is_overpair']:
            return ('call', 0, f"{desc} - call overpair flop")
        
        # TOP PAIR: call (71% win rate overall, but 0% vs raise >50%)
        if hand_info['has_top_pair']:
            if is_facing_raise and pot_pct > 0.5:
                return ('fold', 0, f"{desc} - fold top pair vs raise >{pot_pct:.0%}")
            if pot_pct <= 1.0:
                return ('call', 0, f"{desc} - call top pair flop")
            return ('fold', 0, f"{desc} - fold top pair vs overbet")
        
        # MIDDLE PAIR: call small (75% win rate surprisingly)
        if hand_info['has_middle_pair']:
            if pot_pct <= 0.5:
                return ('call', 0, f"{desc} - call middle pair flop")
            return ('fold', 0, f"{desc} - fold middle pair vs {pot_pct:.0%}")
        
        # BOTTOM PAIR: call flop only small bets
        if hand_info['has_bottom_pair']:
            if pot_pct <= 0.33:
                return ('call', 0, f"{desc} - call bottom pair flop small")
            return ('fold', 0, f"{desc} - fold bottom pair flop")
        
        return ('fold', 0, f"{desc} - fold")


def _postflop_the_lord(hole_cards, board, pot, to_call, street, strength, desc, has_any_draw,
                       has_flush_draw=False, has_oesd=False, bb_size=0.05, is_aggressor=False, 
                       is_facing_raise=False, villain_archetype=None, is_multiway=False):
    """
    THE_LORD postflop - Opponent-aware adjustments on top of value_lord.
    
    Based on real player database advice:
    - vs Fish: Value bet big (70%), never bluff, call down (they bluff less)
    - vs Nit: Fold to their bets (bet=nuts), bluff more (they fold too much)
    - vs Rock: Same as nit but even more extreme
    - vs Maniac: Call down with medium hands (they bluff too much), never bluff
    - vs LAG: Call down more (they overbluff)
    - vs TAG: Baseline (value_lord default)
    
    KEY FIX (Session 64): When villain RAISES (especially check-raises), it's much stronger
    than a normal bet. Fold two pair/trips to raises - they have full house.
    
    MULTIWAY: Passed through to value_lord for smaller bets, tighter ranges.
    """
    # Default to FISH behavior if unknown (most 2NL unknowns are fish)
    # Real data: 216 misses vs unknown (-1069 BB) because we played too tight
    if not villain_archetype or villain_archetype == 'unknown':
        villain_archetype = 'fish'
    
    hand_info = analyze_hand(hole_cards, board)
    pot_pct = to_call / pot if pot > 0 and to_call else 0
    
    # Get value_lord's decision as baseline (pass through is_multiway)
    base_action, base_amount, base_reason = _postflop_value_lord(
        hole_cards, board, pot, to_call, street, strength, desc, has_any_draw,
        has_flush_draw, has_oesd, bb_size, is_aggressor, is_facing_raise, is_multiway
    )
    
    # === CRITICAL: VILLAIN RAISE HANDLING (applies to ALL archetypes) ===
    # When villain raises (especially after we bet = check-raise), they almost always have it
    # This is the #1 leak: calling raises with two pair/trips when villain has full house
    if is_facing_raise and to_call > 0:
        # Flush facing raise on river: FOLD - villain has full house
        # Real data: 54s flush lost 99BB, QTs flush lost 91BB to river raises
        # Flush is strength 6
        if strength == 6 and 'flush' in desc.lower() and street == 'river':
            return ('fold', 0, f"{desc} - fold flush vs river raise (villain has full house)")
        
        # Trips facing raise: FOLD only on PAIRED boards where full house is possible
        # Real data: KTs trips lost 43BB on Ac Kc Kd 5h Jd (board has KK AND 55 possible)
        # But: ATd trips on Ac Ah 7c - villain can't have FH without pocket 7s (unlikely)
        # FIX: Only fold trips when board has ANOTHER pair besides our trips
        if hand_info.get('has_trips') or 'trips' in desc.lower():
            board_ranks = [c[0] for c in board]
            # Find the trips rank (appears 2+ times on board, and we have one)
            hero_ranks = [c[0] for c in hole_cards]
            rank_counts = {}
            for r in board_ranks:
                rank_counts[r] = rank_counts.get(r, 0) + 1
            # Find which rank is our trips (board pair + hero card)
            trips_rank = None
            for r in hero_ranks:
                if rank_counts.get(r, 0) >= 2:
                    trips_rank = r
                    break
            # Board is "dangerous" if there's ANOTHER pair besides our trips
            board_has_other_pair = any(count >= 2 for r, count in rank_counts.items() if r != trips_rank)
            if board_has_other_pair:
                return ('fold', 0, f"{desc} - fold trips vs raise on paired board (villain has full house)")
        
        # Two pair facing raise: Only fold vs TAG/NIT/ROCK (they don't bluff check-raises)
        # Real data: AJs two pair lost 103BB to TAG check-raise
        # But: ATs +96BB, 77 +68BB won vs LAG/MANIAC/FISH raises (they bluff more)
        # FIX: Don't fold two pair when we have TOP PAIR component vs TAG
        # Real data: AKo on 3h Ad 5c 3d 6s - hero had TPTK + board pair, TAG raised turn
        # This is strong enough to call - TAG could have Ax
        if strength == 3 or hand_info.get('has_two_pair'):
            if villain_archetype in ['tag', 'nit', 'rock']:
                # Check if we have top pair as part of our two pair
                if hand_info.get('has_top_pair'):
                    return ('call', 0, f"{desc} - call two pair with top pair vs {villain_archetype} raise")
                return ('fold', 0, f"{desc} - fold two pair vs {villain_archetype} raise (they don't bluff)")
    
    # === SCARY BOARD HANDLING (river, flush possible + paired board) ===
    # When board has flush possible AND is paired on river, one-card two pair is very weak
    # Real data: AKo lost 100BB with Ah Ks on 3s Ts Qs Ad Qd - villain bet 3 streets
    # Only fold to BIG bets from TIGHT players on scary boards
    if street == 'river' and to_call > 0:
        two_pair_type = hand_info.get('two_pair_type', '')
        has_full_house = strength >= 7  # Don't fold full houses!
        if two_pair_type in ['one_card_board_pair', 'board_paired'] and not has_full_house:
            # Check if board has flush possible (3+ of same suit)
            board_suits = [c[1] for c in board]
            flush_possible = any(board_suits.count(s) >= 3 for s in set(board_suits))
            # Check if board is paired
            board_ranks = [c[0] for c in board]
            board_paired = len(board_ranks) != len(set(board_ranks))
            
            # Only fold to big bets (>50% pot) from tight players
            if flush_possible and board_paired and pot_pct > 0.5 and villain_archetype in ['nit', 'rock', 'tag', None]:
                return ('fold', 0, f"{desc} - fold one-card two pair on flush+paired board vs big bet")
    
    # === VILLAIN-SPECIFIC ADJUSTMENTS ===
    
    if villain_archetype == 'fish':
        # Fish: "Value bet | Calls too much | Never bluff"
        # Bet 100% pot for value (UI button), never bluff, fold to their RAISES (rare = nuts)
        
        if to_call == 0:  # Betting
            if base_action == 'bet' and strength >= 2:
                # Bet 100% pot - they call too much (UI has pot button)
                return ('bet', round(pot * 1.0, 2), f"{desc} - POT vs fish (calls too much)")
            if base_action == 'bet' and strength < 2:
                # C-bets are OK vs fish (they still fold 18%) - only block turn/river bluffs
                if is_aggressor and street == 'flop':
                    return (base_action, base_amount, base_reason + " vs fish")
                return ('check', 0, f"{desc} - no bluff vs fish")
        else:  # Facing bet
            # CRITICAL: NFD always calls - 36% equity beats any reasonable pot odds
            if hand_info.get('is_nut_flush_draw') and street in ['flop', 'turn']:
                return ('call', 0, f"{desc} - call NFD vs fish (36% equity)")
            
            if is_facing_raise:
                # FIX: Don't fold two pair+ vs fish raise - they raise with worse
                # Real data: QTs two pair on Qs Jc Ts lost 56.6 BB by folding to fish raise
                # Fish raise != nuts, they raise with top pair, draws, etc.
                if strength >= 3:  # Two pair or better
                    return ('call', 0, f"{desc} - call {desc} vs fish raise (they raise wide)")
                # Fish raise with weaker hands = fold
                if strength < 3:
                    return ('fold', 0, f"{desc} - fold to fish raise (rare = nuts)")
            # Fish bet = value, only call with TOP PAIR+ (not weak pairs)
            # Data shows calling weak pairs vs fish loses money
            if base_action == 'fold' and hand_info['has_top_pair'] and pot_pct <= 0.5:
                return ('call', 0, f"{desc} - call top pair vs fish")
        
        return (base_action, base_amount, base_reason + " vs fish")
    
    elif villain_archetype in ['nit', 'rock']:
        # Nit/Rock: "Fold to bets | Bet = nuts | Bluff more"
        # Their bet = strong, but call with two pair+ (they sometimes bluff)
        # Bet 50% pot (UI button) - they only call with nuts anyway
        # FIX: Call small bets (<30% pot) with high card on flop - they sometimes value bet thin
        # Real data: A6o on 4h 4s 7c - nit bet 43%, we folded, hero won 24.2 BB
        #            A9h on 7h 2s 2c - nit bet 60%, we folded, hero won 13.6 BB
        
        if to_call == 0:  # Betting
            # Bet 50% pot for value (UI has 1/2 pot button)
            if base_action == 'bet' and strength >= 2:
                return ('bet', round(pot * 0.5, 2), f"{desc} - 50% pot vs {villain_archetype}")
            # Bluff more - they fold too much
            if base_action == 'check' and street == 'flop' and is_aggressor:
                return ('bet', round(pot * 0.5, 2), f"{desc} - bluff vs {villain_archetype} (folds too much)")
        else:  # Facing bet
            # If we have a made hand (straight+), use value_lord logic - don't treat as draw
            if strength >= 5:
                return (base_action, base_amount, base_reason + f" vs {villain_archetype}")
            
            # FIX: Call with two pair+ vs nit/rock - they sometimes bluff
            # Real data: A6o on 4h 4s 7c - nit bet, we folded, they were bluffing (-31.6 BB miss)
            if strength >= 3:  # Two pair or better
                return ('call', 0, f"{desc} - call {desc} vs {villain_archetype} (strong hand)")
            
            # CRITICAL: NFD always calls - 36% equity beats any reasonable pot odds
            # Even vs nit's strong range, NFD has enough equity to call
            if hand_info.get('is_nut_flush_draw') and street in ['flop', 'turn']:
                return ('call', 0, f"{desc} - call NFD vs {villain_archetype} (36% equity)")
            
            # Regular flush draw or OESD - need better pot odds vs nit's strong range
            # NFD ~35% equity, OESD ~32% - need pot_pct < 50% to have odds
            if (has_flush_draw or has_oesd) and pot_pct <= 0.50:
                return ('call', 0, f"{desc} - call draw vs {villain_archetype} (good odds)")
            
            # FIX: Call small bets (<30% pot) on flop with high card - nits value bet thin
            if street == 'flop' and strength < 2 and pot_pct < 0.30:
                return ('call', 0, f"{desc} - call small nit bet (they value bet thin)")
            
            # Their bet = strong, but don't fold overpairs or top pair
            # Fold weak pairs (middle/bottom/underpair), keep top pair+
            is_weak_pair = (strength == 2 and not hand_info['is_overpair'] and 
                           not hand_info['has_top_pair'])
            if is_weak_pair and pot_pct > 0.3:
                return ('fold', 0, f"{desc} - fold to {villain_archetype} bet (bet = nuts)")
            # Also fold high card vs their bet (but not draws - handled above)
            if strength < 2 and pot_pct > 0.3:
                return ('fold', 0, f"{desc} - fold to {villain_archetype} bet (bet = nuts)")
        
        return (base_action, base_amount, base_reason + f" vs {villain_archetype}")
    
    elif villain_archetype == 'maniac':
        # Maniac: "Call everything | Can't fold | Call down"
        # Bet 100% pot for value (UI button), call down with medium hands
        # FIX: But respect their RAISES on turn/river with WEAK hands
        # Real data: AA lost 100BB on 7d 7c Td Jc vs maniac raise (they had quads/FH)
        #            But: 77 WON 126BB on 4h 9d 4d 9s vs maniac raise (pocket pair over board)
        # Key insight: Pocket pairs that make two pair with board pairs are STRONG
        #              One-card two pair / overpairs are WEAK vs maniac aggression
        
        if to_call == 0:  # Betting
            if base_action == 'bet' and strength >= 2:
                # Bet 100% pot - they call too much (UI has pot button)
                return ('bet', round(pot * 1.0, 2), f"{desc} - POT vs maniac (calls too much)")
            if base_action == 'bet' and strength < 2:
                # Never bluff maniac
                return ('check', 0, f"{desc} - no bluff vs maniac (can't fold)")
        else:  # Facing bet
            # KEY: Respect RAISES on turn/river even from maniacs
            if is_facing_raise:
                # Turn/river raise from maniac: fold OVERPAIRS (they have set/two pair)
                # Real data: AA lost 100BB, JJ lost 16.8BB vs maniac raises
                # But DON'T fold two pair made with pocket pair (77 on 4499 won 126BB)
                if street in ['turn', 'river'] and pot_pct > 0.40:
                    # Fold overpairs - they're beat by sets/two pair
                    if hand_info.get('is_overpair'):
                        return ('fold', 0, f"{desc} - fold overpair vs maniac {street} raise (they have set/two pair)")
                    # Fold underpairs on river with overcards
                    if hand_info.get('is_underpair') and street == 'river':
                        return ('fold', 0, f"{desc} - fold underpair vs maniac river raise")
                
                # Call with pairs+ (including two pair from pocket pairs)
                if strength >= 2:  # Any pair or better
                    return ('call', 0, f"{desc} - call vs maniac raise (they raise wide)")
                # Maniac RAISE with high card = fold
                return (base_action, base_amount, base_reason + " (maniac raise = has hand)")
            
            # vs maniac BET (not raise): call down much lighter
            if not is_facing_raise:
                if base_action == 'fold' and strength >= 2:
                    return ('call', 0, f"{desc} - call down vs maniac bet (bluffs too much)")
                if base_action == 'fold' and hand_info['is_overpair']:
                    return ('call', 0, f"{desc} - call overpair vs maniac bet")
                if base_action == 'fold' and hand_info['has_top_pair']:
                    return ('call', 0, f"{desc} - call top pair vs maniac bet")
        
        return (base_action, base_amount, base_reason + " vs maniac")
    
    elif villain_archetype == 'lag':
        # LAG: "Call down | Over-aggro"
        # Call down more vs BETS, but respect RAISES (LAGs raise with hands)
        # Exception: Don't call underpairs - they're too weak even vs LAG
        
        if to_call == 0:  # Betting
            pass  # Same as value_lord
        else:  # Facing bet
            # KEY: Respect RAISES from LAGs - they raise with real hands
            if is_facing_raise:
                # LAG RAISE = they have something, already handled above
                return (base_action, base_amount, base_reason + " (lag raise = has hand)")
            
            # Don't override underpair folds - underpairs are too weak (11% win rate)
            if hand_info.get('is_underpair'):
                return (base_action, base_amount, base_reason + " vs lag")
            
            # vs LAG BET (not raise): call down more with top pair+
            if not is_facing_raise:
                if base_action == 'fold' and hand_info['has_top_pair']:
                    return ('call', 0, f"{desc} - call top pair vs lag bet")
                # Call with overpairs
                if base_action == 'fold' and hand_info['is_overpair']:
                    return ('call', 0, f"{desc} - call overpair vs lag bet")
        
        return (base_action, base_amount, base_reason + " vs lag")
    
    # TAG: Fold high card (0% win rate in real data)
    # value_lord calls small bets with high card, but vs TAG this loses
    if villain_archetype == 'tag':
        if to_call > 0 and strength < 2 and not hand_info.get('has_any_pair'):
            # Check for draws first
            if hand_info.get('is_nut_flush_draw') and street in ['flop', 'turn']:
                return ('call', 0, f"{desc} - call NFD vs tag")
            if (has_flush_draw or has_oesd) and pot_pct <= 0.35:
                return ('call', 0, f"{desc} - call draw vs tag")
            return ('fold', 0, f"{desc} - fold high card vs tag (0% win rate)")
        return (base_action, base_amount, base_reason + " vs tag")
    
    # Unknown: use value_lord baseline
    return (base_action, base_amount, base_reason)


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


def _postflop_sonnet_max(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                         strength, desc, draws, combo_draw, has_flush_draw, has_oesd, has_any_draw):
    """
    SONNET_MAX: Sonnet postflop optimized for 2NL fish-heavy tables.
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
