"""
Opponent lookup - get stats and advice for players at the table.
"""

import json
import os
from difflib import SequenceMatcher
from typing import Dict, List, Optional

STATS_FILE = os.path.join(os.path.dirname(__file__), 'player_stats.json')
FUZZY_THRESHOLD = 0.82  # 82% similarity to match

_stats_cache = None
_fuzzy_cache = {}  # Cache fuzzy matches

def load_player_stats() -> Dict:
    """Load player stats from JSON file."""
    global _stats_cache
    if _stats_cache is not None:
        return _stats_cache
    if not os.path.exists(STATS_FILE):
        return {}
    with open(STATS_FILE) as f:
        _stats_cache = json.load(f)
    return _stats_cache

def fuzzy_match(name: str, stats: Dict) -> Optional[str]:
    """Find best fuzzy match for a name in stats DB."""
    if name in _fuzzy_cache:
        return _fuzzy_cache[name]
    
    if name in stats:
        _fuzzy_cache[name] = name
        return name
    
    best_match = None
    best_ratio = FUZZY_THRESHOLD
    
    for db_name in stats.keys():
        ratio = SequenceMatcher(None, name.lower(), db_name.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = db_name
    
    _fuzzy_cache[name] = best_match
    return best_match

def get_advice(archetype: str) -> str:
    """Get short exploitation advice."""
    return {
        'fish': "VALUE BET - they call too much",
        'nit': "STEAL BLINDS - fold to their raises",
        'tag': "RESPECT raises - 3bet light",
        'lag': "CALL DOWN - they bluff too much",
        'maniac': "TRAP - let them hang themselves"
    }.get(archetype, "Play solid")

def lookup_opponents(player_names: List[str]) -> List[Dict]:
    """Look up stats for a list of player names (with fuzzy matching)."""
    stats = load_player_stats()
    results = []
    
    for name in player_names:
        matched_name = fuzzy_match(name, stats)
        if matched_name:
            s = stats[matched_name]
            results.append({
                'name': name,
                'matched_name': matched_name if matched_name != name else None,
                'hands': s['hands'],
                'vpip': s['vpip'],
                'pfr': s['pfr'],
                'archetype': s['archetype'],
                'advice': get_advice(s['archetype'])
            })
        else:
            results.append({
                'name': name,
                'matched_name': None,
                'hands': 0,
                'archetype': 'unknown',
                'advice': 'No data - play solid'
            })
    
    return results

def format_opponent_line(opponents: List[Dict]) -> str:
    """Format opponent info for helper bar display."""
    known = [o for o in opponents if o['hands'] > 0]
    
    if not known:
        return "No known opponents"
    
    # Sort by hands (most data first)
    known.sort(key=lambda x: x['hands'], reverse=True)
    
    parts = []
    for o in known[:3]:  # Top 3 with most data
        parts.append(f"{o['name'][:12]}: {o['archetype'].upper()} ({o['hands']}h)")
    
    return " | ".join(parts)

def format_advice_line(opponents: List[Dict]) -> str:
    """Format advice for the most relevant opponent."""
    known = [o for o in opponents if o['hands'] > 0]
    
    if not known:
        return ""
    
    # Prioritize: fish > maniac > lag > nit > tag
    priority = {'fish': 5, 'maniac': 4, 'lag': 3, 'nit': 2, 'tag': 1, 'unknown': 0}
    known.sort(key=lambda x: (priority.get(x['archetype'], 0), x['hands']), reverse=True)
    
    top = known[0]
    return f"vs {top['name'][:12]}: {top['advice']}"


if __name__ == "__main__":
    # Test with some known players
    test_names = ['Jorgebcn76', 'VEGAYAEM', 'marry24', 'UnknownPlayer123']
    
    print("Looking up:", test_names)
    print()
    
    results = lookup_opponents(test_names)
    for r in results:
        print(f"{r['name']:<20} {r.get('hands', 0):>4}h  {r['archetype']:<8} {r['advice']}")
    
    print()
    print("Helper bar line 3:", format_opponent_line(results))
    print("Advice line:", format_advice_line(results))
