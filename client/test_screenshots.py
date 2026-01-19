"""
Test vision detector on saved screenshots
Usage: 
  python test_screenshots.py [screenshot_path]           # Default: V1 vs V2 comparison
  python test_screenshots.py --compare [N]               # Compare V1 vs V2 on N screenshots from uploads
  python test_screenshots.py --v1 [screenshot_path]      # V1 only (no player detection)
  python test_screenshots.py --v2 [screenshot_path]      # V2 only (with player detection)
  python test_screenshots.py --ai-only [screenshot_path] # AI-only mode (gpt-5.2 does everything)
  python test_screenshots.py --strategy=value_lord       # Use specific strategy
"""

import os
import sys
import json
import glob
import requests
from datetime import datetime

# Parse args
V1_MODE = '--v1' in sys.argv
V2_MODE = '--v2' in sys.argv
AI_ONLY_MODE = '--ai-only' in sys.argv
COMPARE_MODE = '--compare' in sys.argv or (not V1_MODE and not V2_MODE and not AI_ONLY_MODE)
STRATEGY = 'value_lord'
VISION_MODEL = None

for arg in sys.argv:
    if arg.startswith('--strategy='):
        STRATEGY = arg.split('=')[1]
    if arg.startswith('--model='):
        VISION_MODEL = arg.split('=')[1]

# Remove flags from argv for path parsing
args = [a for a in sys.argv[1:] if not a.startswith('--')]

# Imports based on mode
from vision_detector_lite import VisionDetectorLite
from vision_detector_v2 import VisionDetectorV2
from strategy_engine import StrategyEngine

if AI_ONLY_MODE:
    from vision_detector import VisionDetector

LOG_FILE = None
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), 'screenshots')

def compare_v1_v2(v1_result, v2_result):
    """Compare V1 and V2 results, return list of differences."""
    diffs = []
    fields = ['hero_cards', 'community_cards', 'pot', 'to_call', 'is_hero_turn', 'big_blind']
    
    for field in fields:
        val1 = v1_result.get(field)
        val2 = v2_result.get(field)
        if val1 != val2:
            diffs.append(f"{field}: V1={val1} vs V2={val2}")
    
    return diffs

def test_compare(path, index=None, total=None):
    """Compare V1 vs V2 on same screenshot."""
    prefix = f"[{index}/{total}] " if index else ""
    fname = os.path.basename(path)
    print(f"\n{prefix}{fname}", flush=True)
    print("-" * 50, flush=True)
    
    try:
        v1 = VisionDetectorLite(model=VISION_MODEL)
        v2 = VisionDetectorV2(model=VISION_MODEL)
        
        print(f"  V1...", end=" ", flush=True)
        v1_result = v1.detect_table(path)
        v1_time = v1_result.get('api_time', 0)
        print(f"done ({v1_time:.1f}s). V2...", end=" ", flush=True)
        v2_result = v2.detect_table(path)
        v2_time = v2_result.get('api_time', 0)
        print(f"done ({v2_time:.1f}s).", flush=True)
        
        diffs = compare_v1_v2(v1_result, v2_result)
        
        # Print all key fields for both
        fields = ['hero_cards', 'community_cards', 'pot', 'to_call', 'hero_stack', 
                  'is_hero_turn', 'big_blind', 'hero_position', 'facing']
        
        print(f"  {'Field':<18} {'V1':<25} {'V2':<25} {'Match'}", flush=True)
        print(f"  {'-'*18} {'-'*25} {'-'*25} {'-'*5}", flush=True)
        for field in fields:
            val1 = v1_result.get(field)
            val2 = v2_result.get(field)
            match = "OK" if val1 == val2 else "DIFF"
            print(f"  {field:<18} {str(val1):<25} {str(val2):<25} {match}", flush=True)
        
        # V2 extra: players
        players = v2_result.get('players', [])
        if players:
            names = [p['name'] for p in players if not p.get('is_hero')]
            print(f"  V2 players: {names}", flush=True)
        
        status = "MATCH" if len(diffs) == 0 else f"MISMATCH ({len(diffs)} diffs)"
        print(f"  Result: {status}", flush=True)
        
        return {'match': len(diffs) == 0, 'diffs': diffs, 'v1': v1_result, 'v2': v2_result}
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {'match': False, 'error': str(e)}

