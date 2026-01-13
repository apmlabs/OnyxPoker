"""
Shared poker logic for both poker_sim.py and strategy_engine.py.
Contains hand evaluation, postflop decisions, and strategy definitions.
"""

from typing import Dict, List, Set, Tuple, Optional
import random

# Card constants
RANKS = '23456789TJQKA'
SUITS = 'shdc'
RANK_VAL = {r: i for i, r in enumerate(RANKS)}

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
        'bb_defend': expand_range('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
        'call_3bet': expand_range('JJ,TT,99,AKo,AQs,AQo,AJs,KQs'),
        '4bet': expand_range('QQ+,AKs,AKo'),
        'overbet': True,
    },
}

# Player archetypes
STRATEGIES['fish'] = {
    'name': 'Fish',
    'open': {
        'UTG': expand_range('88+,ATs+,KQs,AJo+'),
        'MP': expand_range('77+,A9s+,KJs+,QJs,ATo+,KQo'),
        'CO': expand_range('66+,A7s+,KTs+,QTs+,JTs,ATo+,KJo+'),
        'BTN': expand_range('55+,A5s+,K9s+,Q9s+,J9s+,T9s,98s,A9o+,KTo+,QJo'),
        'SB': expand_range('66+,A7s+,K9s+,Q9s+,JTs,A9o+,KJo+'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs'), 'MP': expand_range('QQ+,AKs'), 'CO': expand_range('QQ+,AKs'), 'BTN': expand_range('QQ+,AKs')},
    '3bet_bluff': set(),
    'call_open_ip': expand_range('22+,A2s+,K5s+,Q7s+,J8s+,T8s+,97s+,87s,76s,65s,A5o+,K9o+,QTo+,JTo'),
    'bb_defend': expand_range('22+,A2s+,K5s+,Q7s+,J8s+,T8s+,97s+,87s,76s,65s,A5o+,K9o+,QTo+,JTo,T9o'),
    'call_3bet': expand_range('QQ,JJ,TT,AKs,AKo,AQs,AQo,AJs,KQs'),
    '4bet': expand_range('AA,KK'),
    'call_wide': True,
}

STRATEGIES['nit'] = {
    'name': 'Nit',
    'open': {
        'UTG': expand_range('TT+,AQs+,AKo'),
        'MP': expand_range('99+,AJs+,KQs,AQo+'),
        'CO': expand_range('88+,ATs+,KQs,AJo+,KQo'),
        'BTN': expand_range('77+,A9s+,KJs+,QJs,ATo+,KJo+'),
        'SB': expand_range('88+,ATs+,KQs,AJo+'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs'), 'MP': expand_range('QQ+,AKs'), 'CO': expand_range('QQ+,AKs,AKo'), 'BTN': expand_range('QQ+,AKs,AKo')},
    '3bet_bluff': set(),
    'call_open_ip': expand_range('JJ-88,AQs-AJs,KQs'),
    'bb_defend': expand_range('TT-66,AQs-ATs,KQs,QJs,JTs'),
    'call_3bet': expand_range('QQ,AKs'),
    '4bet': expand_range('KK+'),
    'fold_wide': True,
}

STRATEGIES['lag'] = {
    'name': 'LAG',
    'open': {
        'UTG': expand_range('66+,A9s+,A5s-A2s,KTs+,QTs+,JTs,ATo+,KQo'),
        'MP': expand_range('55+,A7s+,A5s-A2s,K9s+,Q9s+,J9s+,T9s,98s,ATo+,KJo+,QJo'),
        'CO': expand_range('33+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,54s,A8o+,KTo+,QTo+,JTo'),
        'BTN': expand_range('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,96s+,85s+,74s+,64s+,53s+,A5o+,K8o+,Q9o+,J9o+,T9o'),
        'SB': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,A7o+,K9o+,QTo+'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo,JJ'), 'MP': expand_range('JJ+,AKs,AKo,AQs,TT'), 'CO': expand_range('TT+,AQs+,AKo,AJs'), 'BTN': expand_range('TT+,AQs+,AKo,AJs,KQs')},
    '3bet_bluff': expand_range('A5s-A2s,K9s-K7s,Q9s,J9s,T9s,98s,87s,76s'),
    'call_open_ip': expand_range('TT-22,AJs-A7s,KQs-KTs,QJs-QTs,JTs,T9s,98s,87s,76s'),
    'bb_defend': expand_range('22+,A2s+,K6s+,Q8s+,J8s+,T8s+,97s+,86s+,76s,65s,54s,A7o+,KTo+,QTo+,JTo,T9o'),
    'call_3bet': expand_range('JJ,TT,AKo,AQs,AQo,KQs'),
    '4bet': expand_range('QQ+,AKs'),
}

STRATEGIES['tag'] = {
    'name': 'TAG',
    'open': {
        'UTG': expand_range('77+,ATs+,KQs,AQo+'),
        'MP': expand_range('66+,A9s+,KJs+,QJs,JTs,AJo+,KQo'),
        'CO': expand_range('55+,A7s+,K9s+,Q9s+,J9s+,T9s,98s,ATo+,KJo+,QJo'),
        'BTN': expand_range('22+,A2s+,K8s+,Q9s+,J9s+,T8s+,97s+,87s,76s,65s,A9o+,KTo+,QJo'),
        'SB': expand_range('55+,A5s+,K9s+,Q9s+,J9s+,T8s+,98s,87s,A9o+,KJo+'),
    },
    '3bet_vs': {'UTG': expand_range('QQ+,AKs,AKo'), 'MP': expand_range('QQ+,AKs,AKo'), 'CO': expand_range('JJ+,AQs+,AKo'), 'BTN': expand_range('TT+,AQs+,AKo')},
    '3bet_bluff': expand_range('A5s-A4s'),
    'call_open_ip': expand_range('JJ-55,AQs-ATs,KQs-KJs,QJs,JTs,T9s,98s'),
    'bb_defend': expand_range('TT-22,AJs-A2s,KTs+,Q9s+,J9s+,T8s+,97s+,86s+,76s,65s,A9o+,KJo,QJo'),
    'call_3bet': expand_range('QQ,JJ,AKo,AQs'),
    '4bet': expand_range('KK+,AKs'),
}

# MANIAC: Very aggressive, 3-bets wide, overbets postflop (based on real 2NL data)
STRATEGIES['maniac'] = {
    'name': 'Maniac',
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
    'bb_defend': expand_range('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,96s+,85s+,75s,64s+,54s,A5o+,K9o+,QTo+,JTo,T9o'),
    'call_3bet': expand_range('JJ,TT,99,AKo,AQs,AQo,AJs,KQs'),
    '4bet': expand_range('QQ+,AKs,AKo'),
    'overbet': True,  # Flag for postflop overbetting
}


# Hand evaluation
def hand_to_str(cards: List[Tuple[str, str]]) -> str:
    """Convert 2 card tuples to hand notation like 'AKs' or 'AKo'."""
    c1, c2 = sorted(cards, key=lambda x: RANK_VAL[x[0]], reverse=True)
    r1, s1 = c1
    r2, s2 = c2
    if r1 == r2:
        return r1 + r2
    elif s1 == s2:
        return r1 + r2 + 's'
    else:
        return r1 + r2 + 'o'


def parse_card(card: str) -> Tuple[str, str]:
    """Parse card string like 'As' to ('A', 's')."""
    if not card or len(card) < 2:
        return (None, None)
    rank = card[:-1].upper()
    suit = card[-1].lower()
    if rank == '10':
        rank = 'T'
    return (rank, suit)


def evaluate_hand(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]]) -> Tuple[int, str, int]:
    """
    Evaluate 5-7 card hand. Returns (rank, description, kicker_value).
    Rank: 9=straight flush, 8=quads, 7=full house, 6=flush, 5=straight,
          4=trips/set, 3=two pair, 2=pair, 1=high card
    """
    all_cards = hole_cards + board
    if len(all_cards) < 5:
        return (0, "incomplete", 0)
    
    ranks = [c[0] for c in all_cards]
    suits = [c[1] for c in all_cards]
    hero_ranks = set(c[0] for c in hole_cards)
    
    rank_counts = {}
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1
    
    suit_counts = {}
    for s in suits:
        suit_counts[s] = suit_counts.get(s, 0) + 1
    
    # Check flush
    flush_suit = None
    for s, count in suit_counts.items():
        if count >= 5:
            flush_suit = s
    
    # Check straight
    rank_set = set(RANK_VAL[r] for r in ranks)
    if 12 in rank_set:
        rank_set.add(-1)
    
    straight_high = None
    for i in range(8, -2, -1):
        if all(j in rank_set for j in range(i, i+5)):
            straight_high = i + 4
            break
    
    # Straight flush
    if flush_suit and straight_high is not None:
        flush_ranks = set(RANK_VAL[c[0]] for c in all_cards if c[1] == flush_suit)
        if 12 in flush_ranks:
            flush_ranks.add(-1)
        for i in range(8, -2, -1):
            if all(j in flush_ranks for j in range(i, i+5)):
                return (9, "straight flush", i+4)
    
    # Four of a kind
    for r, count in rank_counts.items():
        if count >= 4:
            return (8, f"quads {r}s", RANK_VAL[r])
    
    # Full house
    trips = [r for r, c in rank_counts.items() if c >= 3]
    pairs = [r for r, c in rank_counts.items() if c >= 2]
    if trips and len(pairs) >= 2:
        return (7, "full house", RANK_VAL[trips[0]])
    
    # Flush
    if flush_suit:
        flush_cards = sorted([RANK_VAL[c[0]] for c in all_cards if c[1] == flush_suit], reverse=True)
        return (6, "flush", flush_cards[0])
    
    # Straight
    if straight_high is not None:
        return (5, "straight", straight_high)
    
    # Three of a kind
    if trips:
        is_set = trips[0] in hero_ranks and len(hero_ranks) == 1
        return (4, f"set of {trips[0]}s" if is_set else f"trips {trips[0]}s", RANK_VAL[trips[0]])
    
    # Two pair
    pair_ranks = sorted([r for r, c in rank_counts.items() if c >= 2], key=lambda r: RANK_VAL[r], reverse=True)
    if len(pair_ranks) >= 2:
        return (3, "two pair", RANK_VAL[pair_ranks[0]])
    
    # One pair
    if pair_ranks:
        pr = pair_ranks[0]
        board_ranks = [c[0] for c in board] if board else []
        board_vals = sorted([RANK_VAL[r] for r in board_ranks], reverse=True)
        hero_vals = [RANK_VAL[r] for r in hero_ranks]
        
        # Check for pocket pair (both hole cards same rank)
        is_pocket_pair = len(hole_cards) == 2 and hole_cards[0][0] == hole_cards[1][0]
        
        if pr in hero_ranks:
            # OVERPAIR: Pocket pair higher than all board cards
            if is_pocket_pair and board_vals and RANK_VAL[pr] > board_vals[0]:
                return (2, f"overpair {pr}{pr}", RANK_VAL[pr] * 100 + RANK_VAL[pr])
            
            # UNDERPAIR TO ACE: Big pocket pair (TT+) but ace on board
            if is_pocket_pair and board_vals and any(v == RANK_VAL['A'] for v in board_vals):
                if RANK_VAL[pr] >= RANK_VAL['T'] and RANK_VAL[pr] < RANK_VAL['A']:
                    return (2, f"underpair {pr}{pr} (ace on board)", RANK_VAL[pr] * 100 + RANK_VAL[pr])
            
            # TOP PAIR
            if board_vals and RANK_VAL[pr] >= board_vals[0]:
                kicker = max(RANK_VAL[r] for r in hero_ranks if r != pr) if len(hero_ranks) > 1 else 0
                if kicker >= RANK_VAL['T']:
                    return (2, "top pair good kicker", RANK_VAL[pr] * 100 + kicker)
                return (2, "top pair weak kicker", RANK_VAL[pr] * 100 + kicker)
            
            # MIDDLE PAIR
            elif board_vals and len(board_vals) > 1 and RANK_VAL[pr] >= board_vals[1]:
                return (2, "middle pair", RANK_VAL[pr])
            
            # BOTTOM PAIR / UNDERPAIR
            return (2, "bottom pair", RANK_VAL[pr])
        return (2, "pair", RANK_VAL[pr])
    
    # High card
    high = max(RANK_VAL[r] for r in ranks)
    return (1, "high card", high)


def check_draws(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]]) -> List[str]:
    """Check for flush and straight draws."""
    draws = []
    if len(board) < 3:
        return draws
    
    all_cards = hole_cards + board
    suits = [c[1] for c in all_cards]
    
    suit_counts = {}
    for s in suits:
        suit_counts[s] = suit_counts.get(s, 0) + 1
    
    for s, count in suit_counts.items():
        if count == 4:
            draws.append("flush_draw")
            break
    
    ranks = set(RANK_VAL[c[0]] for c in all_cards)
    if 12 in ranks:
        ranks.add(-1)
    
    for i in range(-1, 10):
        window = set(range(i, i+5))
        in_window = len(window & ranks)
        if in_window == 4:
            missing = window - ranks
            if missing:
                m = list(missing)[0]
                if m == i or m == i+4:
                    draws.append("oesd")
                else:
                    draws.append("gutshot")
            break
    
    return draws


