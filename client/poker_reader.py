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
        import time
        
        # Timing: Screenshot capture
        capture_start = time.time()
        img = pyautogui.screenshot(region=config.TABLE_REGION)
        capture_time = time.time() - capture_start
        print(f"[PERF] Screenshot capture: {capture_time:.3f}s")
        
        # Timing: Save to temp file
        save_start = time.time()
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f.name)
            temp_path = f.name
        save_time = time.time() - save_start
        print(f"[PERF] Save to temp file: {save_time:.3f}s")
        
        try:
            # Timing: GPT-4o analysis (this is the big one)
            gpt4o_start = time.time()
            result = self.vision.detect_poker_elements(temp_path, include_decision=include_decision)
            gpt4o_time = time.time() - gpt4o_start
            print(f"[PERF] GPT-4o total: {gpt4o_time:.3f}s (API call is 95% of this)")
            
            # Timing: Convert to expected format
            convert_start = time.time()
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
            
            convert_time = time.time() - convert_start
            print(f"[PERF] Convert format: {convert_time:.3f}s")
            
            # Performance summary
            total_time = capture_time + save_time + gpt4o_time + convert_time
            print(f"[PERF] TOTAL: {total_time:.3f}s (capture={capture_time:.3f}s, save={save_time:.3f}s, gpt4o={gpt4o_time:.3f}s, convert={convert_time:.3f}s)")
            
            return state
        finally:
            # Cleanup temp file
            cleanup_start = time.time()
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            cleanup_time = time.time() - cleanup_start
            print(f"[PERF] Cleanup: {cleanup_time:.3f}s")
    
    def capture_screenshot(self) -> str:
        """Capture full table as base64"""
        img = pyautogui.screenshot(region=config.TABLE_REGION)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
