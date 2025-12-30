"""
Poker screen reader - GPT-4o Vision-based detection
Replaces OCR with AI that understands poker
"""

import pyautogui
from PIL import Image
import tempfile
import os
from typing import Dict, List, Tuple
import config
from vision_detector import VisionDetector

class PokerScreenReader:
    def __init__(self):
        pyautogui.FAILSAFE = True
        self.vision = VisionDetector()
    
    
    def capture_region(self, region: Tuple[int, int, int, int]) -> Image.Image:
        """Capture screen region relative to table"""
        table_x, table_y, _, _ = config.TABLE_REGION
        x, y, w, h = region
        abs_region = (table_x + x, table_y + y, w, h)
        return pyautogui.screenshot(region=abs_region)
    
    def ocr_text(self, img: Image.Image, whitelist: str = "0123456789") -> str:
        """OCR with character whitelist"""
        gray = img.convert('L')
        custom_config = f"--psm 7 -c tessedit_char_whitelist={whitelist}"
        text = pytesseract.image_to_string(gray, config=custom_config)
        return text.strip()
    
    def parse_int(self, img: Image.Image) -> int:
        """Parse integer from image"""
        text = self.ocr_text(img)
        match = re.search(r'\d+', text)
        return int(match.group()) if match else 0
    
    def get_hole_cards(self) -> List[str]:
        """Get hero's cards using template matching"""
        cards = []
        for region in config.HOLE_CARD_REGIONS:
            img = self.capture_region(region)
            # Convert PIL to OpenCV format
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            card_name, confidence = self.card_matcher.match_card(img_cv)
            if card_name and confidence > 0.7:
                cards.append(self.card_matcher.format_card(card_name))
            else:
                cards.append('??')
        return cards
    
    def get_community_cards(self) -> List[str]:
        """Get board cards using template matching"""
        if not hasattr(config, 'COMMUNITY_CARD_REGIONS'):
            return []
        
        cards = []
        for region in config.COMMUNITY_CARD_REGIONS:
            img = self.capture_region(region)
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            card_name, confidence = self.card_matcher.match_card(img_cv)
            if card_name and confidence > 0.7:
                cards.append(self.card_matcher.format_card(card_name))
        return cards
    
    def get_pot_size(self) -> int:
        """OCR pot size"""
        img = self.capture_region(config.POT_REGION)
        return self.parse_int(img)
    
    def get_stack_sizes(self) -> List[int]:
        """OCR all stack sizes"""
        stacks = []
        for reg in config.STACK_REGIONS:
            if reg == (0, 0, 0, 0):
                stacks.append(0)
            else:
                img = self.capture_region(reg)
                stacks.append(self.parse_int(img))
        return stacks
    
    def get_action_buttons(self) -> Dict[str, str]:
        """OCR action button labels"""
        actions = {}
        for name, reg in config.BUTTON_REGIONS.items():
            img = self.capture_region(reg)
            label = self.ocr_text(img, whitelist="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ")
            actions[name] = label
        return actions
    
    def is_hero_turn(self) -> bool:
        """Check if it's hero's turn"""
        actions = self.get_action_buttons()
        return bool(actions.get('call', '').strip())
    
    def parse_game_state(self, include_decision: bool = False) -> Dict:
        """
        Parse complete game state using GPT-4o vision
        
        Args:
            include_decision: If True, also get poker decision recommendation
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
    
    def is_hero_turn(self) -> bool:
        """Check if it's hero's turn"""
        state = self.parse_game_state()
        actions = state.get('actions', [])
        return len(actions) > 0 and 'fold' in [a.lower() for a in actions]

    def capture_screenshot(self) -> str:
        """Capture full table as base64"""
        import io
        import base64
        img = pyautogui.screenshot(region=config.TABLE_REGION)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