# Postflop decision logic - matches strategy files exactly
def postflop_action(hole_cards: List[Tuple[str, str]], board: List[Tuple[str, str]], 
                    pot: float, to_call: float, street: str, is_ip: bool,
                    is_aggressor: bool, archetype: str = None, strategy: str = None,
                    num_opponents: int = 1) -> Tuple[str, float, str]:
    """
    Postflop decision based on strategy file rules.
    Returns (action, bet_size, reasoning).
    archetype: 'fish', 'nit', 'tag', 'lag' for special behavior
    strategy: 'gpt3', 'gpt4', 'sonnet', 'kiro_optimal' for bot-specific logic
    num_opponents: number of active opponents (1=heads-up, 2+=multiway)
    """
    strength, desc, kicker = evaluate_hand(hole_cards, board)
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
    
    # FISH: Calls with any pair/draw, never folds top pair, stations
    if archetype == 'fish':
        if to_call == 0 or to_call is None:
            if strength >= 3:
                return ('bet', round(pot * 0.5, 2), f"{desc} - fish bets small")
            return ('check', 0, "fish checks")
        else:
            if has_pair or has_any_draw:
                return ('call', 0, f"{desc} - fish calls")
            return ('fold', 0, "fish folds air")
    
    # NIT: Only continues top pair+, folds to aggression, never bluffs
    if archetype == 'nit':
        if to_call == 0 or to_call is None:
            if strength >= 4:
                return ('bet', round(pot * 0.65, 2), f"{desc} - nit value bets")
            if strength == 3 or "top pair" in desc:
                return ('bet', round(pot * 0.5, 2), f"{desc} - nit bets")
            return ('check', 0, "nit checks weak hand")
        else:
            if strength >= 4:
                return ('call', 0, f"{desc} - nit calls")
            if strength == 3 and street == 'flop':
                return ('call', 0, f"{desc} - nit calls flop")
            if "top pair good kicker" in desc and street == 'flop':
                return ('call', 0, f"{desc} - nit calls flop")
            return ('fold', 0, f"{desc} - nit folds to aggression")
    
    # TAG: C-bets 65%, gives up without equity, folds to raises
    if archetype == 'tag':
        if to_call == 0 or to_call is None:
            if strength >= 3:
                return ('bet', round(pot * 0.65, 2), f"{desc} - tag value bets")
            if "top pair" in desc or "pair" in desc:
                if street == 'flop' and random.random() < 0.65:
                    return ('bet', round(pot * 0.5, 2), f"{desc} - tag c-bets")
                if street == 'turn' and strength >= 2 and "top" in desc:
                    return ('bet', round(pot * 0.55, 2), f"{desc} - tag barrels")
            if combo_draw and street == 'flop':
                return ('bet', round(pot * 0.5, 2), "tag semi-bluffs draw")
            return ('check', 0, f"{desc} - tag checks")
        else:
            if strength >= 4:
                return ('call', 0, f"{desc} - tag calls")
            if strength == 3 and street != 'river':
                return ('call', 0, f"{desc} - tag calls")
            if "top pair" in desc and street == 'flop':
                return ('call', 0, f"{desc} - tag calls flop")
            return ('fold', 0, f"{desc} - tag folds")
    
    # LAG: C-bets 75%, double barrels, bluffs rivers
    if archetype == 'lag':
        if to_call == 0 or to_call is None:
            if strength >= 3:
                return ('bet', round(pot * 0.75, 2), f"{desc} - lag value bets big")
            if "pair" in desc:
                if street in ['flop', 'turn'] and random.random() < 0.75:
                    return ('bet', round(pot * 0.6, 2), f"{desc} - lag barrels")
            if has_any_draw:
                return ('bet', round(pot * 0.65, 2), "lag semi-bluffs")
            if street == 'flop' and random.random() < 0.70:
                return ('bet', round(pot * 0.5, 2), "lag c-bets air")
            if street == 'river' and random.random() < 0.25:
                return ('bet', round(pot * 0.6, 2), "lag river bluff")
            return ('check', 0, f"{desc} - lag checks")
        else:
            if strength >= 3:
                return ('call', 0, f"{desc} - lag calls")
            if "pair" in desc and street != 'river':
                return ('call', 0, f"{desc} - lag floats")
            if has_flush_draw or has_oesd:
                return ('call', 0, "lag calls with draw")
            return ('fold', 0, f"{desc} - lag folds")
    
    # MANIAC: Overbets (100-150% pot), 3-barrels wide, rarely folds
    if archetype == 'maniac':
        if to_call == 0 or to_call is None:
            if strength >= 4:
                # Overbet value hands
                return ('bet', round(pot * 1.25, 2), f"{desc} - maniac overbets value")
            if strength >= 3:
                return ('bet', round(pot * 1.1, 2), f"{desc} - maniac bets big")
            if "pair" in desc:
                if street in ['flop', 'turn'] and random.random() < 0.85:
                    return ('bet', round(pot * 1.0, 2), f"{desc} - maniac overbets")
                if street == 'river' and random.random() < 0.5:
                    return ('bet', round(pot * 1.2, 2), f"{desc} - maniac river overbet")
            if has_any_draw:
                return ('bet', round(pot * 1.0, 2), "maniac overbets draw")
            if street == 'flop' and random.random() < 0.80:
                return ('bet', round(pot * 0.9, 2), "maniac c-bets big")
            if street == 'turn' and random.random() < 0.60:
                return ('bet', round(pot * 1.0, 2), "maniac barrels turn")
            if street == 'river' and random.random() < 0.35:
                return ('bet', round(pot * 1.1, 2), "maniac river bluff")
            return ('check', 0, f"{desc} - maniac checks")
        else:
            # Maniac calls wide, rarely folds
            if strength >= 3:
                return ('call', 0, f"{desc} - maniac calls")
            if "pair" in desc:
                return ('call', 0, f"{desc} - maniac calls any pair")
            if has_any_draw:
                return ('call', 0, "maniac calls with draw")
            if street == 'flop' and random.random() < 0.5:
                return ('call', 0, "maniac floats flop")
            return ('fold', 0, f"{desc} - maniac folds")
    
    # BOT STRATEGIES - strategy-specific postflop logic
    # gpt3/gpt4: Board texture aware, smaller c-bets, 3-bet pot adjustments
    # sonnet/kiro_optimal: Bigger value bets, overpair logic
    # value_max: Maniac-style big bets but smarter (doesn't bluff as much)
    
    if strategy == 'value_max':
        return _postflop_value_max(hole_cards, board, pot, to_call, street, is_ip,
                                   is_aggressor, strength, desc, draws, combo_draw,
                                   has_flush_draw, has_oesd, has_any_draw)
    
    if strategy in ['gpt3', 'gpt4']:
        return _postflop_gpt(hole_cards, board, pot, to_call, street, is_ip, 
                            is_aggressor, strength, desc, draws, combo_draw,
                            has_flush_draw, has_oesd, has_gutshot, is_overpair,
                            is_underpair_to_ace, is_multiway)
    
    if strategy in ['sonnet', 'kiro_optimal']:
        return _postflop_sonnet(hole_cards, board, pot, to_call, street, is_ip,
                               is_aggressor, strength, desc, draws, combo_draw,
                               has_flush_draw, has_oesd, is_overpair, board_has_ace,
                               is_underpair_to_ace, is_multiway)
    
    # DEFAULT fallback (same as sonnet)
    return _postflop_sonnet(hole_cards, board, pot, to_call, street, is_ip,
                           is_aggressor, strength, desc, draws, combo_draw,
                           has_flush_draw, has_oesd, is_overpair, board_has_ace,
                           is_underpair_to_ace, is_multiway)


