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
RAISE 2.5x with: AA-TT, AKs-ATs, AKo, AQo, AJo (AJo is a RAISE not fold!), KQs, KJs, QJs
CALL vs open with: 99-22, A2s-A9s, KTs, QTs, JTs, T9s, 98s, 87s, 76s, KQo
NOT in call range: K9s, K8s, K7s, Q9s, J9s, T8s - these are FOLDS vs opens
VS 3-BET: Only continue with QQ+, AKs, AKo. Fold everything else.

SB RULE: From SB facing ANY raise (even 0.03), FOLD unless:
- Pairs: AA-22
- Suited aces: A2s-AKs  
- Suited connectors: 76s, 87s, 98s, T9s, JTs, QJs
FOLD from SB: T7s, Q8o, J7o, J9s, K7s, A9o, and all other trash

FOLD always preflop:
- Offsuit broadways: KJo, KTo, QJo, QTo, JTo
- Offsuit aces: ATo, A9o, A8o and below (AJo is RAISE!)
- Weak suited: K9s-, Q9s-, J9s-, T8s-, 97s-, 86s-, 75s-, 65s-
- All offsuit connectors: J7o, Q8o, 64o, 97o, T7o, etc

POSTFLOP STRATEGY:
- MADE HANDS (straights/flushes/sets/two-pair): BET 75% pot, never slowplay
- STRONG DRAWS (flush+pair, OESD+pair, combo draws): SEMI-BLUFF 65-75% pot
- TOP PAIR TOP KICKER: BET 65-75% pot all streets
- TOP PAIR WEAK KICKER (K7 on Kxx, Q6 on Qxx): Bet flop 70%, then CHECK turn, CHECK river. If bet at on turn/river, CALL only - NEVER raise with TPWK.
- SECOND PAIR: CHECK, call small bets only, fold to big bets
- OVERPAIR on scary board (KK on AAx): CHECK-CALL, do not raise into likely better hands
- FLUSH/STRAIGHT DRAWS alone: Check if free, call up to 33% pot
- NO PAIR NO DRAW (A-high, K-high, air): CHECK always. Do NOT bet. Just check and fold to bets.

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
