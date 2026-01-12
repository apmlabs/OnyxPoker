"""
Test vision detector on saved screenshots
Usage: 
  python test_screenshots.py [screenshot_path]           # Full mode (gpt-5.2)
  python test_screenshots.py --lite [screenshot_path]    # Lite mode (gpt-4o-mini + strategy)
  python test_screenshots.py --lite --strategy=gpt4      # Lite mode with specific strategy
  python test_screenshots.py --lite --model=gpt-4o       # Lite mode with specific vision model
  python test_screenshots.py --lite --test-all-models    # Test all vision models
  
Available vision models for --lite mode:
  gpt-4o          - Best vision specialist (94% accuracy)
  gpt-4o-mini     - Budget vision (89% accuracy, current default)
  gpt-5-mini      - GPT-5 with reasoning control
  gpt-5-nano      - Cheapest GPT-5
  gpt-5.2         - Best accuracy (full mode default)
  kiro-server     - Kiro CLI via server subprocess (validation)
  
Note: GPT-5 models automatically use reasoning="none" for vision tasks (faster, cheaper)
"""

import os
import sys
import json
import requests
from datetime import datetime

# Parse args
LITE_MODE = '--lite' in sys.argv
STRATEGY = 'gpt3'
VISION_MODEL = None  # None = use default for mode
TEST_ALL_MODELS = '--test-all-models' in sys.argv

# All available vision models to test
ALL_VISION_MODELS = [
    'gpt-4o',           # Best vision specialist (75% cards, 64% board)
    'gpt-5-mini',       # GPT-5 family (62.5% cards, 60% board)
    'gpt-5.1',          # GPT-5.1 (75% cards, 82% board)
    'gpt-5.2',          # Best accuracy (100% cards, 91% board) ⭐
    'kiro-server'       # Kiro CLI via server subprocess
]

for arg in sys.argv:
    if arg.startswith('--strategy='):
        STRATEGY = arg.split('=')[1]
    if arg.startswith('--model='):
        VISION_MODEL = arg.split('=')[1]

# Remove flags from argv for path parsing
args = [a for a in sys.argv[1:] if not a.startswith('--')]

if LITE_MODE:
    from vision_detector_lite import VisionDetectorLite
    from strategy_engine import StrategyEngine, get_available_strategies
else:
    from vision_detector import VisionDetector

LOG_FILE = None
KIRO_SERVER_URL = os.getenv('KIRO_SERVER_URL', 'http://54.80.204.92:5001')