def _postflop_value_max(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                        strength, desc, draws, combo_draw, has_flush_draw, has_oesd, has_any_draw):
    """
    VALUE_MAX: Smart postflop based on hand strength vs board.
    Key principles:
    - Strong hands (sets+): bet big for value
    - Medium hands (top pair): bet/call based on board texture
    - Weak hands: check/fold, don't waste money
    - Draws: semi-bluff with good equity, fold without odds
    """
    # Calculate pot odds when facing bet
    if to_call and to_call > 0:
        pot_odds = to_call / (pot + to_call)  # e.g., call 10 into 30 = 25%
    else:
        pot_odds = 0
    
    # Board texture analysis
    board_ranks = sorted([RANK_VAL[c[0]] for c in board], reverse=True) if board else []
    board_suits = [c[1] for c in board] if board else []
    is_paired_board = len(board_ranks) != len(set(board_ranks))
    is_monotone = len(set(board_suits)) == 1 if len(board_suits) >= 3 else False
    is_two_tone = len(set(board_suits)) == 2 if len(board_suits) >= 3 else False
    has_straight_possible = (max(board_ranks) - min(board_ranks) <= 4) if len(board_ranks) >= 3 else False
    
    # Determine if we likely have best hand
    is_vulnerable = is_two_tone or has_straight_possible
    is_scary_board = is_monotone or is_paired_board or (board_ranks and board_ranks[0] >= RANK_VAL['Q'])
    
    if to_call == 0 or to_call is None:
        # === BETTING (checked to us) ===
        
        # MONSTERS - always bet big
        if strength >= 5:  # Straights+
            return ('bet', round(pot * 1.0, 2), f"{desc} - bet for value")
        
        # STRONG - bet for value, protect on wet boards
        if strength >= 4:  # Sets, two pair
            size = 0.9 if is_vulnerable else 0.75
            return ('bet', round(pot * size, 2), f"{desc} - value bet")
        
        # TOP PAIR GOOD KICKER - bet 2 streets
        if "top pair good kicker" in desc or "top pair" in desc and strength >= 3:
            if street in ['flop', 'turn']:
                size = 0.7 if is_vulnerable else 0.6
                return ('bet', round(pot * size, 2), f"{desc} - value bet")
            else:  # river - check weak top pair
                if "good kicker" in desc:
                    return ('bet', round(pot * 0.5, 2), f"{desc} - thin value")
                return ('check', 0, f"{desc} - check river")
        
        # OVERPAIR - bet for value
        if "overpair" in desc.lower():
            size = 0.7 if is_vulnerable else 0.6
            return ('bet', round(pot * size, 2), f"{desc} - value bet overpair")
        
        # MEDIUM PAIR (second pair, pocket pair below top) - check/call line
        if "second pair" in desc or "middle pair" in desc:
            return ('check', 0, f"{desc} - check medium strength")
        
        # WEAK PAIR (bottom pair, low pocket pair) - check, don't bet
        if "pair" in desc and strength < 3:
            return ('check', 0, f"{desc} - check weak pair")
        
        # STRONG DRAWS - semi-bluff
        if combo_draw:
            return ('bet', round(pot * 0.7, 2), f"combo draw - semi-bluff")
        if has_flush_draw and street == 'flop':
            return ('bet', round(pot * 0.6, 2), f"flush draw - semi-bluff")
        if has_oesd and street == 'flop':
            return ('bet', round(pot * 0.55, 2), f"OESD - semi-bluff")
        
        # C-BET - only with equity or on dry boards
        if is_aggressor and street == 'flop':
            if not is_scary_board and not is_vulnerable:
                return ('bet', round(pot * 0.33, 2), "c-bet dry board")
            if has_any_draw:
                return ('bet', round(pot * 0.5, 2), "c-bet with equity")
            # Don't c-bet scary boards with air
            return ('check', 0, "check - no equity on scary board")
        
        return ('check', 0, f"{desc} - check")
    
    else:
        # === FACING A BET ===
        
        # MONSTERS - raise for value
        if strength >= 5:
            return ('raise', round(pot * 2.0, 2), f"{desc} - raise for value")
        
        # STRONG - raise or call based on street
        if strength >= 4:
            if street == 'river':
                return ('call', 0, f"{desc} - call river")
            return ('raise', round(pot * 2.0, 2), f"{desc} - raise for value")
        
        # TOP PAIR - call if bet is reasonable
        if "top pair" in desc or strength >= 3:
            if pot_odds <= 0.33:  # Calling up to 50% pot
                return ('call', 0, f"{desc} - call (good odds)")
            if "good kicker" in desc and pot_odds <= 0.4:
                return ('call', 0, f"{desc} - call TPGK")
            return ('fold', 0, f"{desc} - fold (bet too big)")
        
        # OVERPAIR - call reasonable bets
        if "overpair" in desc.lower():
            if pot_odds <= 0.35:
                return ('call', 0, f"{desc} - call overpair")
            return ('fold', 0, f"{desc} - fold overpair to big bet")
        
        # MEDIUM PAIR - only call small bets
        if "pair" in desc:
            if pot_odds <= 0.25:  # Only call up to 33% pot
                return ('call', 0, f"{desc} - call small bet")
            return ('fold', 0, f"{desc} - fold weak pair")
        
        # DRAWS - call with odds
        if has_flush_draw or has_oesd:
            # Flush draw ~35% equity, OESD ~32% equity
            equity = 0.35 if has_flush_draw else 0.32
            if combo_draw:
                equity = 0.45
            if pot_odds <= equity:
                return ('call', 0, f"draw - call (have odds)")
            return ('fold', 0, f"draw - fold (no odds)")
        
        return ('fold', 0, f"{desc} - fold")


