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
  "is_hero_turn": true,
  "recommended_action": "fold",
  "recommended_amount": null,
  "max_call": null,
  "reasoning": "Detailed explanation here",
  "confidence": 0.95
}

Rules:
- hero_cards: The TWO face-up cards at BOTTOM of screen. Format: As=Ace spades, Kh=King hearts, Td=Ten diamonds. Use null if hero has no cards (sitting out)
- community_cards: Cards in CENTER of table. Empty [] if preflop
- pot/hero_stack/to_call: Read EXACT amounts including decimals (e.g. 0.05 not 5). Look at currency symbol and decimal point carefully
- to_call: Amount on CALL button, 0 if CHECK available, null if no action buttons
- hero_position: Find the dealer button (D chip). BTN=on hero, SB=one left of BTN, BB=two left of BTN, CO/MP/EP for others
- is_hero_turn: Look at BOTTOM RIGHT corner. TRUE only if you see LARGE RED rectangular buttons with white text like "Fold" "Call €X" "Raise To €X" or "Check" "Bet €X". These buttons are ~150px wide and bright red. FALSE if you only see small gray/white checkboxes with text like "Check", "Check/Fold", "Call Any", "Fold" - those are pre-select options, NOT action buttons.
- recommended_action: What hero SHOULD do. When is_hero_turn=FALSE, recommend what to do IF action gets to hero (e.g. "raise" on BTN with K9o preflop means open-raise if folded to). NEVER recommend fold when checking is free!
- max_call: When is_hero_turn=FALSE, set max amount to call if someone raises ahead. Example: K9o on BTN preflop → action="raise", max_call=0.06 (call up to 3bb if someone opens). Use 0.0 only for trash hands that should fold to any raise.
- reasoning: 2-3 sentences explaining the decision
- confidence: 0.0-1.0 how confident you are in the recommendation

Strategy rules:
- HAND STRENGTH: Hero has pair ONLY if one of hero's 2 cards matches a board card. Example: Hero Q9 on 44T board = NO PAIR (queen high). Hero Q4 on 44T = trips. Board pair alone does NOT give hero a pair!
- STRAIGHTS: Hero has straight ONLY if 5 consecutive ranks exist using BOTH hero cards + board. Example: Hero A2 on 564 board = NO STRAIGHT (just ace high, gutshot to wheel). Hero A2 on 543 board = wheel straight. VERIFY the 5 cards form consecutive ranks!
- STRAIGHT DRAWS: OESD needs 4 consecutive cards where hero contributes. J7 on TQ4 = gutshot only (needs 9), NOT OESD. The 7 doesn't connect! Verify each card in the sequence.
- FLUSH DRAWS: Hero has flush draw ONLY if hero's suit matches board suit. Hero spades on hearts board = NO flush draw
- SUITED vs OFFSUIT: Check BOTH card suits carefully. A♠2♦ = offsuit (different suits). A♠2♠ = suited (same suit). This affects preflop decisions!
- VALUE BETTING: With sets, trips, two-pair, strong top pair - ALWAYS bet or raise for value. At 2NL opponents call light, so bet thinner than higher stakes.
- NEVER SLOWPLAY: Sets/trips/two-pair should bet every street for value. Checking strong hands loses money at micros.
- Suited aces (A2s-A9s) are playable on BTN/CO - call or raise, do not fold

MICRO STAKES (2NL) ADJUSTMENTS:
- Players at 2NL rarely fold pairs - reduce bluff frequency
- If villain calls flop AND turn, they have something - do NOT bluff river with air
- Only bluff with equity (draws, blockers) or on very scary board changes
- Triple barrel bluffing with ace-high = burning money at micros

VALUE BETTING STRATEGY (CRITICAL FOR PROFIT):
- With sets/trips/two-pair: ALWAYS bet or raise for value - never slowplay
- Opponents call too light at 2NL - bet thinner for value than higher stakes
- Top pair good kicker: bet all three streets for value
- Overpairs: bet for value and protection, don't slowplay

DEFENSIVE STRATEGY:
- Big blind defense: call with any ace, suited connectors, pocket pairs
- Don't fold decent hands to small bets - opponents bluff less at micros
- When check is free, NEVER fold - always take the free card
- Preflop: fold trash hands like J6o, 96o even on BTN - don't call just because it's cheap
- Preflop OOP: fold weak aces (A2o-A9o) and weak kings (K2o-K9o) facing raises - they make dominated pairs
- Multiway pots: tighten up significantly, weak hands play poorly vs multiple opponents
- On monotone boards without the flush suit, be cautious - call don't raise with pair+draw

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
