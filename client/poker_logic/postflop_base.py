"""
Config-driven postflop base for strategies sharing the same decision tree:
  kiro/kiro_optimal/kiro5/kiro_v2, kiro_lord, sonnet/2nl_exploit/aggressive.

Strategies with unique logic remain in _monolith.py:
  value_lord, the_lord (active), gpt3/gpt4, sonnet_max, optimal_stats, value_max.
"""
import random
from poker_logic._monolith import analyze_hand, RANK_VAL


# ── Sizing tables ────────────────────────────────────────────────────────────

_KIRO_SIZINGS = {
    'flop':  {'nuts': 1.0, 'set': 0.85, 'twopair': 0.75, 'tptk': 0.70, 'tpgk': 0.65, 'tpwk': 0.60, 'overpair': 0.65},
    'turn':  {'nuts': 1.0, 'set': 0.85, 'twopair': 0.75, 'tptk': 0.60, 'tpgk': 0.55, 'tpwk': 0.0,  'overpair': 0.55},
    'river': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.75, 'tptk': 0.50, 'tpgk': 0.40, 'tpwk': 0.0,  'overpair': 0.45},
}

_SONNET_SIZINGS = {
    'flop':  {'nuts': 1.0, 'set': 0.85, 'twopair': 0.80, 'tptk': 0.75, 'tpgk': 0.70, 'tpwk': 0.65, 'overpair': 0.70},
    'turn':  {'nuts': 1.0, 'set': 0.85, 'twopair': 0.80, 'tptk': 0.70, 'tpgk': 0.60, 'tpwk': 0.0,  'overpair': 0.60},
    'river': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.80, 'tptk': 0.60, 'tpgk': 0.50, 'tpwk': 0.0,  'overpair': 0.50},
}

# ── Strategy configs ─────────────────────────────────────────────────────────

STRATEGY_CONFIGS = {
    'kiro': {
        'sizings': _KIRO_SIZINGS,
        'draw_semi_bluff': {'combo': 0.65, 'flush': 0.45},
        'draw_thresholds': {'flush': 0.40, 'straight': 0.33},
        'multiway_twopair': 0.65,
        'multiway_combo': 0.60,
    },
    'kiro_lord': {
        'sizings': _KIRO_SIZINGS,
        'draw_semi_bluff': {'combo': 0.65, 'flush': 0.45},
        'draw_thresholds': {'straight': 0.33},
        'draw_thresholds_nfd': 0.35,
        'draw_thresholds_non_nfd': 0.25,
        'multiway_twopair': 0.65,
        'multiway_combo': 0.60,
        # kiro_lord specific fixes
        'fold_pocket_under_board': True,
        'fold_pocket_over_river_pct': 0.50,
        'tpgk_turn_max_pct': 0.43,
        'tpgk_river_max_pct': 0.40,
    },
    'sonnet': {
        'sizings': _SONNET_SIZINGS,
        'draw_semi_bluff': {'combo': 0.70, 'flush': 0.50},
        'draw_thresholds': {'flush_nfd': 0.41, 'flush': 0.25, 'straight': 0.22},
        'multiway_twopair': 0.70,
        'multiway_combo': 0.65,
    },
}

# Aliases
STRATEGY_CONFIGS['kiro_optimal'] = STRATEGY_CONFIGS['kiro']
STRATEGY_CONFIGS['kiro5'] = STRATEGY_CONFIGS['kiro']
STRATEGY_CONFIGS['kiro_v2'] = STRATEGY_CONFIGS['kiro']
STRATEGY_CONFIGS['2nl_exploit'] = STRATEGY_CONFIGS['sonnet']
STRATEGY_CONFIGS['aggressive'] = STRATEGY_CONFIGS['sonnet']