def _postflop_gpt(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                  strength, desc, draws, combo_draw, has_flush_draw, has_oesd, has_gutshot,
                  is_overpair=False, is_underpair_to_ace=False, is_multiway=False):
    """
    GPT3/GPT4 postflop: Board texture aware, smaller c-bets on dry boards.
    From strategy file:
    - Dry boards (Axx/Kxx/Qxx): c-bet small 25-35%
    - Wet boards (connected/two-tone): check more, bet with equity
    - 3-bet pots: small c-bet 25-33%
    - TPTK: 2 streets value, 3 vs stations
    - Weak TP: bet once, check-call, fold to pressure
    - Overpair: bet 65-70% pot
    - Underpair to ace: check-call
    - Multiway: reduce c-bets sharply, bet mostly for value + strong draws
    """
    # Check board texture
    board_ranks = sorted([RANK_VAL[c[0]] for c in board], reverse=True)
    board_suits = [c[1] for c in board]
    is_dry = (board_ranks[0] >= RANK_VAL['Q'] and  # High card board
              len(set(board_suits)) >= 2 and  # Not monotone
              (len(board_ranks) < 2 or board_ranks[0] - board_ranks[-1] > 4))  # Not connected
    is_wet = (len(set(board_suits)) <= 2 or  # Two-tone or monotone
              (len(board_ranks) >= 3 and board_ranks[0] - board_ranks[2] <= 4))  # Connected
    
    if to_call == 0 or to_call is None:
        # Multiway: only bet strong value + strong draws
        if is_multiway:
            if strength >= 4:  # Sets+
                return ('bet', round(pot * 0.75, 2), f"{desc} - multiway value")
            if strength == 3:  # Two pair
                return ('bet', round(pot * 0.65, 2), f"{desc} - multiway value")
            if combo_draw:
                return ('bet', round(pot * 0.60, 2), "combo draw - multiway semi-bluff")
            return ('check', 0, f"{desc} - check multiway")
        
        # Heads-up betting logic
        if strength >= 5:  # Nuts
            return ('bet', round(pot * 1.0, 2), f"{desc} - bet 100%")
        if strength == 4:  # Sets
            return ('bet', round(pot * 0.75, 2), f"{desc} - bet 75%")
        if strength == 3:  # Two pair
            return ('bet', round(pot * 0.70, 2), f"{desc} - bet 70%")
        
        # OVERPAIR (QQ on J85) - bet for value
        if is_overpair or "overpair" in desc:
            size = 0.65 if street == 'flop' else (0.60 if street == 'turn' else 0.50)
            return ('bet', round(pot * size, 2), f"{desc} - overpair value bet")
        
        # UNDERPAIR TO ACE (KK on Axx) - check-call
        if is_underpair_to_ace or "underpair" in desc:
            return ('check', 0, f"{desc} - check (ace on board)")
        
        # Top pair - board texture matters
        if "top pair good kicker" in desc:
            if is_dry:
                size = 0.33 if street == 'flop' else 0.50
            else:
                size = 0.55 if street == 'flop' else 0.60
            if street != 'river':
                return ('bet', round(pot * size, 2), f"{desc} - value bet")
            return ('check', 0, f"{desc} - check river")
        
        if "top pair" in desc and street == 'flop':
            size = 0.30 if is_dry else 0.50
            return ('bet', round(pot * size, 2), f"{desc} - c-bet")
        
        # Draws - semi-bluff with equity
        if combo_draw:
            return ('bet', round(pot * 0.65, 2), "combo draw - semi-bluff")
        if has_flush_draw and is_aggressor and street == 'flop':
            return ('bet', round(pot * 0.50, 2), "flush draw - semi-bluff")
        if has_oesd and is_aggressor and street == 'flop':
            return ('bet', round(pot * 0.45, 2), "OESD - semi-bluff")
        
        # C-bet air on dry boards only
        if is_aggressor and street == 'flop' and is_dry and random.random() < 0.55:
            return ('bet', round(pot * 0.30, 2), "c-bet dry board")
        
        return ('check', 0, f"{desc} - check")
    
    # Facing bet
    if strength >= 5:
        return ('call', 0, f"{desc} - call")
    if strength == 4:
        return ('call', 0, f"{desc} - call")
    if strength == 3:
        return ('call', 0, f"{desc} - call")
    
    # OVERPAIR facing bet - call down
    if is_overpair or "overpair" in desc:
        if street != 'river':
            return ('call', 0, f"{desc} - call {street}")
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.35:
            return ('call', 0, f"{desc} - call small river")
        return ('fold', 0, f"{desc} - fold big river")
    
    # UNDERPAIR TO ACE facing bet - call flop, fold turn/river
    if is_underpair_to_ace or "underpair" in desc:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.25:
            return ('call', 0, f"{desc} - call small bet")
        return ('fold', 0, f"{desc} - fold (ace on board)")
    
    if "top pair good kicker" in desc:
        if street in ['flop', 'turn']:
            return ('call', 0, f"{desc} - call {street}")
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.40:
            return ('call', 0, f"{desc} - call small river")
        return ('fold', 0, f"{desc} - fold big river")
    
    if "top pair" in desc:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        return ('fold', 0, f"{desc} - fold {street}")
    
    if "pair" in desc and street == 'flop':
        return ('call', 0, f"{desc} - call flop")
    
    if has_flush_draw:
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.40:
            return ('call', 0, "flush draw - call")
    if has_oesd:
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.33:
            return ('call', 0, "OESD - call")
    if has_gutshot:
        return ('fold', 0, "gutshot - fold")
    
    return ('fold', 0, f"{desc} - fold")


