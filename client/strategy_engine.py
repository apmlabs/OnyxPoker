"""
Strategy Engine - Hardcoded poker strategies from top-performing bots.
Takes table data and returns action + reasoning.
"""

from typing import Dict, Any, Optional, List, Set

# Strategy definitions based on simulation results (1M hands)
# Ranked: gpt3 (+20.49), gpt4 (+19.87), sonnet (+19.57), kiro_optimal (+19.53)

STRATEGIES = {
    'gpt3': {
        'name': 'GPT3 Strategy',
        'description': 'Best performer - balanced aggression',
        # Open ranges by position
        'open': {
            'UTG': '77+, ATs+, KQs, AJo+, AQo+',
            'MP': '66+, ATs+, A5s-A2s, KJs+, QJs, JTs, KQo, AJo+, AQo+',
            'CO': '55+, A8s+, A5s-A2s, KTs+, QTs+, JTs, T9s, 98s, 87s, ATo+, KJo+, QJo',
            'BTN': '22+, A2s+, K7s+, Q8s+, J8s+, T8s+, 97s+, 86s+, 75s+, 65s, 54s, A2o+, KTo+, QTo+, JTo, T9o, 98o',
            'SB': '22+, A2s+, K6s+, Q7s+, J7s+, T7s+, 97s+, 86s+, 75s+, 65s, 54s, ATo+, KJo+, QJo, JTo',
        },
        # 3-bet ranges
        '3bet_value': {
            'vs_UTG': 'QQ+, AKs, AKo',
            'vs_MP': 'JJ+, AKs, AKo, AQs',
            'vs_CO': 'TT+, AJs+, AQo+, KQs',
            'vs_BTN': 'TT+, AJs+, AQo+, KQs',
        },
        '3bet_bluff': 'A5s-A2s',
        # Call ranges vs open
        'call_open': {
            'vs_UTG': '99-22, AQs-AJs, KQs, QJs, JTs, T9s, 98s',
            'vs_MP': '99-22, AQs-AJs, KQs, QJs, JTs, T9s, 98s',
            'vs_CO': '99-22, AJs-ATs, KQs-KJs, QJs, JTs, T9s, 98s, 87s',
            'vs_BTN': '99-22, AJs-ATs, KQs-KJs, QJs, JTs, T9s, 98s, 87s',
        },
        # BB defense
        'bb_defend': '99-22, A2s+, K8s+, Q9s+, J9s+, T8s+, 97s+, 86s+, 75s+, 65s, 54s, A8o+, KTo+, QTo+, JTo, T9o, 98o',
        # vs 3-bet
        'vs_3bet_4bet': 'QQ+, AKs, AKo',
        'vs_3bet_call': 'JJ-TT, AQs, AKo, KQs',
    },
    'gpt4': {
        'name': 'GPT4 Strategy',
        'description': 'Second best - includes HUD adjustments',
        'open': {
            'UTG': '77+, ATs+, KQs, AJo+, AQo+',
            'MP': '66+, ATs+, A5s-A2s, KJs+, QJs, JTs, KQo, AJo+, AQo+',
            'CO': '55+, A8s+, A5s-A2s, KTs+, QTs+, JTs, T9s, 98s, 87s, ATo+, KJo+, QJo',
            'BTN': '22+, A2s+, K7s+, Q8s+, J8s+, T8s+, 97s+, 86s+, 75s+, 65s, 54s, A2o+, KTo+, QTo+, JTo, T9o, 98o',
            'SB': '22+, A2s+, K6s+, Q7s+, J7s+, T7s+, 97s+, 86s+, 75s+, 65s, 54s, ATo+, KJo+, QJo, JTo',
        },
        '3bet_value': {
            'vs_UTG': 'QQ+, AKs, AKo',
            'vs_MP': 'JJ+, AKs, AKo, AQs',
            'vs_CO': 'TT+, AJs+, AQo+, KQs',
            'vs_BTN': 'TT+, AJs+, AQo+, KQs',
        },
        '3bet_bluff': 'A5s-A2s, KTs-K9s',
        'call_open': {
            'vs_UTG': '99-22, AQs-AJs, KQs, QJs, JTs, T9s, 98s',
            'vs_MP': '99-22, AQs-AJs, KQs, QJs, JTs, T9s, 98s',
            'vs_CO': '99-22, AJs-ATs, KQs-KJs, QJs, JTs, T9s, 98s, 87s',
            'vs_BTN': '99-22, AJs-ATs, KQs-KJs, QJs, JTs, T9s, 98s, 87s',
        },
        'bb_defend': 'A2s+, K8s+, Q9s+, J9s+, T8s+, 97s+, 86s+, 75s+, 65s, 54s, A8o+, KTo+, QTo+, JTo, T9o, 98o',
        'vs_3bet_4bet': 'QQ+, AKs, AKo',
        'vs_3bet_call': 'JJ-TT, AQs, AKo, KQs',
    },
    'sonnet': {
        'name': 'Sonnet Strategy',
        'description': 'Third best - exploitative style',
        'open': {
            'UTG': '77+, ATs+, KQs, AQo+',
            'MP': '66+, A9s+, A5s-A2s, KJs+, QJs, JTs, AJo+, KQo',
            'CO': '44+, A2s+, K9s+, Q9s+, J9s+, T8s+, 97s+, 86s+, 76s, 65s, ATo+, KJo+, QJo',
            'BTN': '22+, A2s+, K6s+, Q7s+, J7s+, T7s+, 96s+, 85s+, 75s+, 64s+, 54s, A7o+, K9o+, QTo+, JTo',
            'SB': '55+, A2s+, K8s+, Q9s+, J9s+, T8s+, 98s, 87s, A9o+, KTo+',
        },
        '3bet_value': {
            'vs_UTG': 'QQ+, AKs, AKo',
            'vs_MP': 'QQ+, AKs, AKo',
            'vs_CO': 'JJ+, AQs+, AKo',
            'vs_BTN': 'TT+, AQs+, AKo',
        },
        '3bet_bluff': 'A5s-A4s, K9s-K8s',
        'call_open': {
            'vs_UTG': 'JJ-88, AQs-AJs, KQs',
            'vs_MP': 'JJ-88, AQs-AJs, KQs',
            'vs_CO': 'TT-66, AJs-ATs, KQs-KJs, QJs, JTs, T9s',
            'vs_BTN': '99-44, ATs-A8s, KJs-KTs, QJs-QTs, JTs, T9s, 98s, 87s',
        },
        'bb_defend': '99-22, AJs-A2s, KTs+, Q9s+, J9s+, T8s+, 97s+, 86s+, 76s, 65s, 54s, A9o+, KJo, QJo, JTo',
        'vs_3bet_4bet': 'KK+, AKs',
        'vs_3bet_call': 'QQ, JJ, AKo, AQs',
    },
    'kiro_optimal': {
        'name': 'Kiro Optimal Strategy',
        'description': 'Fourth best - solid fundamentals',
        'open': {
            'UTG': '77+, ATs+, KQs, AQo+',
            'MP': '66+, A9s+, A5s-A2s, KJs+, QJs, JTs, AJo+, KQo',
            'CO': '44+, A2s+, K9s+, Q9s+, J9s+, T8s+, 97s+, 86s+, 76s, 65s, ATo+, KJo+, QJo',
            'BTN': '22+, A2s+, K5s+, Q7s+, J7s+, T7s+, 96s+, 85s+, 75s+, 64s+, 54s, A7o+, K9o+, QTo+, JTo',
            'SB': '55+, A2s+, K8s+, Q9s+, J9s+, T8s+, 98s, 87s, A9o+, KTo+',
        },
        '3bet_value': {
            'vs_UTG': 'QQ+, AKs, AKo',
            'vs_MP': 'QQ+, AKs, AKo',
            'vs_CO': 'JJ+, AQs+, AKo',
            'vs_BTN': 'TT+, AQs+, AKo',
        },
        '3bet_bluff': 'A5s-A4s, K9s',
        'call_open': {
            'vs_UTG': 'JJ-88, AQs-AJs, KQs',
            'vs_MP': 'JJ-88, AQs-AJs, KQs',
            'vs_CO': 'TT-66, AJs-ATs, KQs-KJs, QJs, JTs, T9s',
            'vs_BTN': '99-44, ATs-A8s, KJs-KTs, QJs-QTs, JTs, T9s, 98s, 87s',
        },
        'bb_defend': '99-22, AJs-A2s, KTs+, Q9s+, J9s+, T8s+, 97s+, 86s+, 76s, 65s, 54s, A9o+, KJo, QJo',
        'vs_3bet_4bet': 'KK+, AKs',
        'vs_3bet_call': 'QQ, JJ, AKo, AQs',
    },
}

