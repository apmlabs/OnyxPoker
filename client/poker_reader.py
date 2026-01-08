"""
Poker screen reader - AI Vision-based detection
"""

import pyautogui
from PIL import Image
import tempfile
import os
from typing import Dict
import config
from vision_detector import VisionDetector, MODEL

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
        """Parse complete game state using AI vision"""
        import time
        
        t_start = time.time()
        
        # Step 1: Screenshot
        t = time.time()
        img = pyautogui.screenshot(region=config.TABLE_REGION)
        t_screenshot = time.time() - t
        
        # Step 2: Save to temp file
        t = time.time()
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f.name)
            temp_path = f.name
        t_save = time.time() - t
        
        try:
            # Step 3: AI vision (includes encode, api, parse)
            result = self.vision.detect_poker_elements(temp_path, include_decision=include_decision)
            
            if not result:
                self.log("No result from AI", "ERROR")
                return None
            
            # Get AI timings
            ai_timings = result.get('timings', {})
            
            # Build state with null safety
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
                'confidence': result.get('confidence', 0.0) if result.get('confidence') is not None else 0.0,
                'model': result.get('model', MODEL)
            }
            
            if include_decision:
                state['recommended_action'] = result.get('recommended_action', 'fold')
                state['recommended_amount'] = result.get('recommended_amount', 0) if result.get('recommended_amount') is not None else 0
                state['reasoning'] = result.get('reasoning', '')
            
            # Calculate total time
            t_total = time.time() - t_start
            
            # Log timing breakdown
            self.log(f"Timing: screenshot={t_screenshot:.2f}s save={t_save:.2f}s encode={ai_timings.get('encode', 0):.2f}s api={ai_timings.get('api', 0):.1f}s parse={ai_timings.get('parse', 0):.2f}s total={t_total:.1f}s")
            
            return state
            
        except Exception as e:
            self.log(f"Parse error: {e}", "ERROR")
            return None
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def capture_screenshot(self) -> str:
        """Capture full table as base64"""
        img = pyautogui.screenshot(region=config.TABLE_REGION)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