def _postflop_sonnet(hole_cards, board, pot, to_call, street, is_ip, is_aggressor,
                     strength, desc, draws, combo_draw, has_flush_draw, has_oesd,
                     is_overpair, board_has_ace, is_underpair_to_ace=False, is_multiway=False):
    """
    Sonnet/Kiro_optimal postflop: Bigger value bets, overpair logic.
    From strategy file:
    - Nuts: 100% pot all streets
    - Sets: 85% pot all streets
    - Two pair: 80% pot all streets
    - TPTK: 75/70/60%
    - TPGK: 70/60/50%
    - TPWK: 65% flop, check-call later
    - Overpair: 70/60/50%
    - Overpair on Axx (KK on Axx): check-call only
    - Middle pair: check-call once, fold turn
    - Multiway: reduce c-bets sharply, bet mostly for value + strong draws
    """
    s = {
        'flop': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.80, 'tptk': 0.75, 'tpgk': 0.70, 'tpwk': 0.65, 'overpair': 0.70},
        'turn': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.80, 'tptk': 0.70, 'tpgk': 0.60, 'tpwk': 0.0, 'overpair': 0.60},
        'river': {'nuts': 1.0, 'set': 0.85, 'twopair': 0.80, 'tptk': 0.60, 'tpgk': 0.50, 'tpwk': 0.0, 'overpair': 0.50},
    }.get(street, {})
    
    if to_call == 0 or to_call is None:
        # Multiway: only bet strong value + strong draws
        if is_multiway:
            if strength >= 4:  # Sets+
                return ('bet', round(pot * s.get('set', 0.85), 2), f"{desc} - multiway value")
            if strength == 3:  # Two pair
                return ('bet', round(pot * 0.70, 2), f"{desc} - multiway value")
            if combo_draw:
                return ('bet', round(pot * 0.65, 2), "combo draw - multiway semi-bluff")
            return ('check', 0, f"{desc} - check multiway")
        
        # Heads-up betting logic
        if strength >= 5:
            return ('bet', round(pot * s.get('nuts', 1.0), 2), f"{desc} - bet 100%")
        if strength == 4:
            return ('bet', round(pot * s.get('set', 0.85), 2), f"{desc} - bet 85%")
        if strength == 3:
            return ('bet', round(pot * s.get('twopair', 0.80), 2), f"{desc} - bet 80%")
        
        # Big pocket pair below ace (KK/QQ/JJ/TT on Axx) - check-call only
        if is_underpair_to_ace:
            return ('check', 0, f"{desc} - check (pocket pair below ace)")
        
        # True overpair (QQ on J85)
        if is_overpair:
            return ('bet', round(pot * s.get('overpair', 0.70), 2), f"{desc} overpair - bet")
        
        if "top pair good kicker" in desc:
            return ('bet', round(pot * s.get('tptk', 0.75), 2), f"{desc} - value bet")
        if "top pair" in desc and "weak" not in desc:
            return ('bet', round(pot * s.get('tpgk', 0.70), 2), f"{desc} - value bet")
        if "top pair weak kicker" in desc and street == 'flop':
            return ('bet', round(pot * s.get('tpwk', 0.65), 2), f"{desc} - bet flop")
        
        if combo_draw:
            return ('bet', round(pot * 0.70, 2), "combo draw - semi-bluff 70%")
        if has_flush_draw and is_aggressor:
            return ('bet', round(pot * 0.50, 2), "flush draw - semi-bluff")
        
        return ('check', 0, f"{desc} - check")
    
    # Facing bet
    if strength >= 5:
        return ('call', 0, f"{desc} - call")
    if strength == 4:
        return ('call', 0, f"{desc} - call")
    if strength == 3:
        return ('call', 0, f"{desc} - call")
    
    # Big pocket pair below ace - check-call
    if is_underpair_to_ace:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop (pocket pair below ace)")
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.35:
            return ('call', 0, f"{desc} - call small bet")
        return ('fold', 0, f"{desc} - fold big bet (ace on board)")
    
    # True overpair facing bet
    if is_overpair:
        if street != 'river':
            return ('call', 0, f"{desc} overpair - call")
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.35:
            return ('call', 0, f"{desc} overpair - call small river")
        return ('fold', 0, f"{desc} overpair - fold big river")
    
    if "top pair good kicker" in desc:
        if street in ['flop', 'turn']:
            return ('call', 0, f"{desc} - call {street}")
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.40:
            return ('call', 0, f"{desc} - call small river")
        return ('fold', 0, f"{desc} - fold big river bet")
    
    if "top pair" in desc:
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop")
        return ('fold', 0, f"{desc} - fold {street}")
    
    # Middle pair: check-call once, fold turn
    if "middle pair" in desc or ("pair" in desc and "top" not in desc and "bottom" not in desc):
        if street == 'flop':
            return ('call', 0, f"{desc} - call flop once")
        return ('fold', 0, f"{desc} - fold {street}")
    
    if "pair" in desc and street == 'flop':
        return ('call', 0, f"{desc} - call flop")
    
    if has_flush_draw:
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.40:
            return ('call', 0, "flush draw - call <=40%")
    if has_oesd:
        pot_odds = to_call / (pot + to_call) if pot > 0 else 1
        if pot_odds <= 0.33:
            return ('call', 0, "OESD - call <=33%")
    
    return ('fold', 0, f"{desc} - fold")


# Preflop decision logic
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
        
        # 3-bet bluff
        if opener_pos in ['CO', 'BTN'] and hand in strategy.get('3bet_bluff', set()):
            if random.random() < 0.4:
                return ('raise', f'{hand} 3-bet bluff vs {opener_pos}')
        
        # Call IP
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
