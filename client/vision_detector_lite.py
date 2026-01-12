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

MODEL = "gpt-4.1-nano"  # gpt-5-nano is slow due to reasoning, use 4.1-nano instead

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
        
        prompt = """Read this PokerStars 6-max table screenshot. Return ONLY valid JSON:

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
- num_players: Count of players still in hand.
- facing_raise: TRUE if someone raised before hero.

Return ONLY the JSON object, nothing else."""

        t = time.time()
        try:
            response = self.client.responses.create(
                model=self.model,
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{image_data}"}
                    ]
                }]
            )
            api_time = time.time() - t
            
            # Debug: print response structure
            self.log(f"Response type: {type(response)}", "DEBUG")
            self.log(f"Response: {response}", "DEBUG")
            
            # Extract response text
            result_text = None
            if hasattr(response, 'output_text'):
                result_text = response.output_text
            elif hasattr(response, 'output'):
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
                raise ValueError(f"No text in response. Response keys: {dir(response)}")
            
            self.log(f"Raw response: {result_text[:200]}...", "DEBUG")
            
            # Clean up JSON
            result_text = result_text.strip()
            if result_text.startswith('```'):
                lines = result_text.split('\n')
                result_text = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
                result_text = result_text.strip()
            
            result = json.loads(result_text)
            result['api_time'] = api_time
            result['model'] = self.model
            
            return result
            
        except Exception as e:
            self.log(f"API Error: {e}", "ERROR")
            raise
