"""Inactive postflop strategies: optimal_stats, value_max, gpt, sonnet_max"""

import random
from poker_logic.card_utils import RANK_VAL
from poker_logic.hand_analysis import analyze_hand

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
