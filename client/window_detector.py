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
        """Find all PokerStars windows"""
        windows = []
        
        # Common poker client window titles
        poker_keywords = ['pokerstars', 'poker', 'table', 'hold', 'holdem']
        
        for window in gw.getAllWindows():
            title_lower = window.title.lower()
            if any(kw in title_lower for kw in poker_keywords):
                if window.width > 400 and window.height > 300:  # Reasonable size
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
        """Auto-detect poker table elements using CV"""
        
        # Convert to OpenCV format
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        elements = {
            'pot_region': None,
            'button_regions': {},
            'card_regions': [],
            'stack_regions': [],
            'confidence': 0.0
        }
        
        # Detect buttons by looking for rectangular regions at bottom
        height, width = gray.shape
        bottom_region = gray[int(height * 0.8):, :]
        
        # Find contours (potential buttons)
        edges = cv2.Canny(bottom_region, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        buttons = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # Button-like dimensions
            if 60 < w < 150 and 30 < h < 60:
                buttons.append((x, y + int(height * 0.8), w, h))
        
        # Sort buttons left to right
        buttons.sort(key=lambda b: b[0])
        
        if len(buttons) >= 3:
            elements['button_regions'] = {
                'fold': buttons[0],
                'call': buttons[1] if len(buttons) > 1 else buttons[0],
                'raise': buttons[2] if len(buttons) > 2 else buttons[0]
            }
            elements['confidence'] = 0.7
        
        # Detect pot region (center-top area with text)
        pot_region = gray[int(height * 0.2):int(height * 0.4), int(width * 0.3):int(width * 0.7)]
        
        # Look for text in this region
        text = pytesseract.image_to_string(pot_region)
        if any(char.isdigit() for char in text):
            elements['pot_region'] = (
                int(width * 0.3),
                int(height * 0.2),
                int(width * 0.4),
                int(height * 0.2)
            )
            elements['confidence'] += 0.2
        
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
