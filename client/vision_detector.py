"""
GPT-4o Vision-Based Poker Table Detection
Replaces OpenCV with AI that understands poker context
"""

import os
import base64
import json
from typing import Dict, Any, Optional
from openai import OpenAI

class VisionDetector:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize GPT-4o vision detector"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def detect_poker_elements(self, screenshot_path: str, include_decision: bool = False) -> Dict[str, Any]:
        """
        Analyze poker table screenshot with GPT-4o
        
        Args:
            screenshot_path: Path to screenshot
            include_decision: If True, also get poker decision recommendation
        
        Returns:
            {
                "hero_cards": ["As", "Kh"],
                "community_cards": ["Qd", "Jc", "Ts"],
                "pot": 150,
                "hero_stack": 500,
                "opponent_stacks": [480, 500, 450, 520, 490],
                "to_call": 20,
                "min_raise": 40,
                "available_actions": ["fold", "call", "raise"],
                "button_positions": {
                    "fold": [300, 700],
                    "call": [400, 700],
                    "raise": [500, 700]
                },
                "confidence": 0.95,
                
                # If include_decision=True:
                "recommended_action": "raise",
                "recommended_amount": 60,
                "reasoning": "Strong hand with straight draw, good pot odds"
            }
        """
        # Encode image
        with open(screenshot_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Build prompt
        if include_decision:
            prompt = """Analyze this poker table screenshot carefully and recommend the best action.

Identify and return JSON with:
1. hero_cards: Your 2 hole cards (e.g., ["As", "Kh"])
2. community_cards: Board cards 0-5 (e.g., ["Qd", "Jc", "Ts"])
3. pot: Pot amount in dollars (number)
4. hero_stack: Your stack in dollars (number)
5. opponent_stacks: List of opponent stacks (up to 5 players)
6. to_call: Amount to call in dollars (number)
7. min_raise: Minimum raise amount (number)
8. available_actions: List of actions you can take (["fold", "call", "raise"])
9. button_positions: Pixel coordinates of action buttons {"fold": [x, y], "call": [x, y], "raise": [x, y]}

POKER DECISION (analyze the situation):
10. recommended_action: "fold", "call", or "raise"
11. recommended_amount: If raising, the amount to raise (number)
12. reasoning: Brief explanation of why this is the best play (string)

Consider:
- Hand strength (pair, two pair, straight, flush, etc.)
- Pot odds (is calling profitable?)
- Position (early/middle/late)
- Stack sizes (yours and opponents)
- Board texture (wet/dry, draw-heavy)

Card format: Rank (A,K,Q,J,T,9-2) + Suit (s=spades, h=hearts, d=diamonds, c=clubs)
Example: "As" = Ace of Spades, "Kh" = King of Hearts

If you can't see something clearly, use null.
Return ONLY valid JSON, no explanation."""
        else:
            prompt = """Analyze this poker table screenshot carefully.

Identify and return JSON with:
1. hero_cards: Your 2 hole cards (e.g., ["As", "Kh"])
2. community_cards: Board cards 0-5 (e.g., ["Qd", "Jc", "Ts"])
3. pot: Pot amount in dollars (number)
4. hero_stack: Your stack in dollars (number)
5. opponent_stacks: List of opponent stacks (up to 5 players)
6. to_call: Amount to call in dollars (number)
7. min_raise: Minimum raise amount (number)
8. available_actions: List of actions you can take (["fold", "call", "raise"])
9. button_positions: Pixel coordinates of action buttons {"fold": [x, y], "call": [x, y], "raise": [x, y]}

Card format: Rank (A,K,Q,J,T,9-2) + Suit (s=spades, h=hearts, d=diamonds, c=clubs)
Example: "As" = Ace of Spades, "Kh" = King of Hearts

If you can't see something clearly, use null.
Return ONLY valid JSON, no explanation."""

        # Call GPT-4o
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0  # Deterministic
        )
        
        # Parse response
        result_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        result = json.loads(result_text)
        
        # Add confidence (GPT-4o doesn't provide this, so we estimate)
        result['confidence'] = 0.95
        
        return result
    
    def detect_calibration(self, screenshot_path: str) -> Dict[str, Any]:
        """
        Detect poker table elements for calibration
        Returns button regions and pot region
        """
        # Use same detection but extract regions
        elements = self.detect_poker_elements(screenshot_path)
        
        # Convert to calibration format
        calibration = {
            'button_regions': elements.get('button_positions', {}),
            'pot_region': None,  # GPT-4o reads pot directly, no region needed
            'confidence': elements.get('confidence', 0.95)
        }
        
        return calibration
