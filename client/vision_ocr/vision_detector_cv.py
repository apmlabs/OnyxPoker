"""
OpenCV-based vision detector - replaces GPT vision.
Target: <0.5s vs GPT's 5.5s
"""
import cv2
import numpy as np
import pytesseract
import re
from typing import Dict, Any, List
from card_detector import CardDetector


class VisionDetectorCV:
    def __init__(self):
        self.card_detector = CardDetector()
        # Seat regions: (name_y1%, name_y2%, name_x1%, name_x2%)
        self.seats = [
            (0.230, 0.266, 0.036, 0.160),  # seat1 top-left
            (0.144, 0.180, 0.428, 0.516),  # seat2 top-center
            (0.230, 0.266, 0.846, 0.975),  # seat3 top-right
            (0.517, 0.553, 0.877, 0.965),  # seat4 right
            (0.510, 0.546, 0.015, 0.129),  # seat6 left
        ]
    
    def detect_table(self, screenshot_path: str) -> Dict[str, Any]:
        img = cv2.imread(screenshot_path)
        if img is None:
            return self._empty_result()
        
        h, w = img.shape[:2]
        
        # Cards (fast - template matching)
        cards = self.card_detector.detect(screenshot_path)
        hero = cards.get('hero', [])
        board = cards.get('board', [])
        
        # OCR regions
        pot = self._ocr_amount(img[int(h*0.323):int(h*0.359), int(w*0.449):int(w*0.542)])
        to_call = self._ocr_to_call(img[int(h*0.862):int(h*0.970), int(w*0.516):int(w*0.774)])
        opponents = self._detect_opponents(img, h, w)
        
        return {
            'hero_cards': hero,  # Already in short format (3d, Ac)
            'community_cards': board,  # Already in short format
            'pot': pot,
            'hero_stack': 0.0,
            'to_call': to_call,
            'big_blind': 0.02,
            'opponents': opponents
        }
    
    def _ocr_amount(self, region) -> float:
        if region.size == 0:
            return 0.0
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray, config='--psm 6').strip()
        match = re.search(r'[€£]?([\d.]+)', text.replace('A', '4').replace('?', '2'))
        return float(match.group(1)) if match else 0.0
    
    def _ocr_to_call(self, region) -> float:
        if region.size == 0:
            return 0.0
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray, config='--psm 6').strip().lower()
        if 'call' in text:
            match = re.search(r'call[^\d€£]*([\d.]+)', text)
            return float(match.group(1)) if match else 0.0
        return 0.0
    
    def _detect_opponents(self, img, h, w) -> List[Dict]:
        opponents = []
        for ny1, ny2, nx1, nx2 in self.seats:
            region = img[int(h*ny1):int(h*ny2), int(w*nx1):int(w*nx2)]
            if region.size == 0:
                continue
            
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray, config='--psm 7').strip()
            name = re.sub(r'[^\w\d_]', '', text)
            
            if not name or len(name) < 2:
                continue
            
            # Check for card backs (dark red)
            card_y1 = max(0, int(h*ny1) - int(h * 0.06))
            card_region = img[card_y1:int(h*ny1), int(w*nx1):int(w*nx2)]
            has_cards = False
            if card_region.size > 0:
                hsv = cv2.cvtColor(card_region, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, (0, 50, 30), (20, 255, 150))
                has_cards = cv2.countNonZero(mask) > 300
            
            opponents.append({'name': name, 'has_cards': has_cards})
        return opponents
    
    def _to_short(self, card: str) -> str:
        if not card:
            return ''
        suit_map = {'♥': 'h', '♦': 'd', '♠': 's', '♣': 'c'}
        rank = card[:-1]
        suit = suit_map.get(card[-1], '?')
        if rank == '10':
            rank = 'T'
        return f"{rank}{suit}"
    
    def _empty_result(self) -> Dict[str, Any]:
        return {
            'hero_cards': [], 'community_cards': [], 'pot': 0.0,
            'hero_stack': 0.0, 'to_call': 0.0, 'big_blind': 0.02, 'opponents': []
        }


if __name__ == '__main__':
    import sys, time, json
    detector = VisionDetectorCV()
    test_img = sys.argv[1] if len(sys.argv) > 1 else '../../server/uploads/20260120_134214.png'
    start = time.time()
    result = detector.detect_table(test_img)
    print(json.dumps(result, indent=2))
    print(f"\nTime: {time.time()-start:.2f}s")
