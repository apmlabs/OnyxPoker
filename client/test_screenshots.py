"""
Test vision detector on saved screenshots
Usage: python test_screenshots.py [screenshot_path]
"""

import os
import sys
import json
from datetime import datetime
from vision_detector import VisionDetector

LOG_FILE = None

def test_screenshot(path, index=None, total=None):
    global LOG_FILE
    prefix = f"[{index}/{total}] " if index else ""
    fname = os.path.basename(path)
    print(f"{prefix}{fname}", end=" ", flush=True)
    
    detector = VisionDetector()
    try:
        result = detector.detect_poker_elements(path, include_decision=True)
        
        cards = result.get('hero_cards') or []
        pos = result.get('position') or '?'
        turn = result.get('is_hero_turn', False)
        action = result.get('action') or 'none'
        api_time = result.get('api_time', 0)
        
        out = f"| {' '.join(cards) if cards else '--':8} | {pos:3} | turn={str(turn):5} | {action:6} | {api_time:.1f}s"
        print(out)
        
        # Save to log
        if LOG_FILE:
            result['screenshot'] = fname
            result['timestamp'] = datetime.now().isoformat()
            LOG_FILE.write(json.dumps(result) + '\n')
            LOG_FILE.flush()
        
        return result
    except Exception as e:
        err = str(e).encode('ascii', 'replace').decode('ascii')
        print(f"| ERROR: {err[:50]}")
        return None

def main():
    global LOG_FILE
    
    if len(sys.argv) > 1:
        test_screenshot(sys.argv[1])
    else:
        screenshots_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
        if not os.path.exists(screenshots_dir):
            print(f"No screenshots folder found")
            return
        
        files = sorted([f for f in os.listdir(screenshots_dir) if f.endswith('.png')])
        if not files:
            print(f"No screenshots found")
            return
        
        # Create log file
        logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
        LOG_FILE = open(log_path, 'w')
        
        print(f"Testing {len(files)} screenshots, logging to {log_path}\n")
        for i, f in enumerate(files, 1):
            test_screenshot(os.path.join(screenshots_dir, f), i, len(files))
        
        LOG_FILE.close()
        print(f"\nDone! Results saved to: {log_path}")
        print(f"Upload with: python send_logs.py")

if __name__ == '__main__':
    main()