def validate_with_kiro_server(table_data):
    """Validate poker state using Kiro CLI via server"""
    print(f"\n{'='*80}")
    print(f"KIRO-SERVER VALIDATION START")
    print(f"{'='*80}")
    print(f"Sending to server: {KIRO_SERVER_URL}/validate-state")
    print(f"State: cards={table_data.get('hero_cards')}, board={table_data.get('community_cards')}, pot={table_data.get('pot')}, pos={table_data.get('position')}")
    
    try:
        import time
        start = time.time()
        
        response = requests.post(
            f'{KIRO_SERVER_URL}/validate-state',
            json={'state': table_data},
            timeout=180
        )
        
        elapsed = time.time() - start
        print(f"Response received in {elapsed:.2f}s")
        print(f"Status code: {response.status_code}")
        
        result = response.json()
        print(f"Understood: {result.get('understood')}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"Interpretation preview: {result.get('interpretation', '')[:100]}...")
        print(f"Concerns: {result.get('concerns')}")
        print(f"{'='*80}\n")
        
        return result
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print(f"{'='*80}\n")
        return {
            'understood': False,
            'confidence': 0.0,
            'interpretation': f'Error: {str(e)}',
            'concerns': [str(e)]
        }

def test_screenshot(path, index=None, total=None, model_override=None):
    global LOG_FILE
    prefix = f"[{index}/{total}] " if index else ""
    fname = os.path.basename(path)
    model_suffix = f" ({model_override})" if model_override else ""
    print(f"{prefix}{fname}{model_suffix}", end=" ", flush=True)
    
    try:
        if LITE_MODE:
            # Use kiro-server for validation if specified
            if model_override == 'kiro-server':
                # First get table data with default vision model
                detector = VisionDetectorLite(model='gpt-4o-mini')
                table_data = detector.detect_table(path)
                
                # Then validate with Kiro server
                validation = validate_with_kiro_server(table_data)
                
                # Combine results
                result = {
                    **table_data,
                    'model': 'kiro-server',
                    'validation': validation,
                    'action': 'validated' if validation.get('understood') else 'invalid',
                    'reasoning': validation.get('interpretation', ''),
                    'confidence': validation.get('confidence', 0.0)
                }
            else:
                # Normal vision + strategy flow
                detector = VisionDetectorLite(model=model_override or VISION_MODEL)
                table_data = detector.detect_table(path)
                
                engine = StrategyEngine(STRATEGY)
                decision = engine.get_action(table_data)
                
                result = {**table_data, **decision}
        else:
            detector = VisionDetector()
            result = detector.detect_poker_elements(path, include_decision=True)
        
        cards = result.get('hero_cards') or []
        pos = result.get('position') or '?'
        turn = result.get('is_hero_turn', False)
        action = result.get('action') or 'none'
        api_time = result.get('api_time', 0)
        strategy = result.get('strategy', 'gpt-5.2')
        model_used = result.get('model', 'unknown')
        
        out = f"| {' '.join(cards) if cards else '--':8} | {pos:3} | turn={str(turn):5} | {action:6} | {api_time:.1f}s | {model_used}"
        print(out)
        
        # Save to log
        if LOG_FILE:
            result['screenshot'] = fname
            result['timestamp'] = datetime.now().isoformat()
            if model_override:
                result['test_model'] = model_override
            LOG_FILE.write(json.dumps(result) + '\n')
            LOG_FILE.flush()
        
        return result
    except Exception as e:
        err = str(e).encode('ascii', 'replace').decode('ascii')
        print(f"| ERROR: {err}")
        return None

def main():
    global LOG_FILE
    
    if LITE_MODE:
        model_info = VISION_MODEL or 'gpt-4o-mini (default)'
        if TEST_ALL_MODELS:
            model_info = f"ALL MODELS: {', '.join(ALL_VISION_MODELS)}"
        print(f"LITE MODE: {model_info} + {STRATEGY} strategy")
        print(f"Available strategies: {', '.join(get_available_strategies())}\n")
    else:
        print("FULL MODE: gpt-5.2\n")
    
    if args:
        # Single screenshot
        if TEST_ALL_MODELS and LITE_MODE:
            print(f"Testing {len(ALL_VISION_MODELS)} models on single screenshot:\n")
            for model in ALL_VISION_MODELS:
                test_screenshot(args[0], model_override=model)
        else:
            test_screenshot(args[0])
    else:
        # All screenshots in folder
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
        
        if TEST_ALL_MODELS and LITE_MODE:
            # Test all models on each screenshot (side-by-side comparison)
            mode_suffix = f"lite_{STRATEGY}_all_models"
            log_path = os.path.join(logs_dir, f"test_{mode_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
            LOG_FILE = open(log_path, 'w')
            
            print(f"Testing {len(files)} screenshots with {len(ALL_VISION_MODELS)} models each")
            print(f"Logging to: {log_path}\n")
            
            for i, f in enumerate(files, 1):
                print(f"\n[{i}/{len(files)}] {f}")
                for model in ALL_VISION_MODELS:
                    test_screenshot(os.path.join(screenshots_dir, f), model_override=model)
            
            LOG_FILE.close()
            print(f"\n{'='*80}")
            print(f"Done! Results saved to: {log_path}")
            print(f"Upload with: python send_logs.py")
            print(f"{'='*80}")
        else:
            # Single model test
            mode_suffix = f"lite_{STRATEGY}" if LITE_MODE else "full"
            if VISION_MODEL:
                mode_suffix += f"_{VISION_MODEL.replace('.', '_').replace('-', '_')}"
            log_path = os.path.join(logs_dir, f"test_{mode_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
            LOG_FILE = open(log_path, 'w')
            
            print(f"Testing {len(files)} screenshots, logging to {log_path}\n")
            for i, f in enumerate(files, 1):
                test_screenshot(os.path.join(screenshots_dir, f), i, len(files))
            
            LOG_FILE.close()
            print(f"\nDone! Results saved to: {log_path}")
            print(f"Upload with: python send_logs.py")

if __name__ == '__main__':
    main()
