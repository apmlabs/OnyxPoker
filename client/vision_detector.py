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

POSITION DETECTION (CRITICAL - follow exactly):

The table is an oval with 6 seats arranged like this:
```
        [Seat 1]    [Seat 2]
    [Seat 6]            [Seat 3]
        [Seat 5]    [Seat 4]
              HERO
```
HERO is always at the bottom (Seat 5 area).

1. Find the DEALER BUTTON: A RED SPADE with STAR inside, next to a player's avatar
2. The player WITH the dealer button is BTN (Button)
3. Positions go in order around the table: BTN -> SB -> BB -> UTG -> MP -> CO -> BTN...
4. Starting from BTN, go LEFT around the table to find each position

TO FIND HERO'S POSITION:
- Look at where the dealer button is
- If button is at HERO (bottom) -> HERO is BTN
- If button is at bottom-right -> HERO is SB (one left of button)
- If button is at right side -> HERO is BB (two left of button)
- If button is at top-right -> HERO is UTG (three left of button)
- If button is at top-left -> HERO is MP (four left of button)
- If button is at left side -> HERO is CO (five left of button)

VERIFY: SB has €0.01 posted, BB has €0.02 posted. Check hero's posted blind amount.

Return ONLY valid JSON:
{
  "hero_cards": ["As", "Kh"],
  "community_cards": ["Qd", "Jc", "Ts"],
  "pot": 0.15,
  "hero_stack": 5.00,
  "to_call": 0.02,
  "position": "UTG",
  "num_players": 6,
  "players_in_hand": 3,
  "is_hero_turn": true,
  "action": "fold",
  "amount": 0,
  "max_call": null,
  "reasoning": "Detailed explanation here",
  "confidence": 0.95
}

Rules:
- hero_cards: The TWO face-up cards at BOTTOM of screen. Format: As=Ace spades, Kh=King hearts, Td=Ten diamonds. Use null if hero has no cards (sitting out)
- community_cards: Cards in CENTER of table. Empty [] if preflop
- pot/hero_stack/to_call: Read EXACT amounts including decimals (e.g. 0.05 not 5). Look at currency symbol and decimal point carefully
- to_call: Amount on CALL button, 0 if CHECK available, null if no action buttons
- position: MUST be UTG, MP, CO, BTN, SB, or BB. Use the position detection steps above. Count how many seats clockwise the dealer button is from hero, then determine hero's position.
- is_hero_turn: Look at BOTTOM RIGHT corner. TRUE only if you see LARGE RED rectangular buttons with white text like "Fold" "Call €X" "Raise To €X" or "Check" "Bet €X". These buttons are ~150px wide and bright red. FALSE if you only see small gray/white checkboxes with text like "Check", "Check/Fold", "Call Any", "Fold" - those are pre-select options, NOT action buttons.
- action: What hero SHOULD do. When is_hero_turn=FALSE, recommend what to do IF action gets to hero (e.g. "raise" on BTN with K9o preflop means open-raise if folded to). NEVER recommend fold when checking is free!
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
- Suited aces (A2s-A9s): Playable CO/BTN only, fold UTG/MP/SB vs raises
- Suited kings (K9s+): Playable CO/BTN, fold K2s-K8s in all positions vs raises
- POSITION-SPECIFIC RANGES (CRITICAL):
  * UTG: Tight range - AA-TT, AK-AQ, AJs+, KQs (fold K2s-K9s, A2s-A9s)
  * MP: Add ATs+, KJs+, QJs, suited aces A9s+ (fold K2s-K8s, A2s-A8s)  
  * CO: Add suited connectors 98s+, suited kings K9s+, A2s+ (fold K2s-K8s)
  * BTN: Wide range - K2s+, A2s+, suited connectors 65s+, any pocket pair
  * SB: Tight vs raises (fold K2s-K9s, A2s-A9s), wider vs limps
  * BB: Defend wide vs small raises, fold weak hands vs 3bets OOP

MICRO STAKES (2NL) ADJUSTMENTS:
- Players at 2NL rarely fold pairs - reduce bluff frequency
- If villain calls flop AND turn, they have something - do NOT bluff river with air
- Only bluff with equity (draws, blockers) or on very scary board changes
- Triple barrel bluffing with ace-high = burning money at micros
- EXPLOIT LOOSE-PASSIVE POOL: 
  * UTG/MP value bets: 60-75% pot (tighter ranges need protection)
  * CO/BTN value bets: 75-100% pot (wider ranges, more bluffs)
  * Against calling stations: bet bigger with value, smaller with bluffs
- Suited kings (K9s+) are playable on BTN/CO - don't auto-fold suited hands
- 3-BET STRATEGY (CRITICAL): With AQ+, KQs, JJ+ in position vs single raiser: 3-BET, don't flat. KQo on BTN vs open = 3-bet to 3x their raise. Flatting premium hands loses value at 2NL.

VALUE BETTING STRATEGY (CRITICAL FOR PROFIT):
- With sets/trips/two-pair/full house: ALWAYS bet or raise for value - never slowplay
- NUTS/NEAR-NUTS: Bet large (75-100% pot) - 2NL players call with weak hands
- Opponents call too light at 2NL - bet thinner for value than higher stakes
- Top pair good kicker: bet all three streets for value (60-75% pot sizing)
- Overpairs: bet for value and protection, don't slowplay
- Two pair or better: NEVER just call - always bet or raise for maximum value
- FULL HOUSE/QUADS: Always jam/raise for maximum value - never slowplay the nuts

DEFENSIVE STRATEGY:
- Big blind defense: call with any ace, suited connectors, pocket pairs
- Don't fold decent hands to small bets - opponents bluff less at micros
- When check is free, NEVER fold - always take the free card
- ACE-HIGH CALLS: With A-high and backdoor draws, call small bets (under 1/3 pot)
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
        
        # Validate position detection
        valid_positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
        if result.get('position') not in valid_positions:
            self.log(f"WARNING: Invalid position '{result.get('position')}' detected. Expected one of: {valid_positions}", "ERROR")
            result['position'] = '?'  # Mark as unknown for debugging
        
        return result
