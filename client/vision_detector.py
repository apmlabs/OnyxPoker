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
        
        prompt = """Analyze this PokerStars 6-max table screenshot.

Return JSON:
{
  "hero_cards": ["As", "Kh"],
  "community_cards": ["Qd", "Jc", "Ts"],
  "pot": 0.15,
  "hero_stack": 5.00,
  "to_call": 0.02,
  "is_hero_turn": true,
  "action": "raise",
  "bet_size": 0.10,
  "reasoning": "explanation",
  "confidence": 0.95
}

READING THE TABLE:
- hero_cards: TWO face-up cards at BOTTOM. Format: As=Ace spades, Kh=King hearts. null if no cards.
- community_cards: Cards in CENTER. Empty [] if preflop.
- pot/hero_stack/to_call: Read EXACT amounts with decimals.
- to_call: Amount on CALL button, 0 if CHECK available, null if no buttons.
- is_hero_turn: TRUE if LARGE RED buttons visible, FALSE if only checkboxes.
- action: fold/check/call/bet/raise. NEVER fold when check is free!
- bet_size: When action is bet/raise, specify the amount in euros. Use 2.5-3x BB preflop, 65-75% pot postflop.
- reasoning: Focus on WHAT to do and WHY.

PREFLOP STRATEGY:
RAISE (2.5-3x BB) these hands. Pocket pairs MUST raise, never just call:
- Premium: AA-22, AKs-ATs, AKo, AQo, AJo, KQs-KJs, QJs
- Playable suited: A9s-A2s, KTs, QTs, JTs, T9s, 98s, 87s, 76s
BB DEFENSE vs min-raise: CALL with 22+, suited connectors (76s, 87s, 98s, T9s, JTs), A2s-A9s, KTs+, QTs+
FOLD everything else including:
- A9o, A7o, A6o, A5o, A4o (only SUITED aces playable)
- QTo, KTo, QJo, KJo (only SUITED versions playable)
- 98o, 87o, 76o, T2s, 94s (only GOOD suited connectors playable)
- NEVER call "because it's cheap" - if not in range, FOLD
CRITICAL: Check if SUITED (same suit symbol) or OFFSUIT before deciding!

POSTFLOP STRATEGY:
- STRAIGHTS/FLUSHES: BET 75-100% pot! You MUST bet, never check.
- POCKET PAIRS (JJ-22): If no overcard = OVERPAIR, BET. If ONE overcard = BET/CALL. If TWO+ overcards = check/fold.
- TOP PAIR = pair matching HIGHEST board card. TOP PAIR TOP KICKER: BET 65-75% pot.
- SECOND PAIR (pair matching 2nd highest card, e.g. KQ on A-K-x): CHECK river, don't value bet.
- SETS/TWO-PAIR: Bet 75-100% pot, never slowplay.
- TOP PAIR WEAK KICKER: Bet flop, CHECK turn and river.
- BOTTOM/MIDDLE PAIR (not pocket pair): CHECK. Never bet.
- NO PAIR: Check if free, fold to bets.

CRITICAL: Action MUST match reasoning. If reasoning says "fold" then action="fold".

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
        
        # Debug max_call
        self.log(f"max_call from GPT: {result.get('max_call')}, is_hero_turn: {result.get('is_hero_turn')}", "DEBUG")
        
        result['api_time'] = api_time
        result['model'] = self.model
        result['confidence'] = 0.95
        
        return result
