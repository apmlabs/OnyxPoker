"""
GPT-5-mini Vision-Based Poker Table Detection
Uses GPT-5-mini multimodal model for poker table analysis
"""

import os
import base64
import json
from typing import Dict, Any, Optional
from openai import OpenAI

class VisionDetector:
    def __init__(self, api_key: Optional[str] = None, logger=None):
        """Initialize GPT-5-mini vision detector"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.client = OpenAI(api_key=self.api_key)
        self.logger = logger  # GUI logger function
    
    def log(self, message: str, level: str = "INFO"):
        """Log to GUI if logger provided, otherwise print"""
        if self.logger:
            self.logger(message, level)
        else:
            print(f"[{level}] {message}")
    
    def detect_poker_elements(self, screenshot_path: str, include_decision: bool = False) -> Dict[str, Any]:
        """
        Analyze poker table screenshot with GPT-5-mini
        """
        import time
        start_time = time.time()
        
        # Encode image
        encode_start = time.time()
        with open(screenshot_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        encode_time = time.time() - encode_start
        
        # Short console log for HTTP requests only
        print(f"[API] GPT-5-mini request: {len(image_data)} bytes")
        
        # Build prompt (shorter for token efficiency)
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

        api_start = time.time()
        
        # Call GPT-5-mini
        response = self.client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                ]
            }],
            max_completion_tokens=50000
        )
        
        api_elapsed = time.time() - api_start
        print(f"[API] {api_elapsed:.1f}s, {response.usage.total_tokens} tokens")
        
        if not response.choices:
            raise ValueError("No response from API")
        
        choice = response.choices[0]
        result_text = choice.message.content
        
        if choice.finish_reason == 'length':
            raise ValueError("Response truncated - increase max_completion_tokens")
        
        if not result_text:
            self.log(f"Empty response content", "ERROR")
            self.log(f"   Finish reason: {choice.finish_reason}", "ERROR")
            raise ValueError(f"Empty response. Finish reason: {choice.finish_reason}")
        
        result_text = result_text.strip()
        self.log(f"   Response length: {len(result_text)} chars")
        
        # Check for refusal
        if any(phrase in result_text.lower() for phrase in ["i cannot", "i'm unable", "i can't", "sorry"]):
            self.log(f"GPT-5-mini appears to be refusing the request", "WARNING")
            self.log(f"   Response: {result_text[:200]}...", "WARNING")
        
        # Remove markdown code blocks if present
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        try:
            result = json.loads(result_text)
            self.log(f"JSON parsed successfully")
        except json.JSONDecodeError as e:
            self.log(f"Invalid JSON response", "ERROR")
            self.log(f"   JSON error: {e}", "ERROR")
            self.log(f"   Response preview: {result_text[:200]}...", "ERROR")
            raise ValueError(f"Invalid JSON response: {e}. Response: {result_text[:200]}")
        
        parse_time = time.time() - parse_start
        
        # Add confidence (GPT-5-mini doesn't provide this, so we estimate)
        result['confidence'] = 0.95
        
        total_elapsed = time.time() - start_time
        
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
