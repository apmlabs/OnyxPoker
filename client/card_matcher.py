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
        self.real_template_dir = os.path.join(template_dir, 'real')
        self.templates = {}
        self.real_templates = {}
        os.makedirs(self.real_template_dir, exist_ok=True)
        self._load_templates()
    
    def _load_templates(self):
        """Load all card templates (real first, then synthetic)"""
        # Load real templates (captured from actual gameplay)
        if os.path.exists(self.real_template_dir):
            for filename in os.listdir(self.real_template_dir):
                if filename.endswith('.png'):
                    card_name = filename[:-4]  # Remove .png
                    template_path = os.path.join(self.real_template_dir, filename)
                    template = cv2.imread(template_path)
                    if template is not None:
                        self.real_templates[card_name] = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # Load synthetic templates (fallback)
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
        
        print(f"✅ Loaded {len(self.real_templates)} real + {len(self.templates)} synthetic templates")
    
    def match_card(self, card_image: np.ndarray, threshold=0.7) -> Tuple[Optional[str], float]:
        """
        Match a card image against templates (real first, then synthetic)
        Returns: (card_name, confidence) or (None, 0.0)
        """
        # Convert to grayscale
        if len(card_image.shape) == 3:
            gray_card = cv2.cvtColor(card_image, cv2.COLOR_BGR2GRAY)
        else:
            gray_card = card_image
        
        best_match = None
        best_score = 0.0
        
        # Try real templates first (higher priority)
        for card_name, template in self.real_templates.items():
            template_resized = cv2.resize(template, (gray_card.shape[1], gray_card.shape[0]))
            result = cv2.matchTemplate(gray_card, template_resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            if max_val > best_score:
                best_score = max_val
                best_match = card_name
        
        # If real templates didn't match well, try synthetic
        if best_score < threshold:
            for card_name, template in self.templates.items():
                template_resized = cv2.resize(template, (gray_card.shape[1], gray_card.shape[0]))
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
    
    def save_real_card(self, card_image: np.ndarray, card_name: str):
        """Save a real card image as a template for future use"""
        if len(card_image.shape) == 3:
            gray_card = cv2.cvtColor(card_image, cv2.COLOR_BGR2GRAY)
        else:
            gray_card = card_image
        
        # Save to real templates directory
        filepath = os.path.join(self.real_template_dir, f"{card_name}.png")
        cv2.imwrite(filepath, gray_card)
        
        # Add to real templates dictionary
        self.real_templates[card_name] = gray_card
        
        print(f"✅ Saved real card template: {card_name}")
        return True

if __name__ == '__main__':
    # Test card matching
    matcher = CardMatcher()
    print(f"Ready to match cards with {len(matcher.templates)} templates")
