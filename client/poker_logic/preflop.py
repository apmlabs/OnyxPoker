"""
Preflop logic - range expansion, strategy definitions, and preflop decisions.
"""

import random
from typing import Dict, Set, Tuple
from poker_logic.card_utils import RANKS, RANK_VAL


def expand_range(range_str: str) -> Set[str]:
    """Expand range notation to set of hands."""
    hands = set()
    
    def add_pairs(start, end='A'):
        for i in range(RANK_VAL[start], RANK_VAL[end] + 1):
            hands.add(RANKS[i] + RANKS[i])
    
    def add_hands(h1, h2, suited, plus=False):
        if plus:
            start_idx = RANK_VAL[h2]
            end_idx = RANK_VAL[h1] - 1
            for i in range(start_idx, end_idx + 1):
                hands.add(h1 + RANKS[i] + ('s' if suited else 'o'))
        else:
            hands.add(h1 + h2 + ('s' if suited else 'o'))
    
    for part in range_str.replace(' ', '').split(','):
        part = part.strip()
        if not part:
            continue
        
        if len(part) == 2 and part[0] == part[1]:
            add_pairs(part[0], part[0])
        elif len(part) == 3 and part[0] == part[1] and part[2] == '+':
            add_pairs(part[0], 'A')
        elif '-' in part and len(part) == 5 and part[0] == part[1]:
            add_pairs(part[3], part[0])
        elif part.endswith('s+'):
            add_hands(part[0], part[1], True, True)
        elif part.endswith('s') and '-' not in part:
            add_hands(part[0], part[1], True, False)
        elif 's-' in part:
            h1 = part[0]
            start = part[part.index('-')+2]
            end = part[1]
            for i in range(RANK_VAL[start], RANK_VAL[end] + 1):
                hands.add(h1 + RANKS[i] + 's')
        elif part.endswith('o+'):
            add_hands(part[0], part[1], False, True)
        elif part.endswith('o'):
            add_hands(part[0], part[1], False, False)
        elif len(part) == 3 and part[2] == '+':
            add_hands(part[0], part[1], True, True)
            add_hands(part[0], part[1], False, True)
    
    return hands


# Strategy definitions - from pokerstrategy files

