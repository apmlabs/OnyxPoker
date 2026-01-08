"""
Test vision detector on saved screenshots
Usage: python test_screenshots.py [screenshot_path]
"""

import os
import sys
import json
from vision_detector import VisionDetector

def test_screenshot(path):
    print(f"\n{'='*60}")
    print(f"Testing: {os.path.basename(path)}")
    print('='*60)
    
    detector = VisionDetector()
    try:
        result = detector.detect_poker_elements(path, include_decision=True)
        
        cards = result.get('hero_cards') or []
        board = result.get('community_cards') or []
        pot = result.get('pot') or 0
        action = result.get('recommended_action') or 'none'
        amount = result.get('recommended_amount') or 0
        reasoning = result.get('reasoning') or ''
        api_time = result.get('api_time', 0)
        
        print(f"Cards:  {' '.join(cards) if cards else '--'}")
        print(f"Board:  {' '.join(board) if board else '--'}")
        print(f"Pot:    ${pot}")
        print(f"Action: {action}" + (f" ${amount}" if amount else ""))
        print(f"Reason: {reasoning[:100]}..." if len(reasoning) > 100 else f"Reason: {reasoning}")
        print(f"Time:   {api_time:.1f}s")
        print(f"\nRaw JSON:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"ERROR: {e}")

def main():
    if len(sys.argv) > 1:
        # Test specific file
        test_screenshot(sys.argv[1])
    else:
        # Test all screenshots in folder
        screenshots_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
        if not os.path.exists(screenshots_dir):
            print(f"No screenshots folder. Run helper_bar.py and press F9 to capture some.")
            return
        
        files = sorted([f for f in os.listdir(screenshots_dir) if f.endswith('.png')])
        if not files:
            print(f"No screenshots found in {screenshots_dir}")
            return
        
        print(f"Found {len(files)} screenshots")
        for f in files:
            test_screenshot(os.path.join(screenshots_dir, f))

if __name__ == '__main__':
    main()
