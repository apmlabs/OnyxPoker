"""
Opponent lookup - get stats and advice for players at the table.
"""

import json
import os
from typing import Dict, List, Optional

STATS_FILE = os.path.join(os.path.dirname(__file__), 'player_stats.json')

def load_player_stats() -> Dict:
    """Load player stats from JSON file."""
    if not os.path.exists(STATS_FILE):
        return {}
    with open(STATS_FILE) as f:
        return json.load(f)

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
    """Look up stats for a list of player names."""
    stats = load_player_stats()
    results = []
    
    for name in player_names:
        if name in stats:
            s = stats[name]
            results.append({
                'name': name,
                'hands': s['hands'],
                'vpip': s['vpip'],
                'pfr': s['pfr'],
                'archetype': s['archetype'],
                'advice': get_advice(s['archetype'])
            })
        else:
            results.append({
                'name': name,
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
