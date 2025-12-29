"""
Poker screen reader - OCR and state parsing
Adapted from GitHub skeleton
"""

import pyautogui
from PIL import Image
import pytesseract
import re
import cv2
import numpy as np
from typing import Dict, List, Tuple
import config
from card_matcher import CardMatcher

class PokerScreenReader:
    def __init__(self):
        pyautogui.FAILSAFE = True
        self.card_matcher = CardMatcher()
    
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
    
    def parse_game_state(self) -> Dict:
        """Parse complete game state"""
        return {
            'hero_cards': self.get_hole_cards(),
            'community_cards': self.get_community_cards(),
            'pot': self.get_pot_size(),
            'stacks': self.get_stack_sizes(),
            'actions': self.get_action_buttons(),
        }
    
    def capture_screenshot(self) -> str:
        """Capture full table as base64"""
        import io
        import base64
        img = pyautogui.screenshot(region=config.TABLE_REGION)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
