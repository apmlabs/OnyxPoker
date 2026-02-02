"""
OpenCV + Tesseract based vision detector for PokerStars.
Target: <2s per screenshot, no GPT fallback.
"""

import cv2
import numpy as np
import pytesseract
import json
import os
import re
from pathlib import Path

TEMPLATE_PATH = Path(__file__).parent / "template_pokerstars_6max.json"

# Card rank/suit mappings
RANKS = {'A': 'A', 'K': 'K', 'Q': 'Q', 'J': 'J', '10': 'T', '9': '9', '8': '8', '7': '7', '6': '6', '5': '5', '4': '4', '3': '3', '2': '2'}
SUITS = {'♠': 's', '♥': 'h', '♦': 'd', '♣': 'c'}

class VisionDetector:
    def __init__(self, template_path=None):
        self.template = self._load_template(template_path or TEMPLATE_PATH)
        self.debug_mode = False
        self.debug_dir = None
        
    def _load_template(self, path):
        with open(path) as f:
            return json.load(f)
    
    def _crop_roi(self, img, roi):
        """Crop ROI from image. ROI is [x%, y%, w%, h%]."""
        h, w = img.shape[:2]
        x1 = int(roi[0] * w)
        y1 = int(roi[1] * h)
        x2 = int((roi[0] + roi[2]) * w)
        y2 = int((roi[1] + roi[3]) * h)
        return img[y1:y2, x1:x2]
    
    def _preprocess_for_ocr(self, img, field_type='text'):
        """Preprocess image for OCR based on field type."""
        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        # Resize 2x for better OCR
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        if field_type == 'money':
            # For money: threshold to get white text on black
            _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        elif field_type == 'name':
            # For names: adaptive threshold
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                          cv2.THRESH_BINARY, 11, 2)
        else:
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        return thresh
    
    def _ocr_text(self, img, whitelist=None, field_type='text'):
        """Run OCR on preprocessed image."""
        processed = self._preprocess_for_ocr(img, field_type)
        
        config = '--psm 7'  # Single line
        if whitelist:
            config += f' -c tessedit_char_whitelist={whitelist}'
        
        text = pytesseract.image_to_string(processed, config=config).strip()
        return text
    
    def _parse_money(self, text):
        """Parse money string like '€5.98' or '0.42' to float."""
        # Remove currency symbols and whitespace
        clean = re.sub(r'[€$£\s]', '', text)
        # Find number pattern
        match = re.search(r'(\d+\.?\d*)', clean)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
        return None
    
    def _detect_card_color(self, card_img):
        """Detect if card has red or black suit based on color."""
        hsv = cv2.cvtColor(card_img, cv2.COLOR_BGR2HSV)
        
        # Red mask (hearts/diamonds)
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_pixels = cv2.countNonZero(mask1) + cv2.countNonZero(mask2)
        
        return 'red' if red_pixels > 50 else 'black'
    
    def _read_card(self, card_img):
        """Read a single card image and return rank+suit like 'As' or 'Th'."""
        if card_img is None or card_img.size == 0:
            return None
        
        h, w = card_img.shape[:2]
        if h < 10 or w < 10:
            return None
        
        # Check if card is present (not just green felt)
        gray = cv2.cvtColor(card_img, cv2.COLOR_BGR2GRAY)
        if np.mean(gray) < 50:  # Too dark, probably no card
            return None
        
        # Get color for suit
        color = self._detect_card_color(card_img)
        
        # Crop top-left corner for rank
        rank_roi = card_img[2:int(h*0.4), 2:int(w*0.5)]
        
        # OCR the rank
        rank_text = self._ocr_text(rank_roi, whitelist='AKQJ1098765432', field_type='text')
        rank_text = rank_text.upper().replace('O', '0').replace('I', '1')
        
        # Map to standard rank
        rank = None
        for r in ['10', 'A', 'K', 'Q', 'J', '9', '8', '7', '6', '5', '4', '3', '2']:
            if r in rank_text:
                rank = RANKS.get(r, r)
                break
        
        if not rank:
            return None
        
        # Determine suit from color + shape analysis
        # For now, use color-based heuristic
        # Red = hearts or diamonds, Black = spades or clubs
        # We'll need suit templates for accurate detection
        suit = self._detect_suit(card_img, color)
        
        return f"{rank}{suit}" if suit else None
    
    def _detect_suit(self, card_img, color):
        """Detect suit from card image."""
        h, w = card_img.shape[:2]
        
        # Crop suit area (below rank, left side)
        suit_roi = card_img[int(h*0.35):int(h*0.65), 2:int(w*0.45)]
        
        if color == 'red':
            # Distinguish hearts vs diamonds by shape
            # Hearts are more rounded at top, diamonds are pointed
            gray = cv2.cvtColor(suit_roi, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                cnt = max(contours, key=cv2.contourArea)
                # Approximate shape
                approx = cv2.approxPolyDP(cnt, 0.04 * cv2.arcLength(cnt, True), True)
                # Diamonds tend to have 4 vertices, hearts more
                if len(approx) <= 5:
                    return 'd'
                else:
                    return 'h'
            return 'h'  # Default to hearts
        else:
            # Distinguish spades vs clubs
            # Spades have pointed top, clubs have rounded lobes
            gray = cv2.cvtColor(suit_roi, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
            
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                cnt = max(contours, key=cv2.contourArea)
                approx = cv2.approxPolyDP(cnt, 0.04 * cv2.arcLength(cnt, True), True)
                # Clubs tend to have more complex shape
                if len(approx) > 6:
                    return 'c'
                else:
                    return 's'
            return 's'  # Default to spades
    
    def _detect_dealer_button(self, img):
        """Find dealer button position using template matching."""
        # The dealer button is a small circular "D" icon
        # For now, check brightness in each seat's dealer search ROI
        
        best_seat = None
        best_score = 0
        
        for seat_id, seat in self.template['seats'].items():
            roi = seat.get('dealer_search_roi')
            if not roi:
                continue
            
            crop = self._crop_roi(img, roi)
            if crop.size == 0:
                continue
            
            # Convert to grayscale and look for bright circular region
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            
            # Dealer button is typically bright (white/yellow)
            bright_pixels = np.sum(gray > 200)
            
            if bright_pixels > best_score:
                best_score = bright_pixels
                best_seat = int(seat_id)
        
        return best_seat if best_score > 50 else None
    
    def _has_cards(self, img, seat_roi):
        """Check if seat has face-down cards (still in hand)."""
        crop = self._crop_roi(img, seat_roi)
        if crop.size == 0:
            return False
        
        # Face-down cards are dark red/maroon
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        
        # Dark red range
        lower = np.array([0, 50, 30])
        upper = np.array([20, 255, 150])
        mask = cv2.inRange(hsv, lower, upper)
        
        return cv2.countNonZero(mask) > 100
    
    def detect(self, image_path):
        """
        Main detection function. Returns dict with all table info.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            return {'error': f'Could not load image: {image_path}'}
        
        result = {
            'hero_cards': [],
            'board': [],
            'pot': None,
            'players': [],
            'dealer_seat': None,
            'to_call': None,
            'confidence': {},
            'errors': []
        }
        
        # 1. Read pot
        try:
            pot_crop = self._crop_roi(img, self.template['table']['pot_roi'])
            pot_text = self._ocr_text(pot_crop, whitelist='0123456789.€Pot:', field_type='money')
            result['pot'] = self._parse_money(pot_text)
            result['confidence']['pot'] = 0.9 if result['pot'] else 0.0
        except Exception as e:
            result['errors'].append(f'pot: {e}')
        
        # 2. Read hero cards
        try:
            for i, card_roi in enumerate(self.template['card_positions']['hero']):
                card_crop = self._crop_roi(img, card_roi)
                card = self._read_card(card_crop)
                if card:
                    result['hero_cards'].append(card)
            result['confidence']['hero_cards'] = 0.9 if len(result['hero_cards']) == 2 else 0.5
        except Exception as e:
            result['errors'].append(f'hero_cards: {e}')
        
        # 3. Read board cards
        try:
            for i, card_roi in enumerate(self.template['card_positions']['board']):
                card_crop = self._crop_roi(img, card_roi)
                card = self._read_card(card_crop)
                if card:
                    result['board'].append(card)
            result['confidence']['board'] = 0.9 if result['board'] else 0.5
        except Exception as e:
            result['errors'].append(f'board: {e}')
        
        # 4. Read players
        try:
            for seat_id, seat in self.template['seats'].items():
                player = {'seat': int(seat_id), 'name': None, 'stack': None, 'has_cards': False}
                
                # Name
                name_crop = self._crop_roi(img, seat['name_roi'])
                name_text = self._ocr_text(name_crop, field_type='name')
                player['name'] = name_text if len(name_text) > 1 else None
                
                # Stack
                stack_crop = self._crop_roi(img, seat['stack_roi'])
                stack_text = self._ocr_text(stack_crop, whitelist='0123456789.€', field_type='money')
                player['stack'] = self._parse_money(stack_text)
                
                # Has cards (for non-hero seats)
                if not seat.get('is_hero'):
                    player['has_cards'] = self._has_cards(img, seat['cards_roi'])
                else:
                    player['has_cards'] = len(result['hero_cards']) > 0
                    player['is_hero'] = True
                
                result['players'].append(player)
        except Exception as e:
            result['errors'].append(f'players: {e}')
        
        # 5. Dealer button
        try:
            result['dealer_seat'] = self._detect_dealer_button(img)
            result['confidence']['dealer'] = 0.9 if result['dealer_seat'] else 0.0
        except Exception as e:
            result['errors'].append(f'dealer: {e}')
        
        # 6. Action buttons / to_call
        try:
            action_crop = self._crop_roi(img, self.template['table']['action_buttons_roi'])
            action_text = self._ocr_text(action_crop, field_type='text')
            
            # Look for "Call €X.XX" pattern
            call_match = re.search(r'[Cc]all.*?(\d+\.?\d*)', action_text)
            if call_match:
                result['to_call'] = float(call_match.group(1))
            elif 'check' in action_text.lower():
                result['to_call'] = 0
        except Exception as e:
            result['errors'].append(f'action: {e}')
        
        return result


def test_detector(image_path):
    """Test the detector on a single image."""
    import time
    
    detector = VisionDetector()
    
    start = time.time()
    result = detector.detect(image_path)
    elapsed = time.time() - start
    
    print(f"Detection time: {elapsed:.2f}s")
    print(f"Hero cards: {result['hero_cards']}")
    print(f"Board: {result['board']}")
    print(f"Pot: {result['pot']}")
    print(f"Dealer seat: {result['dealer_seat']}")
    print(f"To call: {result['to_call']}")
    print(f"Players:")
    for p in result['players']:
        print(f"  Seat {p['seat']}: {p['name']} - €{p['stack']} - cards: {p['has_cards']}")
    if result['errors']:
        print(f"Errors: {result['errors']}")
    
    return result


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        test_detector(sys.argv[1])
    else:
        # Test on a sample image
        test_path = "/home/ubuntu/mcpprojects/onyxpoker/server/uploads/20260120_134214.png"
        test_detector(test_path)
