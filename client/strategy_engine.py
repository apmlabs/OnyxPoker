"""
Strategy Engine - Uses shared poker_logic for decisions.
Takes table data from vision API and returns action + reasoning.
"""

from typing import Dict, Any, List
from poker_logic import (
    STRATEGIES, RANK_VAL, parse_card, hand_to_str,
    evaluate_hand, check_draws, postflop_action, preflop_action,
    get_hand_info
)

DEFAULT_STRATEGY = 'value_lord'


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
        facing_raise = table_data.get('facing_raise', False)
        
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
            return self._preflop(hand, position, to_call, facing_raise)
        
        # Postflop
        return self._postflop(cards, board, pot, to_call, position)
    
    def _preflop(self, hand: str, position: str, to_call: float, facing_raise: bool) -> Dict[str, Any]:
        """Preflop decision with call thresholds."""
        
        # Determine what we're facing
        # Key insight: to_call is the most reliable indicator
        # - to_call <= 0.02 means no raise (just blinds)
        # - to_call > 0.02 means someone raised
        if position == 'BB':
            if to_call <= 0.01:
                facing = 'none'
                opener_pos = None
            elif to_call <= 0.25:
                facing = 'open'
                opener_pos = 'MP'
            else:
                facing = '3bet'
                opener_pos = None
        elif to_call <= 0.02:  # No raise - ignore facing_raise flag
            facing = 'none'
            opener_pos = None
        elif to_call <= 0.25:
            facing = 'open'
            opener_pos = 'MP'
        elif to_call <= 0.80:
            facing = '3bet'
            opener_pos = None
        else:
            facing = '4bet'
            opener_pos = None
        
        action, reasoning = preflop_action(hand, position, self.strategy, facing, opener_pos)
        
        bet_size = None
        if action == 'raise':
            if facing == 'none':
                bet_size = 0.12
            elif facing == 'open':
                bet_size = round(to_call * 3.5, 2)
            elif facing == '3bet':
                bet_size = round(to_call * 2.5, 2)
        
        # Add call threshold info
        call_info = self._get_call_threshold(hand, position)
        
        return {
            'action': action,
            'bet_size': bet_size,
            'reasoning': reasoning,
            'call_info': call_info,
            'strategy': self.strategy_name
        }
    
    def _get_call_threshold(self, hand: str, position: str) -> str:
        """Get max call amount for this hand in this position."""
        s = self.strategy
        
        # Check which ranges this hand is in
        in_4bet = hand in s.get('4bet', set())
        in_call_3bet = hand in s.get('call_3bet', set())
        in_3bet = any(hand in s.get('3bet_vs', {}).get(pos, set()) 
                      for pos in ['UTG', 'MP', 'CO', 'BTN'])
        in_call_ip = hand in s.get('call_open_ip', set())
        in_bb_defend = hand in s.get('bb_defend', set())
        in_open = hand in s.get('open', {}).get(position, set())
        
        # Premium: AA, KK, QQ, AKs - can call any amount
        if in_4bet:
            return "ALL-IN ok"
        
        # Strong: JJ, TT, AQs - can call 3bets
        if in_call_3bet:
            return "call 3bet (15bb)"
        
        # 3-bet hands that don't call 3bets - raise or fold
        if in_3bet and not in_call_ip:
            return "3bet or fold"
        
        # Calling hands IP (not BB-specific)
        if in_call_ip:
            return "call open (4bb)"
        
        # BB defend hands - only applies in BB
        if position == 'BB' and in_bb_defend:
            return "BB defend (4bb)"
        
        # Opening hands only - fold to any raise
        if in_open:
            return "open only, fold vs raise"
        
        return "fold"
    
    def _postflop(self, cards: List[str], board: List[str], pot: float, to_call: float, position: str) -> Dict[str, Any]:
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
        is_aggressor = True  # Assume we were aggressor preflop
        
        # Default to heads-up (vision detector should provide num_players in future)
        num_opponents = 1
        
        action, bet_size, reasoning = postflop_action(
            hole_cards, board_cards, pot, to_call, street, is_ip, is_aggressor,
            strategy=self.strategy_name, num_opponents=num_opponents
        )
        
        # Get enhanced hand info
        hand_info = get_hand_info(hole_cards, board_cards, pot, to_call, num_opponents)
        
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
            'pot_odds': hand_info['pot_odds']
        }


def get_available_strategies() -> List[str]:
    return list(STRATEGIES.keys())
