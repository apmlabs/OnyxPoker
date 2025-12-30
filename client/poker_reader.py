"""
Poker screen reader - GPT-4o Vision-based detection
Replaces OCR with AI that understands poker
"""

import pyautogui
from PIL import Image
import tempfile
import os
import io
import base64
from typing import Dict
import config
from vision_detector import VisionDetector

class PokerScreenReader:
    def __init__(self):
        pyautogui.FAILSAFE = True
        self.vision = VisionDetector()
    
    def parse_game_state(self, include_decision: bool = False) -> Dict:
        """
        Parse complete game state using GPT-4o vision
        
        Args:
            include_decision: If True, also get poker decision recommendation
        
        Returns:
            Dict with game state and optional decision
        """
        # Capture full table screenshot
        img = pyautogui.screenshot(region=config.TABLE_REGION)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f.name)
            temp_path = f.name
        
        try:
            # Use GPT-4o to analyze (with optional decision)
            result = self.vision.detect_poker_elements(temp_path, include_decision=include_decision)
            
            # Convert to expected format
            state = {
                'hero_cards': result.get('hero_cards', ['??', '??']),
                'community_cards': result.get('community_cards', []),
                'pot': result.get('pot', 0),
                'hero_stack': result.get('hero_stack', 0),
                'stacks': result.get('opponent_stacks', []),
                'to_call': result.get('to_call', 0),
                'min_raise': result.get('min_raise', 0),
                'actions': result.get('available_actions', []),
                'button_positions': result.get('button_positions', {}),
                'confidence': result.get('confidence', 0.0)
            }
            
            # Add decision if requested
            if include_decision:
                state['recommended_action'] = result.get('recommended_action')
                state['recommended_amount'] = result.get('recommended_amount')
                state['reasoning'] = result.get('reasoning')
            
            return state
        finally:
            # Cleanup temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def capture_screenshot(self) -> str:
        """Capture full table as base64"""
        img = pyautogui.screenshot(region=config.TABLE_REGION)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
