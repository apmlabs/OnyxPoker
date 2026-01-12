"""
Poker-specific strategy using Kiro CLI
Replaces GPT API calls with Kiro CLI subprocess
"""

import subprocess
import json
import re
from typing import Dict, Any

def analyze_poker_state(state: Dict[str, Any], screenshot_path: str = None) -> Dict[str, Any]:
    """
    Analyze poker game state using Kiro CLI
    
    Args:
        state: Parsed poker state (cards, bets, stacks, etc.)
        screenshot_path: Optional path to screenshot for visual analysis
    
    Returns:
        Decision dict with action, amount, reasoning
    """
    prompt = build_poker_prompt(state)
    
    print(f"\n{'='*60}")
    print(f"CALLING KIRO CLI WITH PROMPT:")
    print(f"{'='*60}")
    print(prompt)
    print(f"{'='*60}\n")
    
    try:
        # Call Kiro CLI
        result = subprocess.run(
            ['kiro-cli', 'chat', prompt],
            capture_output=True,
            text=True,
            timeout=45
        )
        
        print(f"\n{'='*60}")
        print(f"KIRO CLI RESPONSE:")
        print(f"{'='*60}")
        print(result.stdout)
        print(f"{'='*60}\n")
        
        response = result.stdout.strip()
        return parse_poker_decision(response, state)
        
    except subprocess.TimeoutExpired:
        return {'action': 'fold', 'amount': 0, 'reasoning': 'Timeout - defaulting to fold'}
    except Exception as e:
        return {'action': 'fold', 'amount': 0, 'reasoning': f'Error: {str(e)}'}

def build_poker_prompt(state: Dict[str, Any]) -> str:
    """Build structured prompt for Kiro CLI"""
    hero_cards = ', '.join(state.get('hero_cards', []))
    community = ', '.join(state.get('community_cards', []))
    pot = state.get('pot', 0)
    stacks = state.get('stacks', [])
    actions = state.get('actions', {})
    
    # Extract call amount from actions
    call_text = actions.get('call', '')
    to_call = extract_number(call_text)
    
    prompt = f"""You are playing 6-max No-Limit Texas Hold'em poker.

CURRENT SITUATION:
- Your cards: {hero_cards or 'Unknown'}
- Board: {community or 'None'}
- Pot: ${pot}
- Your stack: ${stacks[2] if len(stacks) > 2 else 0}
- To call: ${to_call}

AVAILABLE ACTIONS: {', '.join(k for k, v in actions.items() if v)}

Analyze and respond with ONE of:
- fold
- call
- raise <amount>

Be concise."""
    
    return prompt

def parse_poker_decision(response: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Kiro CLI response into action dict"""
    response_lower = response.lower()
    
    # Look for explicit action at start of response
    first_line = response_lower.split('\n')[0].strip()
    
    # Check for raise first (most specific)
    if 'raise' in first_line or 'bet' in first_line:
        amount = extract_number(response)
        if not amount:
            amount = state.get('pot', 0) // 2  # Default to half pot
        return {'action': 'raise', 'amount': amount, 'reasoning': response}
    elif 'fold' in first_line:
        return {'action': 'fold', 'amount': 0, 'reasoning': response}
    elif 'call' in first_line or 'check' in first_line:
        call_text = state.get('actions', {}).get('call', '')
        amount = extract_number(call_text)
        return {'action': 'call', 'amount': amount, 'reasoning': response}
    else:
        # Fallback: check entire response
        if 'raise' in response_lower or 'bet' in response_lower:
            amount = extract_number(response)
            if not amount:
                amount = state.get('pot', 0) // 2
            return {'action': 'raise', 'amount': amount, 'reasoning': response}
        elif 'fold' in response_lower:
            return {'action': 'fold', 'amount': 0, 'reasoning': response}
        elif 'call' in response_lower or 'check' in response_lower:
            call_text = state.get('actions', {}).get('call', '')
            amount = extract_number(call_text)
            return {'action': 'call', 'amount': amount, 'reasoning': response}
        else:
            return {'action': 'fold', 'amount': 0, 'reasoning': 'Unclear response'}

def extract_number(text: str) -> int:
    """Extract first number from text"""
    match = re.search(r'\d+', text)
    return int(match.group()) if match else 0
