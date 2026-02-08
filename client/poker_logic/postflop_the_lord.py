"""Postflop strategy: the_lord - Opponent-aware (default strategy)"""

from poker_logic.card_utils import RANK_VAL
from poker_logic.hand_analysis import analyze_hand
from poker_logic.postflop_value_lord import _postflop_value_lord

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


