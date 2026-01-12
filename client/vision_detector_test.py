"""
Vision-only detector for fair comparison testing.
Uses same prompt as Kiro CLI (no strategy, just vision).
"""
import base64
import time
from openai import OpenAI
import os

class VisionDetectorTest:
    def __init__(self, model='gpt-5.2'):
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        self.model = model
    
    def analyze(self, screenshot_path):
        """Analyze poker table screenshot - VISION ONLY"""
        
        # Encode image
        with open(screenshot_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # SAME PROMPT AS KIRO CLI (vision only, no strategy)
        prompt = """Analyze this PokerStars 6-max table screenshot.

Return JSON:
{"hero_cards": ["As", "Kh"], "community_cards": ["Qd", "Jc", "Ts"], "pot": 0.15, "is_hero_turn": true}

READING THE TABLE:
- hero_cards: TWO face-up cards at BOTTOM. Format: As=Ace spades, Kh=King hearts, Tc=Ten clubs, 5d=Five diamonds. null if no cards visible.
- community_cards: Cards in CENTER of table. Empty [] if preflop (no board cards yet).
- pot: Read EXACT amount with decimals from "Pot: €X.XX" text.
- is_hero_turn: TRUE if LARGE RED action buttons visible (Fold/Call/Raise), FALSE if only checkboxes or waiting.

SUIT SYMBOLS (CRITICAL):
- Spades (♠): BLACK suit with pointed bottom
- Clubs (♣): BLACK suit with rounded clover shape  
- Hearts (♥): RED suit with rounded top
- Diamonds (♦): RED suit with pointed corners
DO NOT confuse black suits (♠ vs ♣) or red suits (♥ vs ♦)!

Return ONLY valid JSON with these exact fields."""
        
        # JSON schema
        json_schema = {
            "type": "object",
            "properties": {
                "hero_cards": {"type": ["array", "null"], "items": {"type": "string"}},
                "community_cards": {"type": "array", "items": {"type": "string"}},
                "pot": {"type": ["number", "null"]},
                "is_hero_turn": {"type": "boolean"}
            },
            "required": ["hero_cards", "community_cards", "pot", "is_hero_turn"],
            "additionalProperties": False
        }
        
        # Call GPT-5.2
        t = time.time()
        response = self.client.responses.create(
            model=self.model,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{image_data}"}
                ]
            }],
            max_output_tokens=200,
            reasoning={"effort": "none"},
            text={"format": {"type": "json_schema", "name": "poker_vision", "schema": json_schema}}
        )
        elapsed = time.time() - t
        
        # Parse response
        import json
        result = json.loads(response.output[0].content[0].text)
        result['_performance'] = {'total': elapsed}
        
        return result
