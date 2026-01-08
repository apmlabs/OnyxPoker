"""
Vision-Based Poker Table Detection using GPT-5.2 Responses API
"""

import os
import base64
import json
import time
from typing import Dict, Any, Optional
from openai import OpenAI

MODEL = "gpt-5.2"

class VisionDetector:
    def __init__(self, api_key: Optional[str] = None, logger=None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.client = OpenAI(api_key=self.api_key)
        self.logger = logger
        self.model = MODEL
    
    def log(self, message: str, level: str = "INFO"):
        if self.logger:
            self.logger(message, level)
    
    def detect_poker_elements(self, screenshot_path: str, include_decision: bool = False) -> Dict[str, Any]:
        """Analyze poker table screenshot using GPT-5.2 Responses API"""
        
        # Encode image
        with open(screenshot_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        prompt = """Analyze this PokerStars table screenshot. HERO is the player at the BOTTOM of the screen (their cards face up).

Return ONLY valid JSON:
{
  "hero_cards": ["As", "Kh"],
  "community_cards": ["Qd", "Jc", "Ts"],
  "pot": 0.15,
  "hero_stack": 5.00,
  "to_call": 0.02,
  "hero_position": "SB",
  "num_players": 6,
  "players_in_hand": 3,
  "recommended_action": "fold",
  "recommended_amount": null,
  "reasoning": "Brief explanation",
  "confidence": 0.95
}

Rules:
- hero_cards: The TWO face-up cards at BOTTOM of screen. Format: As=Ace spades, Kh=King hearts, Td=Ten diamonds. Use null if hero has no cards (sitting out)
- community_cards: Cards in CENTER of table. Empty [] if preflop
- pot/hero_stack/to_call: Read EXACT amounts including decimals (e.g. 0.05 not 5). Look at currency symbol and decimal point carefully
- to_call: Amount on CALL button, 0 if CHECK available, null if no action buttons
- hero_position: Find the dealer button (D chip). BTN=on hero, SB=one left of BTN, BB=two left of BTN, CO/MP/EP for others
- recommended_action: fold/call/check/raise/bet. Consider position and hand strength
- confidence: 0.0-1.0 how confident you are in the recommendation

Strategy rules:
- With sets or better, BET/RAISE for value - do not check strong hands
- Raise strong suited broadways (KQs, QJs, AJs) vs limpers when in position
- Only cite flush draws if hero's suit matches board suits (e.g. hero has clubs, board has clubs)
- When in position with a strong hand, prefer betting over checking

Return ONLY JSON"""

        # Call GPT-5.2 using Responses API
        t = time.time()
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{image_data}"}
                    ]
                }
            ],
            max_output_tokens=500,
            reasoning={"effort": "none"},
            text={"verbosity": "low"}
        )
        api_time = time.time() - t
        
        # Extract response text
        result_text = None
        for item in response.output:
            if hasattr(item, 'content'):
                for content in item.content:
                    if hasattr(content, 'text'):
                        result_text = content.text
                        break
        
        if not result_text:
            raise ValueError("No text in response")
        
        self.log(f"Raw: {result_text[:150]}...", "DEBUG")
        
        # Parse JSON
        result_text = result_text.strip()
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError as e:
            self.log(f"JSON error: {result_text[:100]}", "ERROR")
            raise ValueError(f"Invalid JSON: {e}")
        
        result['api_time'] = api_time
        result['model'] = self.model
        result['confidence'] = 0.95
        
        return result