STRATEGIES = {
    'gpt3': {
        'name': 'GPT3 Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AJo+,AQo+'),
            'MP': expand_range('66+,ATs+,A5s-A2s,KJs+,QJs,JTs,KQo,AJo+,AQo+'),
            'CO': expand_range('55+,A8s+,A5s-A2s,KTs+,QTs+,JTs,T9s,98s,87s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,54s,A7o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A5s+,K9s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo'), 'MP': expand_range('QQ+,AKs,AKo'), 'CO': expand_range('JJ+,AQs+,AKo'), 'BTN': expand_range('TT+,AQs+,AKo')},
        '3bet_bluff': expand_range('A5s-A4s'),
        'call_open_ip': expand_range('JJ-66,AQs-ATs,KQs-KJs,QJs,JTs,T9s,98s'),
        'bb_defend': expand_range('TT-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A9o+,KJo,QJo'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'kiro5': {
        'name': 'Kiro5 Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A3s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T7s+,96s+,85s+,75s+,64s+,54s,A8o+,K9o+,QTo+,JTo'),
            'SB': expand_range('44+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo'), 'MP': expand_range('QQ+,AKs,AKo'), 'CO': expand_range('JJ+,AQs+,AKo'), 'BTN': expand_range('TT+,AQs+,AKo')},
        '3bet_bluff': expand_range('A5s-A4s,K9s'),
        'call_open_ip': expand_range('JJ-88,AQs-AJs,KQs,TT-66,AJs-ATs,KQs-KJs,QJs,JTs,T9s,99-44,ATs-A9s,KJs-KTs,QJs-QTs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('99-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A9o+,KJo,QJo'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'kiro_v2': {
        'name': 'Kiro V2 Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A3s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('55+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,87s,76s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T7s+,96s+,85s+,75s,65s,54s,A8o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo'), 'MP': expand_range('QQ+,AKs,AKo'), 'CO': expand_range('JJ+,AQs+,AKo'), 'BTN': expand_range('TT+,AQs+,AKo')},
        '3bet_bluff': expand_range('A5s-A4s,K9s'),
        'call_open_ip': expand_range('JJ-77,AQs-ATs,KQs-KJs,QJs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('99-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A9o+,KJo,QJo'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'gpt4': {
        'name': 'GPT4 Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AJo+,AQo+'),
            'MP': expand_range('66+,ATs+,A5s-A2s,KJs+,QJs,JTs,KQo,AJo+,AQo+'),
            'CO': expand_range('55+,A8s+,A5s-A2s,KTs+,QTs+,JTs,T9s,98s,87s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,75s+,65s,54s,A2o+,KTo+,QTo+,JTo,T9o,98o'),
            'SB': expand_range('22+,A2s+,K6s+,Q7s+,J7s+,T7s+,97s+,86s+,75s+,65s,54s,ATo+,KJo+,QJo,JTo'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('JJ+,AKs,AKo,AQs'),
            'CO': expand_range('TT+,AJs+,AQo+,KQs'),
            'BTN': expand_range('TT+,AJs+,AQo+,KQs'),
        },
        '3bet_bluff': expand_range('A5s-A2s,KTs-K9s'),
        'call_open_ip': expand_range('99-22,AQs-AJs,KQs,QJs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,86s+,75s+,65s,54s,A8o+,KTo+,QTo+,JTo,T9o,98o'),
        'call_3bet': expand_range('JJ,TT,AQs,AKo,KQs'),
        '4bet': expand_range('QQ+,AKs,AKo'),
    },
    'sonnet': {
        'name': 'Sonnet Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A2s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K6s+,Q7s+,J7s+,T7s+,96s+,85s+,75s+,64s+,54s,A7o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('QQ+,AKs,AKo'),
            'CO': expand_range('JJ+,AQs+,AKo'),
            'BTN': expand_range('TT+,AQs+,AKo'),
        },
        '3bet_bluff': expand_range('A5s-A4s,K9s-K8s'),
        'call_open_ip': expand_range('JJ-66,AJs-ATs,KQs-KJs,QJs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('99-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,54s,A9o+,KJo,QJo,JTo'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'kiro_optimal': {
        'name': 'Kiro Optimal Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A2s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T7s+,96s+,85s+,75s+,64s+,54s,A7o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('QQ+,AKs,AKo'),
            'CO': expand_range('JJ+,AQs+,AKo'),
            'BTN': expand_range('TT+,AQs+,AKo'),
        },
        '3bet_bluff': expand_range('A5s-A4s,K9s'),
        'call_open_ip': expand_range('JJ-66,AJs-ATs,KQs-KJs,QJs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('99-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,54s,A9o+,KJo,QJo'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'kiro_lord': {
        # Same preflop as kiro_optimal, improved postflop
        'name': 'Kiro Lord Strategy',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A2s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T7s+,96s+,85s+,75s+,64s+,54s,A7o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('QQ+,AKs,AKo'),
            'CO': expand_range('JJ+,AQs+,AKo'),
            'BTN': expand_range('TT+,AQs+,AKo'),
        },
        '3bet_bluff': expand_range('A5s-A4s,K9s'),
        'call_open_ip': expand_range('JJ-66,AJs-ATs,KQs-KJs,QJs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('99-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,54s,A9o+,KJo,QJo'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    'aggressive': {
        'name': 'Aggressive 2NL',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AJo+'),
            'MP': expand_range('66+,A9s+,A5s-A2s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T7s+,96s+,85s+,75s+,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('JJ+,AKs,AKo,AQs'),
            'CO': expand_range('TT+,AQs+,AKo,AJs'),
            'BTN': expand_range('99+,AQs+,AKo,AJs,KQs'),
        },
        '3bet_bluff': expand_range('A5s-A2s,K9s'),
        'call_open_ip': expand_range('99-22,AJs-A9s,KQs-KTs,QJs-QTs,JTs,T9s,98s,87s,76s'),
        'bb_defend': expand_range('99-22,A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,54s,A8o+,KTo+,QTo+,JTo,T9o,98o'),
        'call_3bet': expand_range('JJ,TT,99,88,AQs,AQo,AJs,KQs'),
        '4bet': expand_range('QQ+,AKs,AKo'),
    },
    '2nl_exploit': {
        'name': '2NL Exploit',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AJo+'),
            'MP': expand_range('66+,A9s+,A5s-A2s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T7s+,96s+,85s+,75s+,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('JJ+,AKs,AKo,AQs'),
            'CO': expand_range('TT+,AQs+,AKo,AJs'),
            'BTN': expand_range('99+,AQs+,AKo,AJs,KQs'),
        },
        '3bet_bluff': expand_range('A5s-A2s,K9s'),
        'call_open_ip': expand_range('JJ-44,AJs-A7s,KQs-K9s,QJs-Q9s,JTs-J9s,T9s,98s,87s,76s'),
        'bb_defend': expand_range('99-22,A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,54s,A8o+,KTo+,QTo+,JTo,T9o,98o'),
        'call_3bet': expand_range('QQ,JJ,TT,99,88,AQs,AQo,AJs,KQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    # VALUE_MAX: Maniac-style ranges + aggressive postflop
    'value_max': {
        'name': 'Value Max',
        'open': {
            'UTG': expand_range('55+,A7s+,A5s-A2s,KTs+,QTs+,JTs,T9s,ATo+,KJo+'),
            'MP': expand_range('44+,A5s+,K8s+,Q9s+,J9s+,T8s+,97s+,87s,76s,A9o+,KTo+,QJo'),
            'CO': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A7o+,K9o+,QTo+,JTo'),
            'BTN': expand_range('22+,A2s+,K2s+,Q4s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A2o+,K7o+,Q9o+,J9o+,T9o'),
            'SB': expand_range('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A5o+,K8o+,QTo+,JTo'),
        },
        '3bet_vs': {'UTG': expand_range('TT+,AQs+,AKo,AJs,KQs'), 'MP': expand_range('99+,AJs+,AKo,AQo,KQs,QJs'), 'CO': expand_range('88+,ATs+,AJo+,KQs,KJs,QJs,JTs'), 'BTN': expand_range('77+,A9s+,ATo+,KJs+,KQo,QJs,JTs,T9s')},
        '3bet_bluff': expand_range('A5s-A2s,K9s-K6s,Q9s-Q8s,J9s,T9s,98s,87s,76s,65s,54s'),
        'call_open_ip': expand_range('TT-22,AJs-A5s,KQs-K9s,QJs-Q9s,JTs-J9s,T9s,98s,87s,76s'),
        'sb_defend': expand_range('TT-22,AJs-A2s,KQs-K8s,QJs-Q9s,JTs-J9s,T9s-T8s,98s,87s,76s,A5o+,KQo,KJo,QJo'),
        'bb_defend': expand_range('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
        'call_3bet': expand_range('JJ,TT,99,AKo,AQs,AQo,AJs,KQs'),
        '4bet': expand_range('QQ+,AKs,AKo'),
        'overbet': True,
    },
    # SONNET_MAX: Sonnet preflop + optimized postflop for 2NL fish-heavy tables
    'sonnet_max': {
        'name': 'Sonnet Max',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AQo+'),
            'MP': expand_range('66+,A9s+,A5s-A2s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K6s+,Q7s+,J7s+,T7s+,96s+,85s+,75s+,64s+,54s,A7o+,K9o+,QTo+,JTo'),
            'SB': expand_range('55+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KTo+'),
        },
        '3bet_vs': {
            'UTG': expand_range('QQ+,AKs,AKo'),
            'MP': expand_range('QQ+,AKs,AKo'),
            'CO': expand_range('JJ+,AQs+,AKo'),
            'BTN': expand_range('TT+,AQs+,AKo'),
        },
        '3bet_bluff': expand_range('A5s-A4s,K9s-K8s'),
        'call_open_ip': expand_range('JJ-66,AJs-ATs,KQs-KJs,QJs,JTs,T9s,98s,87s'),
        'bb_defend': expand_range('99-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,54s,A9o+,KJo,QJo,JTo'),
        'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
        '4bet': expand_range('KK+,AKs'),
    },
    # OPTIMAL_STATS: GTO-inspired strategy targeting winning player stats
    # VPIP 21%, PFR 18%, Gap 3%, 3-bet 8%, 4-bet 25%, AF 2.5, C-bet 70%
    'optimal_stats': {
        'name': 'Optimal Stats',
        'open': {
            'UTG': expand_range('77+,ATs+,KQs,AJo+'),
            'MP': expand_range('66+,A9s+,A5s-A3s,KJs+,QJs,JTs,AJo+,KQo'),
            'CO': expand_range('44+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,76s,ATo+,KJo+,QJo'),
            'BTN': expand_range('22+,A2s+,K5s+,Q7s+,J7s+,T6s+,95s+,85s+,74s+,64s+,54s,A7o+,K9o+,QTo+,JTo'),
            'SB': expand_range('33+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,A8o+,KTo+,QJo'),
        },
        # VERY wide 3-bet ranges (target 8% overall) - 3-bet vs ALL positions
        '3bet_vs': {
            'UTG': expand_range('99+,AQs+,AKo,AJs'),
            'MP': expand_range('88+,AJs+,AKo,AQo,KQs,QJs'),
            'CO': expand_range('77+,ATs+,AJo+,KQs,KJs,QJs,JTs'),
            'BTN': expand_range('66+,A9s+,ATo+,KJs+,KQo,QJs,JTs,T9s'),
        },
        # Wide 3-bet bluffs vs late position (always 3-bet these)
        '3bet_bluff': expand_range('A5s-A2s,K9s-K5s,Q9s-Q7s,J9s-J7s,T9s-T7s,98s-97s,87s-86s,76s-75s,65s,54s'),
        # Minimal calling - prefer 3-bet or fold (low gap)
        'call_open_ip': expand_range('TT-77,AQs-ATs,KQs-KJs,QJs,JTs'),
        # BB defend 40%
        'bb_defend': expand_range('99-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A9o+,KJo,QJo'),
        # Wider call 3-bet
        'call_3bet': expand_range('QQ,JJ,TT,99,AKo,AQs,AQo,AJs,KQs'),
        # Wide 4-bet (target 25% of opens facing 3-bet)
        '4bet': expand_range('KK+,AKs,AKo,AQs,AQo'),
        # Flag to always 3-bet bluff (not 40%)
        '3bet_bluff_always': True,
    },
}

# Player archetypes - CALIBRATED TO REAL 2NL DATA (1036 hands, 122 opponents)
# Real data: FISH 55%, NIT 23%, TAG 12%, LAG 7%, MANIAC 3%

# FISH: VPIP 25.5%, PFR 14.6%, Limp 1.4%, AF 1.14
# Loose passive - plays many hands, rarely raises, calls a lot postflop
STRATEGIES['fish'] = {
    'name': 'Fish',
    'open': {
        # Even wider ranges to hit 25% VPIP
        'UTG': expand_range('55+,A6s+,K9s+,Q9s+,J9s+,T9s,98s,A9o+,KJo+,QJo'),
        'MP': expand_range('44+,A4s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,A7o+,KTo+,QTo+,JTo'),
        'CO': expand_range('33+,A2s+,K5s+,Q6s+,J7s+,T7s+,96s+,85s+,74s+,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
        'BTN': expand_range('22+,A2s+,K3s+,Q5s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A3o+,K8o+,Q9o+,J9o+,T9o,98o'),
        'SB': expand_range('33+,A3s+,K6s+,Q7s+,J7s+,T7s+,96s+,86s+,76s,65s,A5o+,K9o+,QTo+,JTo'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs'), 'MP': expand_range('QQ+,AKs'), 'CO': expand_range('QQ+,AKs'), 'BTN': expand_range('QQ+,AKs')},
    '3bet_bluff': set(),
    'call_open_ip': expand_range('22+,A2s+,K5s+,Q7s+,J8s+,T8s+,97s+,87s,76s,65s,A5o+,K9o+,QTo+,JTo'),
    'bb_defend': expand_range('22+,A2s+,K5s+,Q7s+,J8s+,T8s+,97s+,87s,76s,65s,A5o+,K9o+,QTo+,JTo,T9o'),
    'call_3bet': expand_range('QQ,JJ,TT,AKs,AKo,AQs,AQo,AJs,KQs'),
    '4bet': expand_range('AA,KK'),
    'call_wide': True,
    'limp_pct': 0.06,  # 1.4% of total actions = ~6% of opens
}

# NIT: VPIP 10.7%, PFR 7.5%, AF 1.32
# Very tight - only plays premium hands
STRATEGIES['nit'] = {
    'name': 'Nit',
    'open': {
        # Wider ranges to hit 10.7% VPIP
        'UTG': expand_range('88+,AJs+,KQs,AQo+'),
        'MP': expand_range('77+,ATs+,KJs+,QJs,AJo+,KQo'),
        'CO': expand_range('66+,A9s+,KTs+,QTs+,JTs,ATo+,KJo+,QJo'),
        'BTN': expand_range('55+,A7s+,K9s+,Q9s+,J9s+,T9s,98s,A9o+,KTo+,QJo'),
        'SB': expand_range('66+,A8s+,KTs+,QTs+,JTs,ATo+,KJo+'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs'), 'MP': expand_range('QQ+,AKs'), 'CO': expand_range('QQ+,AKs,AKo'), 'BTN': expand_range('QQ+,AKs,AKo')},
    '3bet_bluff': set(),
    'call_open_ip': expand_range('JJ-66,AQs-ATs,KQs,KJs'),
    'bb_defend': expand_range('TT-44,AQs-A8s,KQs,KJs,QJs,JTs'),
    'call_3bet': expand_range('QQ,AKs'),
    '4bet': expand_range('KK+'),
    'fold_wide': True,
}

# TAG: VPIP 20.2%, PFR 14.7%, AF 4.79
# Tight aggressive - selective but aggressive when playing
STRATEGIES['tag'] = {
    'name': 'TAG',
    'open': {
        # Wider ranges to hit 20% VPIP
        'UTG': expand_range('55+,A8s+,K9s+,Q9s+,J9s+,T9s,ATo+,KJo+,QJo'),
        'MP': expand_range('44+,A6s+,K8s+,Q8s+,J8s+,T8s+,97s+,87s,76s,A9o+,KTo+,QTo+,JTo'),
        'CO': expand_range('33+,A4s+,K6s+,Q7s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A7o+,K9o+,QTo+,JTo,T9o'),
        'BTN': expand_range('22+,A2s+,K4s+,Q6s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A5o+,K8o+,Q9o+,J9o+,T9o,98o'),
        'SB': expand_range('33+,A3s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,A7o+,K9o+,QTo+,JTo'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo'), 'MP': expand_range('QQ+,AKs,AKo'), 'CO': expand_range('JJ+,AQs+,AKo'), 'BTN': expand_range('TT+,AQs+,AKo')},
    '3bet_bluff': expand_range('A5s-A4s'),
    'call_open_ip': expand_range('JJ-44,AQs-A9s,KQs-KTs,QJs,JTs,T9s,98s'),
    'bb_defend': expand_range('TT-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A9o+,KJo,QJo'),
    'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
    '4bet': expand_range('KK+,AKs'),
}

# LAG: VPIP 28.7%, PFR 23.5%, AF 6.75
# Loose aggressive - plays many hands aggressively
STRATEGIES['lag'] = {
    'name': 'LAG',
    'open': {
        # Wider ranges to hit 28.7% VPIP
        'UTG': expand_range('44+,A5s+,K8s+,Q9s+,J9s+,T8s+,97s+,87s,76s,A8o+,KTo+,QJo'),
        'MP': expand_range('33+,A3s+,K6s+,Q7s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A6o+,K9o+,QTo+,JTo,T9o'),
        'CO': expand_range('22+,A2s+,K4s+,Q5s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A4o+,K8o+,Q9o+,J9o+,T9o,98o'),
        'BTN': expand_range('22+,A2s+,K2s+,Q3s+,J5s+,T5s+,94s+,83s+,73s+,62s+,52s+,42s+,A2o+,K6o+,Q8o+,J8o+,T8o+,98o,87o'),
        'SB': expand_range('22+,A2s+,K4s+,Q6s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A4o+,K8o+,Q9o+,J9o+,T9o'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo,JJ'), 'MP': expand_range('JJ+,AKs,AKo,AQs,TT'), 'CO': expand_range('TT+,AQs+,AKo,AJs'), 'BTN': expand_range('TT+,AQs+,AKo,AJs,KQs')},
    '3bet_bluff': expand_range('A5s-A2s,K9s-K7s,Q9s,J9s,T9s,98s,87s,76s'),
    'call_open_ip': expand_range('TT-22,AJs-A7s,KQs-KTs,QJs-QTs,JTs,T9s,98s,87s,76s'),
    'bb_defend': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,54s,A7o+,KTo+,QTo+,JTo,T9o'),
    'call_3bet': expand_range('JJ,TT,AKo,AQs,AQo,KQs'),
    '4bet': expand_range('QQ+,AKs'),
}

# MANIAC: VPIP 48.6%, PFR 39.2%, AF 7.00
# Very aggressive - plays almost half of hands, bets relentlessly
STRATEGIES['maniac'] = {
    'name': 'Maniac',
    'open': {
        # Very wide ranges to hit 48.6% VPIP
        'UTG': expand_range('33+,A3s+,K6s+,Q7s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
        'MP': expand_range('22+,A2s+,K4s+,Q5s+,J6s+,T6s+,95s+,84s+,74s+,63s+,53s+,43s,A3o+,K7o+,Q9o+,J9o+,T9o,98o'),
        'CO': expand_range('22+,A2s+,K2s+,Q3s+,J4s+,T5s+,94s+,83s+,73s+,62s+,52s+,42s+,A2o+,K5o+,Q8o+,J8o+,T8o+,98o,87o'),
        'BTN': expand_range('22+,A2s+,K2s+,Q2s+,J3s+,T4s+,93s+,82s+,72s+,62s+,52s+,42s+,32s,A2o+,K3o+,Q6o+,J7o+,T7o+,97o+,87o,76o'),
        'SB': expand_range('22+,A2s+,K2s+,Q4s+,J5s+,T5s+,94s+,83s+,73s+,62s+,52s+,42s+,A2o+,K5o+,Q8o+,J8o+,T8o+,98o,87o'),
    },
    '3bet_vs': {'UTG': expand_range('TT+,AQs+,AKo,AJs,KQs'), 'MP': expand_range('99+,AJs+,AKo,AQo,KQs,QJs'), 'CO': expand_range('88+,ATs+,AJo+,KQs,KJs,QJs,JTs'), 'BTN': expand_range('77+,A9s+,ATo+,KJs+,KQo,QJs,JTs,T9s')},
    '3bet_bluff': expand_range('A5s-A2s,K9s-K6s,Q9s-Q8s,J9s,T9s,98s,87s,76s,65s,54s'),
    'call_open_ip': expand_range('TT-22,AJs-A5s,KQs-K9s,QJs-Q9s,JTs-J9s,T9s,98s,97s,87s,76s,AQo,AJo,ATo,KQo,KJo,QJo'),
    'sb_defend': expand_range('TT-22,AJs-A2s,KQs-K8s,QJs-Q9s,JTs-J9s,T9s-T8s,98s,87s,76s,A5o+,KQo,KJo,QJo'),
    'bb_defend': expand_range('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
    'call_3bet': expand_range('JJ,TT,99,AKo,AQs,AQo,AJs,KQs'),
    '4bet': expand_range('QQ+,AKs,AKo'),
    'overbet': True,  # Flag for postflop overbetting
}

# value_lord: disciplined value betting with paired board awareness
STRATEGIES['value_lord'] = STRATEGIES['maniac'].copy()
STRATEGIES['value_lord']['name'] = 'Value Lord'

# the_lord: opponent-aware strategy based on villain archetypes
STRATEGIES['the_lord'] = STRATEGIES['value_lord'].copy()
STRATEGIES['the_lord']['name'] = 'The Lord'

# Archetype-specific preflop ranges for calling vs their raise
# Based on advice: fish=wider, nit/rock=tighter, maniac=QQ+/AK, lag=99+/AQ+, tag=TT+/AK
THE_LORD_VS_RAISE = {
    'fish': expand_range('77+,A9s+,KTs+,QTs+,AJo+,KQo'),  # Wider - they raise weak
    'nit': expand_range('QQ+,AKs'),  # Much tighter - they only raise premiums
    'rock': expand_range('QQ+,AKs'),  # Same as nit
    'maniac': expand_range('QQ+,AKs,AKo'),  # Only premiums - they raise everything
    'lag': expand_range('99+,AQs+,AQo+'),  # Tighter - they raise wide but have hands
    'tag': expand_range('TT+,AKs,AKo'),  # Baseline - respect their raises
    'unknown': expand_range('TT+,AKs,AKo'),  # Default to TAG
}




def preflop_action(hand: str, position: str, strategy: Dict, 
                   facing: str, opener_pos: str = None) -> Tuple[str, str]:
    """
    Preflop decision based on strategy.
    facing: 'none', 'open', '3bet', '4bet'
    Returns (action, reasoning).
    """
    if position not in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
        position = 'BTN'
    
    # RFI
    if facing == 'none':
        if position == 'BB':
            return ('check', 'BB checks')
        open_range = strategy['open'].get(position, set())
        if hand in open_range:
            return ('raise', f'{hand} in {position} open range')
        return ('fold', f'{hand} not in {position} open range')
    
    # Facing open
    if facing == 'open':
        # 3-bet value
        three_bet_range = strategy.get('3bet_vs', {}).get(opener_pos, set())
        if hand in three_bet_range:
            return ('raise', f'{hand} 3-bet vs {opener_pos}')
        
        # 3-bet bluff (always or 40% depending on strategy)
        if opener_pos in ['CO', 'BTN'] and hand in strategy.get('3bet_bluff', set()):
            if strategy.get('3bet_bluff_always') or random.random() < 0.4:
                return ('raise', f'{hand} 3-bet bluff vs {opener_pos}')
        
        # SB defend - 3bet or call strong hands (SB is OOP so tighter than BB)
        if position == 'SB':
            sb_defend = strategy.get('sb_defend', strategy.get('call_open_ip', set()))
            if hand in sb_defend:
                return ('call', f'{hand} SB defend')
        
        # Call IP (CO, BTN) or BB defend
        if position in ['CO', 'BTN', 'BB']:
            if position == 'BB' and hand in strategy.get('bb_defend', set()):
                return ('call', f'{hand} BB defend')
            if hand in strategy.get('call_open_ip', set()):
                return ('call', f'{hand} call IP')
            # Fish calls wide
            if strategy.get('call_wide') and hand in strategy.get('bb_defend', set()):
                return ('call', f'{hand} call wide')
        
        return ('fold', f'{hand} fold vs open')
    
    # Facing 3-bet
    if facing == '3bet':
        if hand in strategy.get('4bet', set()):
            return ('raise', f'{hand} 4-bet')
        if hand in strategy.get('call_3bet', set()):
            return ('call', f'{hand} call 3-bet')
        if strategy.get('fold_wide'):
            return ('fold', f'{hand} nit folds to 3-bet')
        return ('fold', f'{hand} fold to 3-bet')
    
    # Facing 4-bet
    if facing == '4bet':
        if hand in expand_range('KK+'):
            return ('raise', f'{hand} 5-bet jam')
        if hand in expand_range('QQ,AKs'):
            return ('call', f'{hand} call 4-bet')
        return ('fold', f'{hand} fold to 4-bet')
    
    return ('fold', 'default fold')
