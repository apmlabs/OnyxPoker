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

CRITICAL - SUITED VS OFFSUIT:
Before ANY preflop decision, check BOTH card suits:
- Ad6d = SUITED (both diamonds) = A6s
- Ad6c = OFFSUIT (diamond vs club) = A6o
- 6h5s = OFFSUIT (heart vs spade) = 65o = FOLD
- 6s5s = SUITED (both spades) = 65s = CALL
If suits are DIFFERENT, treat as OFFSUIT and usually FOLD.

PREFLOP STRATEGY:
RAISE 2.5x: AA-99, AKs-ATs, AKo, AQo, AJo, KQs, KJs, KQo, QJs
AJo RULE: AJo vs single open = 3-BET always. €0.05 open is NOT a 3-bet!
CALL vs open (SUITED ONLY): 88-22, A2s-A9s, KTs, QTs, JTs, T9s, 98s, 87s, 76s, 65s
VS 3-BET (€0.15+ sizing): Call JJ-99, AQs, AKo. 4-bet QQ+, AKs. Fold rest including 22-88.

SB RULE: From SB facing ANY raise, FOLD unless:
- Pairs: AA-22
- Suited aces: A2s-AKs (MUST be same suit!)
- Suited connectors: 65s, 76s, 87s, 98s, T9s, JTs, QJs (MUST be same suit!)
FOLD from SB: All offsuit hands except pairs.

FOLD always preflop:
- ALL offsuit connectors: 65o, 76o, 87o, 98o, T9o, JTo (only suited versions call)
- Offsuit aces: A9o and below
- Offsuit broadways: KJo, KTo, QJo, QTo, JTo
- Weak suited: K9s-, Q9s-, J9s-, T8s-, 97s-, 86s-

BOTTOM PAIR: CHECK always. Never bet with bottom pair.

POSTFLOP STRATEGY:
- STRAIGHTS/FLUSHES/SETS/FULL HOUSE: BET 75-100% pot
- TWO PAIR (both hole cards paired): BET 75% pot all streets
- BOARD PAIR + POCKET PAIR (44 on K33): BET flop 70%, CHECK turn
- COMBO DRAWS (flush+straight, flush+pair): SEMI-BLUFF 65-75% pot
- TOP PAIR GOOD KICKER (AK/AQ/AJ on Axx): BET 70% flop, 65% turn, 50% river
- TOP PAIR WEAK KICKER (K7 on Kxx): BET flop 70% ONLY. If bet at later, CALL. Never RAISE.
- OVERPAIR on scary board (KK on Axx): CHECK-CALL only. NEVER raise.
- FLUSH DRAW alone: Check if free, call up to 40% pot
- STRAIGHT DRAW alone: Check if free, call up to 33% pot
- NO PAIR NO DRAW: CHECK always. NEVER bet with just ace-high or king-high.

Return ONLY JSON"""

        # JSON schema to enforce action consistency
        json_schema = {
            "name": "poker_decision",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "hero_cards": {"type": ["array", "null"], "items": {"type": "string"}},
                    "community_cards": {"type": "array", "items": {"type": "string"}},
                    "pot": {"type": ["number", "null"]},
                    "hero_stack": {"type": ["number", "null"]},
                    "to_call": {"type": ["number", "null"]},
                    "is_hero_turn": {"type": "boolean"},
                    "action": {"type": "string", "enum": ["fold", "check", "call", "bet", "raise"]},
                    "bet_size": {"type": ["number", "null"]},
                    "reasoning": {"type": "string"},
                    "confidence": {"type": "number"}
                },
                "required": ["hero_cards", "community_cards", "pot", "hero_stack", "to_call", "is_hero_turn", "action", "bet_size", "reasoning", "confidence"],
                "additionalProperties": False
            }
        }
        
        # Call GPT-5.2 using Responses API with structured output
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
            text={"format": {"type": "json_schema", "json_schema": json_schema}}
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
