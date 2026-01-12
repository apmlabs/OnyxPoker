"""
Lite Vision Detector - Uses gpt-5-nano for table data extraction only.
No poker strategy - just reads the table state.
"""

import os
import base64
import json
import time
from typing import Dict, Any, Optional
from openai import OpenAI

MODEL = "gpt-5-nano"

class VisionDetectorLite:
    def __init__(self, api_key: Optional[str] = None, logger=None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found")
        self.client = OpenAI(api_key=self.api_key)
        self.logger = logger
        self.model = MODEL
    
    def log(self, message: str, level: str = "INFO"):
        if self.logger:
            self.logger(message, level)
    
    def detect_table(self, screenshot_path: str) -> Dict[str, Any]:
        """Extract table data only - no strategy decisions."""
        
        with open(screenshot_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        prompt = """Read this PokerStars 6-max table screenshot. Return ONLY table data as JSON:

{
  "hero_cards": ["As", "Kh"],
  "community_cards": ["Qd", "Jc", "Ts"],
  "pot": 0.15,
  "hero_stack": 5.00,
  "to_call": 0.02,
  "is_hero_turn": true,
  "position": "BTN",
  "num_players": 3,
  "facing_raise": false
}

READING RULES:
- hero_cards: TWO face-up cards at BOTTOM. Format: As=Ace spades, Kh=King hearts. null if no cards.
- community_cards: Cards in CENTER. Empty [] if preflop.
- pot/hero_stack/to_call: Read EXACT amounts with decimals.
- to_call: Amount on CALL button, 0 if CHECK available, null if no buttons.
- is_hero_turn: TRUE if LARGE RED buttons visible, FALSE if only checkboxes.
- position: UTG/MP/CO/BTN/SB/BB based on dealer button location relative to hero.
- num_players: Count of players still in hand (have cards or chips committed).
- facing_raise: TRUE if someone raised before hero, FALSE if first to act or facing limp.

SUIT CHECK: As=Ace spades, Ah=Ace hearts, Ad=Ace diamonds, Ac=Ace clubs.

Return ONLY JSON, no explanation."""

        json_schema = {
            "type": "object",
            "properties": {
                "hero_cards": {"type": ["array", "null"], "items": {"type": "string"}},
                "community_cards": {"type": "array", "items": {"type": "string"}},
                "pot": {"type": ["number", "null"]},
                "hero_stack": {"type": ["number", "null"]},
                "to_call": {"type": ["number", "null"]},
                "is_hero_turn": {"type": "boolean"},
                "position": {"type": ["string", "null"]},
                "num_players": {"type": ["integer", "null"]},
                "facing_raise": {"type": "boolean"}
            },
            "required": ["hero_cards", "community_cards", "pot", "hero_stack", "to_call", "is_hero_turn", "position", "num_players", "facing_raise"],
            "additionalProperties": False
        }
        
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
            text={"format": {"type": "json_schema", "name": "table_data", "schema": json_schema}}
        )
        api_time = time.time() - t
        
        # Extract response - gpt-5-nano returns output as string or in output array
        result_text = None
        if hasattr(response, 'output'):
            if isinstance(response.output, str):
                result_text = response.output
            elif isinstance(response.output, list):
                for item in response.output:
                    if hasattr(item, 'content'):
                        for content in item.content:
                            if hasattr(content, 'text'):
                                result_text = content.text
                                break
                    if result_text:
                        break
        
        if not result_text:
            raise ValueError("No text in response")
        
        result_text = result_text.strip()
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        result = json.loads(result_text)
        result['api_time'] = api_time
        result['model'] = self.model
        
        return result