def test_single(path, mode='v2'):
    """Test single screenshot with specified mode."""
    fname = os.path.basename(path)
    print(f"{fname}", end=" ", flush=True)
    
    try:
        if mode == 'v1':
            detector = VisionDetectorLite(model=VISION_MODEL)
            result = detector.detect_table(path)
        elif mode == 'v2':
            detector = VisionDetectorV2(model=VISION_MODEL)
            result = detector.detect_table(path)
        else:  # ai-only
            detector = VisionDetector()
            result = detector.detect_poker_elements(path, include_decision=True)
        
        cards = result.get('hero_cards') or []
        board = result.get('community_cards') or []
        pot = result.get('pot', 0)
        to_call = result.get('to_call', 0)
        api_time = result.get('api_time', 0)
        
        print(f"| {' '.join(cards) if cards else '--':8} | board={board} | pot={pot} | to_call={to_call} | {api_time:.1f}s")
        
        if mode == 'v2':
            players = result.get('players', [])
            if players:
                names = [p['name'] for p in players if not p.get('is_hero')]
                if names:
                    print(f"  Players: {names}")
        
        return result
        
    except Exception as e:
        print(f"| ERROR: {e}")
        return None

def main():
    if COMPARE_MODE:
        # Default: compare V1 vs V2
        print("COMPARE MODE: V1 vs V2 vision comparison")
        print("=" * 60)
        
        # Get screenshots
        if args and args[0].isdigit():
            limit = int(args[0])
            screenshots = sorted(glob.glob(os.path.join(SCREENSHOTS_DIR, '*.png')))[:limit]
        elif args:
            screenshots = [args[0]]
        else:
            screenshots = sorted(glob.glob(os.path.join(SCREENSHOTS_DIR, '*.png')))[:5]
        
        if not screenshots:
            print(f"No screenshots found in {SCREENSHOTS_DIR}")
            return
        
        print(f"Testing {len(screenshots)} screenshots...\n")
        
        matches = 0
        mismatches = 0
        errors = 0
        all_results = []
        
        for i, path in enumerate(screenshots, 1):
            result = test_compare(path, i, len(screenshots))
            result['file'] = os.path.basename(path)
            all_results.append(result)
            if result.get('error'):
                errors += 1
            elif result.get('match'):
                matches += 1
            else:
                mismatches += 1
        
        # Save detailed results
        out_file = os.path.join(os.path.dirname(__file__), 'vision_compare_results.json')
        with open(out_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\nDetailed results saved to: {out_file}")
        
        print("\n" + "=" * 60)
        print(f"Results: {matches} matches, {mismatches} mismatches, {errors} errors")
        if matches + mismatches > 0:
            print(f"Match rate: {matches/(matches+mismatches)*100:.1f}%")
    
    elif V1_MODE:
        print("V1 MODE: vision_detector_lite (no player detection)\n")
        if args:
            test_single(args[0], 'v1')
        else:
            screenshots = sorted(glob.glob(os.path.join(SCREENSHOTS_DIR, '*.png')))[:5]
            for i, path in enumerate(screenshots, 1):
                print(f"[{i}/{len(screenshots)}] ", end="")
                test_single(path, 'v1')
    
    elif V2_MODE:
        print("V2 MODE: vision_detector_v2 (with player detection)\n")
        if args:
            test_single(args[0], 'v2')
        else:
            screenshots = sorted(glob.glob(os.path.join(SCREENSHOTS_DIR, '*.png')))[:5]
            for i, path in enumerate(screenshots, 1):
                print(f"[{i}/{len(screenshots)}] ", end="")
                test_single(path, 'v2')
    
    elif AI_ONLY_MODE:
        print("AI-ONLY MODE: gpt-5.2 does everything\n")
        if args:
            test_single(args[0], 'ai-only')
        else:
            screenshots = sorted(glob.glob(os.path.join(SCREENSHOTS_DIR, '*.png')))[:5]
            for i, path in enumerate(screenshots, 1):
                print(f"[{i}/{len(screenshots)}] ", end="")
                test_single(path, 'ai-only')

if __name__ == '__main__':
    main()
