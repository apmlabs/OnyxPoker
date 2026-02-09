"""
Strategy Engine - Uses shared poker_logic for decisions.
Takes table data from vision API and returns action + reasoning.
"""

from typing import Dict, Any, List, Tuple
from poker_logic import (
    STRATEGIES, RANK_VAL, parse_card, hand_to_str,
    check_draws, postflop_action, preflop_action,
    get_hand_info, analyze_hand
)

DEFAULT_STRATEGY = 'the_lord'


def get_hand_notation(cards: List[str]) -> str:
    """Convert card strings to hand notation."""
    if not cards or len(cards) != 2:
        return None
    
    parsed = []
    for c in cards:
        r, s = parse_card(c)
        if not r or not s:
            return None
        parsed.append((r, s))
    
    return hand_to_str(parsed)


def parse_board(board: List[str]) -> List[tuple]:
    """Convert board strings to tuples."""
    result = []
    for c in board or []:
        r, s = parse_card(c)
        if r and s:
            result.append((r, s))
    return result


class StrategyEngine:
    def __init__(self, strategy_name: str = DEFAULT_STRATEGY):
        if strategy_name not in STRATEGIES:
            strategy_name = DEFAULT_STRATEGY
        self.strategy_name = strategy_name
        self.strategy = STRATEGIES[strategy_name]
    
    def get_action(self, table_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine action based on table data and strategy."""
        
        cards = table_data.get('hero_cards') or []
        board = table_data.get('community_cards') or []
        pot = table_data.get('pot') or 0
        to_call = table_data.get('to_call') or 0
        position = (table_data.get('position') or 'BTN').upper()
        big_blind = table_data.get('big_blind') or 0.05  # Default to 5NL
        
        hand = get_hand_notation(cards)
        if not hand:
            return {
                'action': 'fold',
                'bet_size': None,
                'reasoning': 'Could not parse hand',
                'strategy': self.strategy_name
            }
        
        # Preflop
        if not board:
            return self._preflop(hand, position, to_call, big_blind, table_data)
        
        # Postflop
        return self._postflop(cards, board, pot, to_call, position, table_data)
    
    def _preflop(self, hand: str, position: str, to_call: float, big_blind: float = 0.05, table_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Preflop decision with call thresholds."""
        
        # Determine what we're facing based on to_call relative to big_blind
        # - to_call <= BB means no raise (just blinds)
        # - to_call > BB means someone raised
        if position == 'BB':
            if to_call <= big_blind * 0.5:  # Less than half BB = no raise
                facing = 'none'
                opener_pos = None
            elif to_call <= big_blind * 12:  # Up to 12BB = open raise
                facing = 'open'
                opener_pos = 'MP'
            else:
                facing = '3bet'
                opener_pos = None
        elif to_call <= big_blind:  # No raise - just blinds
            facing = 'none'
            opener_pos = None
        elif to_call <= big_blind * 12:  # Up to 12BB = open raise
            facing = 'open'
            opener_pos = 'MP'
        elif to_call <= big_blind * 40:  # Up to 40BB = 3bet
            facing = '3bet'
            opener_pos = None
        else:
            facing = '4bet'
            opener_pos = None
        
        action, reasoning = preflop_action(hand, position, self.strategy, facing, opener_pos)
        
        # THE_LORD: Adjust preflop action based on villain archetype
        if self.strategy_name == 'the_lord' and facing in ['open', '3bet'] and table_data:
            villain_archetype = self._get_villain_archetype(table_data)
            if villain_archetype:
                action, reasoning = self._the_lord_preflop_adjust(hand, action, reasoning, facing, villain_archetype)
        
        bet_size = None
        if action == 'raise':
            if facing == 'none':
                bet_size = round(big_blind * 6, 2)  # 3BB open (6x SB)
            elif facing == 'open':
                bet_size = round(to_call * 3.5, 2)
            elif facing == '3bet':
                bet_size = round(to_call * 2.5, 2)
        
        # Add call threshold info
        call_info = self._get_call_threshold(hand, position)
        bb_defense = self._get_bb_defense(hand)
        
        return {
            'action': action,
            'bet_size': bet_size,
            'reasoning': reasoning,
            'call_info': call_info,
            'bb_defense': bb_defense,
            'facing': facing,
            'strategy': self.strategy_name
        }
    
    def _get_call_threshold(self, hand: str, position: str) -> str:
        """Get action vs raise for this hand in this position."""
        s = self.strategy
        
        # Check which ranges this hand is in
        in_4bet = hand in s.get('4bet', set())
        in_call_3bet = hand in s.get('call_3bet', set())
        in_3bet_vs_pos = {}
        for pos in ['UTG', 'MP', 'CO', 'BTN']:
            in_3bet_vs_pos[pos] = hand in s.get('3bet_vs', {}).get(pos, set())
        in_3bet_bluff = hand in s.get('3bet_bluff', set())
        in_call_ip = hand in s.get('call_open_ip', set())
        in_bb_defend = hand in s.get('bb_defend', set())
        in_open = hand in s.get('open', {}).get(position, set())
        
        # Premium: AA, KK - 4bet/call any
        if in_4bet:
            return "4BET or CALL any"
        
        # Strong 3bet value hands (QQ+, AK)
        if any(in_3bet_vs_pos.values()) and in_call_3bet:
            return "3BET value, call 4bet"
        
        # 3bet bluff hands (A5s-A4s) - 3bet or fold
        if in_3bet_bluff:
            return "3BET bluff or FOLD"
        
        # Can call 3bets (JJ, TT, AQs)
        if in_call_3bet:
            return "CALL 3bet up to 15bb"
        
        # 3-bet hands that don't call 3bets - reraise or fold
        if any(in_3bet_vs_pos.values()) and not in_call_ip:
            return "3BET or FOLD"
        
        # Calling hands IP (not BB-specific)
        if in_call_ip:
            return "CALL up to 4bb"
        
        # BB defend hands
        if position == 'BB' and in_bb_defend:
            return "CALL up to 3bb"
        
        # Opening hands: can call min-raises only
        if in_open:
            return "CALL up to 2.5bb"
        
        return "FOLD"
    
    def _get_bb_defense(self, hand: str) -> str:
        """Get BB defense threshold for Line 1 display."""
        s = self.strategy
        
        in_4bet = hand in s.get('4bet', set())
        in_call_3bet = hand in s.get('call_3bet', set())
        in_bb_defend = hand in s.get('bb_defend', set())
        
        if in_4bet:
            return "CALL any"
        if in_call_3bet:
            return "CALL 6bb"
        if in_bb_defend:
            return "CALL 3bb"
        return "FOLD"
    
    def _the_lord_preflop_adjust(self, hand: str, base_action: str, base_reasoning: str, 
                                  facing: str, villain_archetype: str) -> Tuple[str, str]:
        """Adjust preflop action based on villain archetype for the_lord strategy.
        
        Based on advice:
        - vs Fish: Call wider (they raise weak)
        - vs Nit/Rock: Much tighter (they only raise premiums)
        - vs Maniac: QQ+/AK only (they raise everything)
        - vs LAG: 99+/AQ+ (they raise wide but have hands)
        - vs TAG: TT+/AK (baseline)
        """
        from poker_logic import THE_LORD_VS_RAISE
        
        # Only adjust when facing a raise
        if facing not in ['open', '3bet']:
            return (base_action, base_reasoning)
        
        vs_range = THE_LORD_VS_RAISE.get(villain_archetype, THE_LORD_VS_RAISE['tag'])
        
        # If hand is in the archetype-specific range, call/raise
        if hand in vs_range:
            if base_action == 'fold':
                return ('call', f'{hand} call vs {villain_archetype} raise')
            return (base_action, base_reasoning + f' vs {villain_archetype}')
        else:
            # Hand not in range - fold unless we were raising
            if base_action in ['call', 'check']:
                return ('fold', f'{hand} fold vs {villain_archetype} (not in range)')
            # If we were raising (3bet/4bet), check if it's still good
            if base_action == 'raise':
                # Only continue raising with premium hands vs tight players
                if villain_archetype in ['nit', 'rock']:
                    from poker_logic import expand_range
                    if hand not in expand_range('QQ+,AKs'):
                        return ('fold', f'{hand} fold vs {villain_archetype} (too tight to 3bet)')
            return (base_action, base_reasoning + f' vs {villain_archetype}')
    
    def _get_villain_archetype(self, table_data: Dict[str, Any]) -> str:
        """Get villain archetype from opponent_stats.
        
        For heads-up: use the single opponent with cards.
        For multiway: use the tightest archetype (most conservative).
        """
        opponent_stats = table_data.get('opponent_stats', [])
        if not opponent_stats:
            return None
        
        # Find opponents still in hand (have cards)
        opponents = table_data.get('opponents', [])
        active_names = {o['name'] for o in opponents if o.get('has_cards', False)}
        
        # Get archetypes of active opponents
        active_archetypes = []
        for opp in opponent_stats:
            if opp.get('name') in active_names and opp.get('archetype'):
                active_archetypes.append(opp['archetype'])
        
        if not active_archetypes:
            return None
        
        # If single opponent, use their archetype
        if len(active_archetypes) == 1:
            return active_archetypes[0]
        
        # Multiway: use tightest archetype (most conservative play)
        # Order from tightest to loosest: rock, nit, tag, lag, fish, maniac
        tightness_order = ['rock', 'nit', 'tag', 'lag', 'fish', 'maniac', 'unknown']
        for arch in tightness_order:
            if arch in active_archetypes:
                return arch
        
        return active_archetypes[0]
    
    def _postflop(self, cards: List[str], board: List[str], pot: float, to_call: float, position: str, table_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Postflop decision."""
        
        # Parse cards
        hole_cards = []
        for c in cards:
            r, s = parse_card(c)
            if r and s:
                hole_cards.append((r, s))
        
        board_cards = parse_board(board)
        
        if len(hole_cards) != 2:
            return {
                'action': 'fold',
                'bet_size': None,
                'reasoning': 'Could not parse hole cards',
                'strategy': self.strategy_name
            }
        
        # Determine street
        if len(board_cards) == 3:
            street = 'flop'
        elif len(board_cards) == 4:
            street = 'turn'
        else:
            street = 'river'
        
        # Position (simplified)
        is_ip = position in ['BTN', 'CO']
        
        # Get is_aggressor from table_data if available, otherwise default to True
        if table_data:
            is_aggressor = table_data.get('is_aggressor', True)
            # Get actual number of opponents from vision (num_players - 1 = opponents)
            num_opponents = max(1, (table_data.get('num_players', 2) - 1))
            is_facing_raise = table_data.get('is_facing_raise', False)
            # Get villain archetype for the_lord strategy
            villain_archetype = self._get_villain_archetype(table_data)
        else:
            is_aggressor = True  # Default for backward compatibility
            num_opponents = 1  # Default to heads-up
            is_facing_raise = False
            villain_archetype = None
        
        action, bet_size, reasoning = postflop_action(
            hole_cards, board_cards, pot, to_call, street, is_ip, is_aggressor,
            archetype=villain_archetype, strategy=self.strategy_name, num_opponents=num_opponents,
            is_facing_raise=is_facing_raise
        )
        
        # Get enhanced hand info
        hand_info = get_hand_info(hole_cards, board_cards, pot, to_call, num_opponents)
        
        # Get hand analysis for stats display
        hand_analysis = analyze_hand(hole_cards, board_cards)
        
        return {
            'action': action,
            'bet_size': bet_size if bet_size > 0 else None,
            'reasoning': reasoning,
            'strategy': self.strategy_name,
            'equity': hand_info['equity'],
            'hand_desc': hand_info['hand_desc'],
            'draws': hand_info['draws'],
            'outs': hand_info['outs'],
            'out_types': hand_info['out_types'],
            'pot_odds': hand_info['pot_odds'],
            'hand_analysis': hand_analysis
        }


def get_available_strategies() -> List[str]:
    return list(STRATEGIES.keys())
