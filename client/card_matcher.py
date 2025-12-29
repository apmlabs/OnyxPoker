"""
Card Recognition using Template Matching
Matches cards from screenshots against generated templates
"""

import cv2
import numpy as np
import os
from typing import List, Tuple, Optional

class CardMatcher:
    def __init__(self, template_dir='templates'):
        self.template_dir = template_dir
        self.templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load all card templates"""
        if not os.path.exists(self.template_dir):
            print(f"⚠️ Template directory not found: {self.template_dir}")
            return
        
        for filename in os.listdir(self.template_dir):
            if filename.endswith('.png'):
                card_name = filename[:-4]  # Remove .png
                template_path = os.path.join(self.template_dir, filename)
                template = cv2.imread(template_path)
                if template is not None:
                    self.templates[card_name] = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        print(f"✅ Loaded {len(self.templates)} card templates")
    
    def match_card(self, card_image: np.ndarray, threshold=0.7) -> Tuple[Optional[str], float]:
        """
        Match a card image against templates
        Returns: (card_name, confidence) or (None, 0.0)
        """
        if len(self.templates) == 0:
            return None, 0.0
        
        # Convert to grayscale
        if len(card_image.shape) == 3:
            gray_card = cv2.cvtColor(card_image, cv2.COLOR_BGR2GRAY)
        else:
            gray_card = card_image
        
        best_match = None
        best_score = 0.0
        
        # Try each template
        for card_name, template in self.templates.items():
            # Resize template to match card image size
            template_resized = cv2.resize(template, (gray_card.shape[1], gray_card.shape[0]))
            
            # Template matching
            result = cv2.matchTemplate(gray_card, template_resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            if max_val > best_score:
                best_score = max_val
                best_match = card_name
        
        if best_score >= threshold:
            return best_match, best_score
        else:
            return None, best_score
    
    def match_cards(self, card_images: List[np.ndarray]) -> List[Tuple[Optional[str], float]]:
        """Match multiple card images"""
        return [self.match_card(img) for img in card_images]
    
    def format_card(self, card_name: Optional[str]) -> str:
        """Format card name for display (e.g., 'As' -> 'A♠')"""
        if not card_name:
            return '??'
        
        suit_symbols = {'s': '♠', 'h': '♥', 'd': '♦', 'c': '♣'}
        rank = card_name[:-1]
        suit = card_name[-1]
        return f"{rank}{suit_symbols.get(suit, suit)}"

if __name__ == '__main__':
    # Test card matching
    matcher = CardMatcher()
    print(f"Ready to match cards with {len(matcher.templates)} templates")
