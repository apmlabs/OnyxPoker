"""
Vision Detector V2 - Extended detection including player names.
Experimental - does not replace vision_detector_lite.py
"""

import os
import base64
import json
import time
from typing import Dict, Any, Optional
from openai import OpenAI

DEFAULT_MODEL = "gpt-5.2"

class VisionDetectorV2:
    def __init__(self, api_key: Optional[str] = None, logger=None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found")
        self.client = OpenAI(api_key=self.api_key)
        self.logger = logger
        self.model = model or DEFAULT_MODEL
    
    def log(self, message: str, level: str = "INFO"):
        if self.logger:
            self.logger(message, level)
    
    def detect_table(self, screenshot_path: str) -> Dict[str, Any]:
        """Extract extended table data including player names."""
        
        with open(screenshot_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        prompt = """Read this PokerStars 6-max table screenshot. Return ONLY valid JSON:

{
  "hero_cards": ["As", "Kh"],
  "community_cards": ["Qd", "Jc", "Ts"],
  "pot": 0.15,
  "hero_stack": 5.00,
  "to_call": 0.02,
  "is_hero_turn": true,
  "big_blind": 0.02,
  "players_in_hand": 3,
  "players": [
    {"name": "Player1", "stack": 5.00, "has_cards": true},
    {"name": "Player2", "stack": 3.50, "has_cards": false},
    {"name": "HeroName", "stack": 5.00, "has_cards": true, "is_hero": true}
  ]
}

CRITICAL - CARD SUIT DETECTION:
Look VERY carefully at card suits. Do NOT guess or assume:
- SPADES = black pointy symbol (s)
- HEARTS = red heart symbol (h)  
- DIAMONDS = red diamond symbol (d)
- CLUBS = black clover symbol (c)

COMMON MISTAKES TO AVOID:
- Confusing hearts with diamonds (both red)
- Confusing spades with clubs (both black)
- Hallucinating cards that aren't visible
- Mixing up card order

READING RULES:
- hero_cards: TWO face-up cards at BOTTOM CENTER. Format: As=Ace spades, Kh=King hearts, Td=Ten diamonds. null if no visible cards or cards face-down.
- community_cards: Cards in CENTER of table. Empty [] if preflop (no board yet).
- pot: Total pot amount shown in CENTER. Read exact decimal value.
- hero_stack: Hero's chip stack at BOTTOM. Read exact decimal value.
- to_call: Amount shown on CALL button. 0 if CHECK button visible. null if no action buttons.
- is_hero_turn: TRUE if LARGE RED action buttons (FOLD/CHECK/CALL/RAISE) visible. FALSE if only small checkboxes.
- big_blind: Read from WINDOW TITLE at top. Format is "Table - $SB/$BB". Extract BB value.

PLAYER DETECTION:
- players_in_hand: Count of players who still have cards (not folded). Look for face-down card backs.
- players: Array of occupied seats clockwise from bottom-left:
  - name: Player's username shown below their avatar. MUST be actual username, NOT button text like "Fold", "Call", "Post BB"
  - stack: Their chip amount
  - has_cards: TRUE if they have card backs visible (still in hand), FALSE if folded
  - is_hero: TRUE only for the player at BOTTOM CENTER with face-up cards
- Omit empty seats from the array

Return ONLY the JSON object, nothing else."""

        t = time.time()
        try:
            api_params = {
                "model": self.model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                    ]
                }],
                "response_format": {"type": "json_object"}
            }
            
            if self.model.startswith('gpt-5.1') or self.model.startswith('gpt-5.2'):
                api_params["reasoning_effort"] = "none"
            elif self.model.startswith('gpt-5'):
                api_params["reasoning_effort"] = "minimal"
            
            response = self.client.chat.completions.create(**api_params)
            api_time = time.time() - t
            
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith('```'):
                lines = result_text.split('\n')
                result_text = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:]).strip()
            
            result = json.loads(result_text)
            result['api_time'] = api_time
            result['model'] = self.model
            
            return result
            
        except Exception as e:
            self.log(f"API Error: {e}", "ERROR")
            raise


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python vision_detector_v2.py <screenshot.png>")
        sys.exit(1)
    
    detector = VisionDetectorV2()
    result = detector.detect_table(sys.argv[1])
    print(json.dumps(result, indent=2))
