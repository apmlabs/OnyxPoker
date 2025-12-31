"""
Poker screen reader - GPT-5-mini Vision-based detection
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
    def __init__(self, logger=None):
        pyautogui.FAILSAFE = True
        self.vision = VisionDetector(logger=logger)
        self.logger = logger
    
    def log(self, message: str, level: str = "INFO"):
        """Log to GUI if logger provided"""
        if self.logger:
            self.logger(message, level)
    
    def parse_game_state(self, include_decision: bool = False) -> Dict:
        """
        Parse complete game state using GPT-5-mini vision
        
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
            # Timing: GPT-5-mini analysis (this is the big one)
            gpt4o_start = time.time()
            result = self.vision.detect_poker_elements(temp_path, include_decision=include_decision)
            gpt4o_time = time.time() - gpt4o_start
            print(f"[PERF] GPT-5-mini total: {gpt4o_time:.3f}s (API call is 95% of this)")
            
            # Timing: Convert to expected format with null safety
            convert_start = time.time()
            
            if not result:
                self.log("ERROR: GPT-5-mini returned no result", "ERROR")
                return None
            
            state = {
                'hero_cards': result.get('hero_cards', ['??', '??']),
                'community_cards': result.get('community_cards', []),
                'pot': result.get('pot', 0) if result.get('pot') is not None else 0,
                'hero_stack': result.get('hero_stack', 0) if result.get('hero_stack') is not None else 0,
                'stacks': result.get('opponent_stacks', []),
                'to_call': result.get('to_call', 0) if result.get('to_call') is not None else 0,
                'min_raise': result.get('min_raise', 0) if result.get('min_raise') is not None else 0,
                'actions': result.get('available_actions', []),
                'button_positions': result.get('button_positions', {}),
                'confidence': result.get('confidence', 0.0) if result.get('confidence') is not None else 0.0
            }
            
            # Add decision if requested
            if include_decision:
                state['recommended_action'] = result.get('recommended_action', 'fold')
                state['recommended_amount'] = result.get('recommended_amount', 0) if result.get('recommended_amount') is not None else 0
                state['reasoning'] = result.get('reasoning', 'No reasoning provided')
            
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
