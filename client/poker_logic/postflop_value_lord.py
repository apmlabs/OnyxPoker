"""Postflop strategy: value_lord - Conservative c-bet, aggressive value betting"""

from poker_logic.card_utils import RANK_VAL
from poker_logic.hand_analysis import analyze_hand

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


