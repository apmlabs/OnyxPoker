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
from poker_logic.postflop_value_lord import _postflop_value_lord
from poker_logic.postflop_the_lord import _postflop_the_lord
from poker_logic.postflop_inactive import _postflop_optimal_stats, _postflop_value_max, _postflop_gpt, _postflop_sonnet_max

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


