"""
Strategy Engine - Uses shared poker_logic for decisions.
Takes table data from vision API and returns action + reasoning.
"""

from typing import Dict, Any, List
from poker_logic import (
    STRATEGIES, RANK_VAL, parse_card, hand_to_str,
    evaluate_hand, check_draws, postflop_action, preflop_action
)

DEFAULT_STRATEGY = 'gpt3'


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
        """Preflop decision."""
        
        # Determine what we're facing
        if to_call <= 0.05 and not facing_raise:
            facing = 'none'
            opener_pos = None
        elif to_call <= 0.20:  # Facing open (2-4bb)
            facing = 'open'
            opener_pos = 'BTN'  # Assume late position open
        elif to_call <= 0.60:  # Facing 3-bet
            facing = '3bet'
            opener_pos = None
        else:  # Facing 4-bet
            facing = '4bet'
            opener_pos = None
        
        action, reasoning = preflop_action(hand, position, self.strategy, facing, opener_pos)
        
        bet_size = None
        if action == 'raise':
            if facing == 'none':
                bet_size = 0.12  # 2.5bb
            elif facing == 'open':
                bet_size = round(to_call * 3.5, 2)
            elif facing == '3bet':
                bet_size = round(to_call * 2.5, 2)
        
        return {
            'action': action,
            'bet_size': bet_size,
            'reasoning': reasoning,
            'strategy': self.strategy_name
        }
    
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
        
        action, bet_size, reasoning = postflop_action(
            hole_cards, board_cards, pot, to_call, street, is_ip, is_aggressor,
            strategy=self.strategy_name
        )
        
        return {
            'action': action,
            'bet_size': bet_size if bet_size > 0 else None,
            'reasoning': reasoning,
            'strategy': self.strategy_name
        }


def get_available_strategies() -> List[str]:
    return list(STRATEGIES.keys())