DEFAULT_STRATEGY = 'gpt3'


def parse_card(card: str) -> tuple:
    """Parse card string to (rank, suit). Returns (None, None) if invalid."""
    if not card or len(card) < 2:
        return (None, None)
    rank = card[:-1].upper()
    suit = card[-1].lower()
    return (rank, suit)


def get_hand_notation(cards: List[str]) -> Optional[str]:
    """Convert two cards to standard notation (e.g., 'AKs', 'QJo', '77')."""
    if not cards or len(cards) != 2:
        return None
    
    r1, s1 = parse_card(cards[0])
    r2, s2 = parse_card(cards[1])
    
    if not r1 or not r2:
        return None
    
    # Rank order for sorting
    rank_order = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10, '10': 10,
                  '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
    
    # Normalize 10 to T
    if r1 == '10':
        r1 = 'T'
    if r2 == '10':
        r2 = 'T'
    
    v1 = rank_order.get(r1, 0)
    v2 = rank_order.get(r2, 0)
    
    # Sort high to low
    if v1 < v2:
        r1, r2 = r2, r1
        s1, s2 = s2, s1
    
    if r1 == r2:
        return r1 + r2  # Pair: "AA", "KK"
    elif s1 == s2:
        return r1 + r2 + 's'  # Suited: "AKs"
    else:
        return r1 + r2 + 'o'  # Offsuit: "AKo"


