"""
Automatic window detection and calibration
Finds PokerStars window and poker table elements
"""

import pyautogui
import pygetwindow as gw
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict
import logging

logger = logging.getLogger(__name__)

class WindowDetector:
    """Auto-detect poker windows and elements"""
    
    def __init__(self):
        self.poker_window = None
        self.table_region = None
        self.can_capture_background = self._test_background_capture()
    
    def _test_background_capture(self) -> bool:
        """Test if we can capture background windows"""
        try:
            # PyAutoGUI can't capture background windows on Windows
            # Would need win32gui for that
            return False
        except:
            return False
    
    def find_poker_windows(self) -> List[Dict]:
        """Find all windows (not just poker-related)"""
        windows = []
        
        for window in gw.getAllWindows():
            # Skip empty titles and very small windows
            if window.title and window.width > 400 and window.height > 300:
                windows.append({
                    'title': window.title,
                    'left': window.left,
                    'top': window.top,
                    'width': window.width,
                    'height': window.height,
                        'window': window
                    })
        
        return windows
    
    def select_window(self, windows: List[Dict]) -> Optional[Dict]:
        """Let user select which window to use"""
        if not windows:
            return None
        
        # If only one, use it
        if len(windows) == 1:
            return windows[0]
        
        # Multiple windows - return list for UI to handle
        return windows
    
    def activate_window(self, window_info: Dict) -> bool:
        """Bring window to foreground"""
        try:
            window = window_info['window']
            if not self.can_capture_background:
                window.activate()
                pyautogui.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Failed to activate window: {e}")
            return False
    
    def capture_window(self, window_info: Dict) -> Image.Image:
        """Capture window screenshot"""
        region = (
            window_info['left'],
            window_info['top'],
            window_info['width'],
            window_info['height']
        )
        return pyautogui.screenshot(region=region)
    
    def detect_poker_elements(self, img: Image.Image) -> Dict:
        """Detect poker table elements using OCR with spatial reasoning"""
        
        # Convert to OpenCV format
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        height, width = img_cv.shape[:2]
        
        elements = {
            'pot_region': None,
            'button_regions': {},
            'card_regions': [],
            'stack_regions': [],
            'confidence': 0.0
        }
        
        # Run OCR to get all text with bounding boxes
        ocr_data = pytesseract.image_to_data(img_cv, output_type=pytesseract.Output.DICT)
        
        # Collect all detected numbers (potential pot/stacks)
        numbers = []
        
        for i, text in enumerate(ocr_data['text']):
            if not text.strip():
                continue
                
            text_clean = text.strip()
            text_lower = text_clean.lower()
            x, y, w, h = (ocr_data['left'][i], ocr_data['top'][i], 
                         ocr_data['width'][i], ocr_data['height'][i])
            
            # Calculate relative position (0-1)
            rel_x = x / width
            rel_y = y / height
            
            # Detect buttons by text (should be in bottom 20%)
            if rel_y > 0.8:  # Bottom 20%
                button_padding = 20
                btn_x = max(0, x - button_padding)
                btn_y = max(0, y - button_padding)
                btn_w = w + button_padding * 2
                btn_h = h + button_padding * 2
                
                if 'fold' in text_lower:
                    elements['button_regions']['fold'] = (btn_x, btn_y, btn_w, btn_h)
                    elements['confidence'] += 0.3
                elif 'call' in text_lower or 'check' in text_lower:
                    elements['button_regions']['call'] = (btn_x, btn_y, btn_w, btn_h)
                    elements['confidence'] += 0.3
                elif 'raise' in text_lower or 'bet' in text_lower:
                    elements['button_regions']['raise'] = (btn_x, btn_y, btn_w, btn_h)
                    elements['confidence'] += 0.3
            
            # Collect numbers (remove currency symbols and commas)
            number_text = text_clean.replace('$', '').replace('€', '').replace(',', '').replace('.', '')
            if number_text.isdigit():
                value = int(number_text)
                numbers.append({
                    'value': value,
                    'x': x, 'y': y, 'w': w, 'h': h,
                    'rel_x': rel_x, 'rel_y': rel_y
                })
        
        # Find pot: largest number in center area (not edges, not bottom)
        center_numbers = [n for n in numbers 
                         if 0.3 < n['rel_x'] < 0.7  # Center horizontally
                         and 0.2 < n['rel_y'] < 0.6]  # Middle vertically
        
        if center_numbers:
            # Pot is usually the largest number in center
            pot = max(center_numbers, key=lambda n: n['value'])
            elements['pot_region'] = (pot['x'], pot['y'], pot['w'], pot['h'])
            elements['confidence'] += 0.1
        
        return elements
    
    def create_preview(self, img: Image.Image, elements: Dict) -> Image.Image:
        """Create preview image with detected regions highlighted"""
        preview = img.copy()
        draw = ImageDraw.Draw(preview)
        
        # Draw button regions
        for name, region in elements.get('button_regions', {}).items():
            if region:
                x, y, w, h = region
                draw.rectangle([x, y, x+w, y+h], outline='red', width=3)
                draw.text((x, y-20), name.upper(), fill='red')
        
        # Draw pot region
        if elements.get('pot_region'):
            x, y, w, h = elements['pot_region']
            draw.rectangle([x, y, x+w, y+h], outline='green', width=3)
            draw.text((x, y-20), 'POT', fill='green')
        
        # Add confidence score
        conf = elements.get('confidence', 0.0)
        draw.text((10, 10), f"Confidence: {conf:.1%}", fill='yellow')
        
        return preview
    
    def validate_elements(self, elements: Dict) -> Tuple[bool, str]:
        """Validate detected elements are sufficient"""
        
        if not elements.get('button_regions'):
            return False, "No action buttons detected"
        
        if len(elements['button_regions']) < 2:
            return False, "Need at least 2 buttons (fold/call)"
        
        if elements.get('confidence', 0) < 0.5:
            return False, "Low confidence in detection"
        
        return True, "Elements detected successfully"
