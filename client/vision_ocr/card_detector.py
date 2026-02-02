"""
Card detector using OpenCV template matching.
Based on EdjeElectronics approach with brightness-based card finding.
"""
import cv2
import numpy as np
import os

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')

# Standard dimensions for templates (actual template sizes)
RANK_WIDTH = 40
RANK_HEIGHT = 45
SUIT_WIDTH = 30
SUIT_HEIGHT = 30

# Thresholds for matching
RANK_DIFF_MAX = 3500
SUIT_DIFF_MAX = 2000

class CardDetector:
    def __init__(self):
        self.rank_templates = {}
        self.suit_templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load rank and suit templates."""
        for f in os.listdir(TEMPLATE_DIR):
            path = os.path.join(TEMPLATE_DIR, f)
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            if f.startswith('rank_') and not '_' in f[5:-4]:
                name = f[5:-4]  # rank_10.png -> 10
                self.rank_templates[name] = img
            elif f.startswith('suit_') and not '_' in f[5:-4]:
                name = f[5:-4]  # suit_h.png -> h
                self.suit_templates[name] = img
    
    def detect(self, img_path):
        """Detect cards in image."""
        img = cv2.imread(img_path)
        if img is None:
            return {'hero': [], 'board': []}
        
        # Find hero cards
        hero_cards = []
        hero_regions = self.find_hero_cards(img)
        for x, y, w, h in hero_regions:
            card_img = img[y:y+h, x:x+w]
            rank, suit = self.identify_card(card_img)
            if rank and suit:
                hero_cards.append(f"{rank}{suit}")
        
        # Find board cards
        board_cards = []
        board_regions = self.find_board_cards(img)
        for x, y, w, h in board_regions:
            card_img = img[y:y+h, x:x+w]
            rank, suit = self.identify_card(card_img)
            if rank and suit:
                board_cards.append(f"{rank}{suit}")
        
        return {'hero': hero_cards, 'board': board_cards}
    
    def find_hero_cards(self, img):
        """Find hero cards using contour detection with morphological closing."""
        h, w = img.shape[:2]
        
        # Hero cards are at bottom center
        y_start = int(h * 0.61)
        y_end = int(h * 0.78)
        x_start = int(w * 0.38)
        x_end = int(w * 0.58)
        
        hero_region = img[y_start:y_end, x_start:x_end]
        
        # Preprocess: grayscale → blur → threshold
        gray = cv2.cvtColor(hero_region, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Binary threshold to get white cards
        _, thresh = cv2.threshold(blur, 120, 255, cv2.THRESH_BINARY)
        
        # Morphological closing to fill card interiors (small kernel to keep cards separate)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter for card-sized contours
        regions = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 5000 < area < 50000:  # Card size range (increased min from 2000)
                x, y, w_cnt, h_cnt = cv2.boundingRect(cnt)
                # Check aspect ratio (cards are roughly square to slightly tall)
                if 0.6 < w_cnt / h_cnt < 1.4:
                    regions.append((
                        x_start + x,
                        y_start + y,
                        w_cnt,
                        h_cnt
                    ))
        
        # Sort left to right
        regions.sort(key=lambda r: r[0])
        return regions[:2]  # Max 2 hero cards
    
    def find_board_cards(self, img):
        """Find board cards using contour detection with morphological closing."""
        h, w = img.shape[:2]
        
        # Board area
        y_start = int(h * 0.33)
        y_end = int(h * 0.52)
        x_start = int(w * 0.28)
        x_end = int(w * 0.72)
        
        board_region = img[y_start:y_end, x_start:x_end]
        
        # Preprocess: grayscale → blur → threshold
        gray = cv2.cvtColor(board_region, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Binary threshold to get white cards
        _, thresh = cv2.threshold(blur, 120, 255, cv2.THRESH_BINARY)
        
        # Morphological closing to fill card interiors
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter for card-sized contours
        regions = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 5000 < area < 50000:  # Card size range
                x, y, w_cnt, h_cnt = cv2.boundingRect(cnt)
                # Check aspect ratio
                if 0.6 < w_cnt / h_cnt < 1.4:
                    regions.append((
                        x_start + x,
                        y_start + y,
                        w_cnt,
                        h_cnt
                    ))
        
        # Sort left to right
        regions.sort(key=lambda r: r[0])
        return regions[:5]  # Max 5 board cards
    
    def identify_card(self, card_img):
        """Identify rank and suit using template matching with binary conversion."""
        h, w = card_img.shape[:2]
        if h < 50 or w < 50:
            return None, None
        
        # Convert to grayscale
        gray = cv2.cvtColor(card_img, cv2.COLOR_BGR2GRAY)
        
        # Extract top-left corner - use more of the card to capture symbols
        corner_h = int(h * 0.50)  # Top 50% of card (was 35%)
        corner_w = int(w * 0.40)  # Left 40% of card (was 30%)
        corner = gray[0:corner_h, 0:corner_w]
        
        # Threshold to binary - use FIXED threshold of 127 (mid-gray)
        _, corner_thresh = cv2.threshold(corner, 127, 255, cv2.THRESH_BINARY)
        
        # INVERT so symbols are BLACK (0) on WHITE (255) background - matches templates
        corner_thresh = cv2.bitwise_not(corner_thresh)
        
        # Split corner into rank (top 55%) and suit (bottom 45%)
        # Adjusted because rank is usually larger than suit
        split_point = int(corner_h * 0.55)
        rank_region = corner_thresh[0:split_point, :]
        suit_region = corner_thresh[split_point:, :]
        
        # Match rank using template matching
        best_rank = None
        best_rank_score = -1
        for name, template in self.rank_templates.items():
            # Convert template to grayscale if needed
            if len(template.shape) == 3:
                template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # Threshold template with SAME fixed threshold
            _, template_thresh = cv2.threshold(template, 127, 255, cv2.THRESH_BINARY)
            
            # Resize template to match region size
            template_resized = cv2.resize(template_thresh, (rank_region.shape[1], rank_region.shape[0]))
            
            # Template matching with normalized correlation
            result = cv2.matchTemplate(rank_region, template_resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            if max_val > best_rank_score:
                best_rank_score = max_val
                best_rank = name
        
        # Match suit
        best_suit = None
        best_suit_score = -1
        for name, template in self.suit_templates.items():
            # Convert template to grayscale if needed
            if len(template.shape) == 3:
                template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # Threshold template with SAME fixed threshold
            _, template_thresh = cv2.threshold(template, 127, 255, cv2.THRESH_BINARY)
            
            # Resize template to match region size
            template_resized = cv2.resize(template_thresh, (suit_region.shape[1], suit_region.shape[0]))
            
            # Template matching
            result = cv2.matchTemplate(suit_region, template_resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            if max_val > best_suit_score:
                best_suit_score = max_val
                best_suit = name
        
        # Lower threshold since we're resizing significantly
        if best_rank_score < 0.15:
            return None, None
        if best_suit_score < 0.15:
            return None, None
        
        return best_rank, best_suit

if __name__ == '__main__':
    import sys
    detector = CardDetector()
    
    if len(sys.argv) > 1:
        result = detector.detect(sys.argv[1])
        print(f"Hero: {result['hero']}")
        print(f"Board: {result['board']}")
    else:
        # Test on all screenshots
        import glob
        screenshots = sorted(glob.glob('/home/ubuntu/mcpprojects/onyxpoker/server/uploads/202601*.png'))[:10]
        for path in screenshots:
            result = detector.detect(path)
            print(f"{os.path.basename(path)}: Hero={result['hero']} Board={result['board']}")