def expand_range(range_str: str) -> Set[str]:
    """Expand range notation to set of hands."""
    hands = set()
    if not range_str:
        return hands
    
    rank_order = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    
    for part in range_str.replace(' ', '').split(','):
        part = part.strip()
        if not part:
            continue
        
        # Pair range: "77+" or "99-22"
        if len(part) >= 2 and part[0] == part[1] and part[0] in rank_order:
            if '+' in part:
                start_idx = rank_order.index(part[0])
                for r in rank_order[:start_idx + 1]:
                    hands.add(r + r)
            elif '-' in part:
                high, low = part.split('-')
                hi_idx = rank_order.index(high[0])
                lo_idx = rank_order.index(low[0])
                for i in range(hi_idx, lo_idx + 1):
                    hands.add(rank_order[i] + rank_order[i])
            else:
                hands.add(part[:2])
        
        # Suited/offsuit range: "ATs+", "A5s-A2s", "KQo"
        elif len(part) >= 3:
            suited = 's' in part
            offsuit = 'o' in part
            base = part.replace('s', '').replace('o', '').replace('+', '').replace('-', ' ').split()[0]
            
            if len(base) >= 2:
                high_rank = base[0]
                low_rank = base[1]
                suffix = 's' if suited else ('o' if offsuit else '')
                
                if '+' in part:
                    # ATs+ means ATs, AJs, AQs, AKs
                    hi_idx = rank_order.index(high_rank)
                    lo_idx = rank_order.index(low_rank)
                    for i in range(hi_idx + 1, lo_idx + 1):
                        hands.add(high_rank + rank_order[i] + suffix)
                elif '-' in part:
                    # A5s-A2s
                    parts = part.replace('s', '').replace('o', '').split('-')
                    if len(parts) == 2:
                        start_low = parts[0][1]
                        end_low = parts[1][1]
                        start_idx = rank_order.index(start_low)
                        end_idx = rank_order.index(end_low)
                        for i in range(start_idx, end_idx + 1):
                            hands.add(high_rank + rank_order[i] + suffix)
                else:
                    hands.add(base + suffix)
    
    return hands


