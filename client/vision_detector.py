"""
Vision-Based Poker Table Detection
Configurable AI model for poker table analysis
"""

import os
import base64
import json
from typing import Dict, Any, Optional
from openai import OpenAI

# Model configuration - change here to switch models
MODEL = "gpt-5.2"  # Options: gpt-5-mini, gpt-5.2, gpt-4o

class VisionDetector:
    def __init__(self, api_key: Optional[str] = None, logger=None):
        """Initialize vision detector"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.client = OpenAI(api_key=self.api_key)
        self.logger = logger
        self.model = MODEL
    
    def log(self, message: str, level: str = "INFO"):
        """Log to GUI only"""
        if self.logger:
            self.logger(message, level)
    
    def detect_poker_elements(self, screenshot_path: str, include_decision: bool = False) -> Dict[str, Any]:
        """Analyze poker table screenshot with AI vision"""
        import time
        
        timings = {}
        
        # Encode image
        t = time.time()
        with open(screenshot_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        timings['encode'] = time.time() - t
        
        # Build prompt
        t = time.time()
        if include_decision:
            prompt = """Analyze this poker screenshot. Return JSON only:

{
  "hero_cards": ["As", "Kh"],
  "community_cards": ["Qd", "Jc", "Ts"],
  "pot": 150,
  "hero_stack": 500,
  "to_call": 20,
  "available_actions": ["fold", "call", "raise"],
  "button_positions": {"fold": [300, 700], "call": [400, 700], "raise": [500, 700]},
  "recommended_action": "raise",
  "recommended_amount": 60,
  "reasoning": "Strong hand, good pot odds"
}

Use null if you can't see something. Cards format: As=Ace spades, Kh=King hearts."""
        else:
            prompt = """Analyze this poker screenshot. Return JSON only:

{
  "hero_cards": ["As", "Kh"],
  "community_cards": ["Qd", "Jc", "Ts"],
  "pot": 150,
  "hero_stack": 500,
  "to_call": 20,
  "available_actions": ["fold", "call", "raise"],
  "button_positions": {"fold": [300, 700], "call": [400, 700], "raise": [500, 700]}
}

Use null if you can't see something. Cards format: As=Ace spades, Kh=King hearts."""
        timings['prompt'] = time.time() - t
        
        # Call AI model
        t = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                ]
            }],
            max_completion_tokens=1000
        )
        timings['api'] = time.time() - t
        
        if not response.choices:
            raise ValueError("No response from API")
        
        choice = response.choices[0]
        result_text = choice.message.content
        
        self.log(f"Raw: {result_text[:200] if result_text else 'empty'}...", "DEBUG")
        
        if choice.finish_reason == 'length':
            raise ValueError("Response truncated")
        
        if not result_text:
            raise ValueError("Empty response")
        
        # Parse JSON
        t = time.time()
        result_text = result_text.strip()
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        timings['parse'] = time.time() - t
        
        result['confidence'] = 0.95
        result['timings'] = timings
        result['model'] = self.model
        
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
            'pot_region': None,  # GPT-5-mini reads pot directly, no region needed
            'confidence': elements.get('confidence', 0.95)
        }
        
        return calibration