def postflop_config_driven(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                           strength, desc, draws, combo_draw, has_flush_draw, has_oesd,
                           has_gutshot=False, has_any_draw=False,
                           is_overpair=False, board_has_ace=False, is_underpair_to_ace=False,
                           is_multiway=False, config_name='sonnet'):
    """Config-driven postflop. Drop-in replacement for kiro/kiro_lord/sonnet."""
    cfg = STRATEGY_CONFIGS.get(config_name, STRATEGY_CONFIGS['sonnet'])
    hand_info = analyze_hand(hole_cards, board)
    s = cfg['sizings'].get(street, {})
    pot_pct = to_call / pot if pot > 0 and to_call else 0
    pot_odds = to_call / (pot + to_call) if to_call and pot > 0 else 0

    # ── BETTING (checked to us) ──────────────────────────────────────────

    if to_call == 0 or to_call is None:
        if is_multiway:
            if strength >= 4:
                return ('bet', round(pot * s.get('set', 0.85), 2), f"{desc} - multiway value")
            if strength == 3:
                return ('bet', round(pot * cfg.get('multiway_twopair', 0.65), 2), f"{desc} - multiway value")
            if combo_draw:
                return ('bet', round(pot * cfg.get('multiway_combo', 0.60), 2), "combo draw - multiway semi-bluff")
            return ('check', 0, f"{desc} - check multiway")

        if strength >= 5:
            return ('bet', round(pot * s.get('nuts', 1.0), 2), f"{desc} - bet {int(s.get('nuts',1)*100)}%")
        if strength == 4:
            return ('bet', round(pot * s.get('set', 0.85), 2), f"{desc} - bet {int(s.get('set',0.85)*100)}%")
        if strength == 3:
            return ('bet', round(pot * s.get('twopair', 0.75), 2), f"{desc} - bet {int(s.get('twopair',0.75)*100)}%")

        if hand_info['is_underpair_to_ace']:
            return ('check', 0, f"{desc} - check (pocket pair below ace)")
        if hand_info['is_overpair']:
            return ('bet', round(pot * s.get('overpair', 0.65), 2), f"{desc} overpair - bet")

        if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
            return ('bet', round(pot * s.get('tptk', 0.70), 2), f"{desc} - value bet")
        if hand_info['has_top_pair'] and hand_info.get('kicker_val', 0) >= 6:
            return ('bet', round(pot * s.get('tpgk', 0.65), 2), f"{desc} - value bet")
        if hand_info['has_top_pair'] and street == 'flop':
            tpwk = s.get('tpwk', 0.60)
            if tpwk > 0:
                return ('bet', round(pot * tpwk, 2), f"{desc} - bet flop")

        # Draws
        dsb = cfg.get('draw_semi_bluff', {})
        if combo_draw:
            return ('bet', round(pot * dsb.get('combo', 0.65), 2), "combo draw - semi-bluff")
        if hand_info.get('has_flush_draw') and is_aggressor:
            return ('bet', round(pot * dsb.get('flush', 0.50), 2), "flush draw - semi-bluff")

        return ('check', 0, f"{desc} - check")

    # ── FACING BET ───────────────────────────────────────────────────────

    if strength >= 6:
        return ('raise', round(to_call * 3, 2), f"{desc} - raise monster")
    if strength >= 5:
        return ('raise', round(to_call * 1.0, 2), f"{desc} - raise strong")
    if strength == 4:
        return ('raise', round(to_call * 1.0, 2), f"{desc} - raise set/trips")

    # Two pair
    if strength == 3:
        if cfg.get('fold_pocket_under_board') and hand_info.get('two_pair_type') == 'pocket_under_board':
            return ('fold', 0, f"{desc} - fold (pocket under board)")
        pct_limit = cfg.get('fold_pocket_over_river_pct')
        if pct_limit and hand_info.get('two_pair_type') == 'pocket_over_board' and street == 'river' and pot_pct > pct_limit:
            return ('fold', 0, f"{desc} - fold pocket over vs {pot_pct:.0%} river")
        if street == 'river' and pot_pct > 0.75:
            return ('fold', 0, f"{desc} - fold two pair vs {pot_pct:.0%} pot")
        return ('call', 0, f"{desc} - call two pair")

    if hand_info['is_underpair_to_ace']:
        if street == 'flop' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call flop (pocket pair below ace)")
        return ('fold', 0, f"{desc} - fold (ace on board)")

    if hand_info['is_overpair']:
        if street == 'flop':
            return ('call', 0, f"{desc} overpair - call")
        if pot_pct <= 0.5:
            return ('call', 0, f"{desc} overpair - call {street}")
        return ('fold', 0, f"{desc} overpair - fold vs {pot_pct:.0%} pot")

    # kiro_lord: underpair call flop once
    if cfg.get('fold_pocket_under_board') and hand_info.get('is_pocket_pair') and not hand_info.get('is_overpair'):
        if street == 'flop' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call underpair flop once")
        return ('fold', 0, f"{desc} - fold underpair")

    # Top pair good kicker
    if hand_info['has_top_pair'] and hand_info['has_good_kicker']:
        turn_max = cfg.get('tpgk_turn_max_pct', 0.60)
        river_max = cfg.get('tpgk_river_max_pct', 0.45)
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        if street == 'turn' and pot_pct <= turn_max:
            return ('call', 0, f"{desc} - call turn")
        if street == 'river' and pot_pct <= river_max:
            return ('call', 0, f"{desc} - call small river")
        return ('fold', 0, f"{desc} - fold vs {pot_pct:.0%} pot")

    if hand_info['has_top_pair']:
        if street == 'flop' and pot_pct <= 0.5:
            return ('call', 0, f"{desc} - call flop")
        return ('fold', 0, f"{desc} - fold {street}")

    if hand_info['has_middle_pair']:
        if street == 'flop' and pot_pct <= 0.4:
            return ('call', 0, f"{desc} - call flop once")
        return ('fold', 0, f"{desc} - fold {street}")

    if hand_info['has_bottom_pair']:
        return ('fold', 0, f"{desc} - fold (bottom pair)")

    # Draws
    dt = cfg.get('draw_thresholds', {})
    if hand_info.get('has_flush_draw'):
        if hand_info.get('is_nut_flush_draw'):
            threshold = dt.get('flush_nfd', cfg.get('draw_thresholds_nfd', 0.41))
        else:
            threshold = dt.get('flush', cfg.get('draw_thresholds_non_nfd', 0.25))
        if pot_odds <= threshold:
            nfd_str = 'nut ' if hand_info.get('is_nut_flush_draw') else ''
            return ('call', 0, f"{nfd_str}flush draw - call")
    if hand_info.get('has_straight_draw') or has_oesd:
        threshold = dt.get('straight', 0.22)
        if pot_odds <= threshold:
            return ('call', 0, "straight draw - call")

    return ('fold', 0, f"{desc} - fold")