def hand_in_range(hand: str, range_str: str) -> bool:
    """Check if hand is in range."""
    if not hand or not range_str:
        return False
    expanded = expand_range(range_str)
    return hand in expanded


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
        stack = table_data.get('hero_stack') or 100
        to_call = table_data.get('to_call') or 0
        position = (table_data.get('position') or 'BTN').upper()
        facing_raise = table_data.get('facing_raise', False)
        is_hero_turn = table_data.get('is_hero_turn', True)
        
        # Get hand notation
        hand = get_hand_notation(cards)
        if not hand:
            return {
                'action': 'fold',
                'bet_size': None,
                'reasoning': 'Could not parse hand',
                'strategy': self.strategy_name
            }
        
        # Preflop logic
        if not board:
            return self._preflop_action(hand, position, to_call, pot, stack, facing_raise)
        
        # Postflop - simplified for now
        return self._postflop_action(hand, board, pot, to_call, stack)
    
    def _preflop_action(self, hand: str, position: str, to_call: float, pot: float, stack: float, facing_raise: bool) -> Dict[str, Any]:
        """Preflop decision logic."""
        
        # Normalize position
        if position not in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
            position = 'BTN'
        
        # First to act (RFI)
        if to_call == 0 or (to_call <= 0.05 and not facing_raise):
            open_range = self.strategy['open'].get(position, '')
            if hand_in_range(hand, open_range):
                raise_size = round(2.5 * 0.05, 2)  # 2.5bb
                return {
                    'action': 'raise',
                    'bet_size': raise_size,
                    'reasoning': f'{hand} in {position} open range - raise 2.5bb',
                    'strategy': self.strategy_name
                }
            else:
                return {
                    'action': 'fold',
                    'bet_size': None,
                    'reasoning': f'{hand} not in {position} open range',
                    'strategy': self.strategy_name
                }
        
        # Facing a raise
        if facing_raise and to_call > 0:
            # Check 3-bet value range
            aggressor_pos = 'BTN'  # Default assumption
            value_range = self.strategy['3bet_value'].get(f'vs_{aggressor_pos}', '')
            if hand_in_range(hand, value_range):
                raise_size = round(to_call * 3.5, 2)
                return {
                    'action': 'raise',
                    'bet_size': raise_size,
                    'reasoning': f'{hand} in 3-bet value range - 3-bet to {raise_size}',
                    'strategy': self.strategy_name
                }
            
            # Check 3-bet bluff range
            bluff_range = self.strategy.get('3bet_bluff', '')
            if hand_in_range(hand, bluff_range):
                raise_size = round(to_call * 3.5, 2)
                return {
                    'action': 'raise',
                    'bet_size': raise_size,
                    'reasoning': f'{hand} in 3-bet bluff range - 3-bet to {raise_size}',
                    'strategy': self.strategy_name
                }
            
            # Check call range
            call_range = self.strategy['call_open'].get(f'vs_{aggressor_pos}', '')
            if hand_in_range(hand, call_range):
                return {
                    'action': 'call',
                    'bet_size': None,
                    'reasoning': f'{hand} in call range vs {aggressor_pos} open',
                    'strategy': self.strategy_name
                }
            
            # BB defense
            if position == 'BB':
                bb_range = self.strategy.get('bb_defend', '')
                if hand_in_range(hand, bb_range):
                    return {
                        'action': 'call',
                        'bet_size': None,
                        'reasoning': f'{hand} in BB defense range',
                        'strategy': self.strategy_name
                    }
        
        # Default fold
        return {
            'action': 'fold',
            'bet_size': None,
            'reasoning': f'{hand} not playable in this spot',
            'strategy': self.strategy_name
        }
    
    def _postflop_action(self, hand: str, board: List[str], pot: float, to_call: float, stack: float) -> Dict[str, Any]:
        """Simplified postflop logic - bet with made hands, check/fold weak."""
        
        # Very simplified - in reality would need hand strength evaluation
        # For now, just check if we can check, otherwise fold marginal
        
        if to_call == 0:
            # Can check - do so with most hands
            return {
                'action': 'check',
                'bet_size': None,
                'reasoning': 'Check to see next card',
                'strategy': self.strategy_name
            }
        
        # Facing bet - simplified: call small bets, fold large
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        
        if pot_odds < 0.25:
            return {
                'action': 'call',
                'bet_size': None,
                'reasoning': f'Good pot odds ({pot_odds:.0%}) - call',
                'strategy': self.strategy_name
            }
        
        return {
            'action': 'fold',
            'bet_size': None,
            'reasoning': 'Facing large bet without strong hand',
            'strategy': self.strategy_name
        }


def get_available_strategies() -> List[str]:
    """Return list of available strategy names."""
    return list(STRATEGIES.keys())


def get_strategy_info(name: str) -> Optional[Dict[str, str]]:
    """Return strategy name and description."""
    if name in STRATEGIES:
        return {
            'name': STRATEGIES[name]['name'],
            'description': STRATEGIES[name]['description']
        }
    return None
