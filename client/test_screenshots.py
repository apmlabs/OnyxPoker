"""
Test vision detector on saved screenshots
Usage: 
  python test_screenshots.py [screenshot_path]           # Default: V1 vs V2 comparison
  python test_screenshots.py --compare [N]               # Compare V1 vs V2 on N screenshots from uploads
  python test_screenshots.py --compress [N]              # V1 (full) vs V2 (1280px compressed) comparison
  python test_screenshots.py --track [N]                 # Test opponent tracking across N screenshots
  python test_screenshots.py --v1 [screenshot_path]      # V1 only (no player detection)
  python test_screenshots.py --v2 [screenshot_path]      # V2 only (with player detection)
  python test_screenshots.py --ai-only [screenshot_path] # AI-only mode (gpt-5.2 does everything)
  python test_screenshots.py --strategy=value_lord       # Use specific strategy
"""

import os
import sys
import json
import glob
import tempfile
from datetime import datetime
from PIL import Image

# Parse args
V1_MODE = '--v1' in sys.argv
V2_MODE = '--v2' in sys.argv
AI_ONLY_MODE = '--ai-only' in sys.argv
TRACK_MODE = '--track' in sys.argv
COMPRESS_MODE = '--compress' in sys.argv
COMPARE_MODE = '--compare' in sys.argv or (not V1_MODE and not V2_MODE and not AI_ONLY_MODE and not TRACK_MODE and not COMPRESS_MODE)
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

# Opponent tracking logic (same as helper_bar.py)
ACTION_WORDS = ['fold', 'check', 'call', 'raise', 'bet', 'all-in', 'allin', 
                'post', 'muck', 'show', 'sit out', 'sitting out']

def is_action_word(name):
    """Check if name is actually an action word"""
    if not name:
        return True
    name_lower = name.lower()
    for word in ACTION_WORDS:
        if name_lower.startswith(word):
            return True
    return False

class OpponentTracker:
    """Track opponents across screenshots, handling action words as names"""
    def __init__(self):
        self.last_opponents = []
        self.last_hero_cards = None
    
    def merge(self, new_opponents, hero_cards):
        """Merge new detection with previous, filtering action words"""
        hero_cards_changed = (hero_cards != self.last_hero_cards)
        
        if hero_cards_changed:
            # New hand - reset
            self.last_hero_cards = hero_cards
            self.last_opponents = [o for o in new_opponents if not is_action_word(o.get('name'))]
            return new_opponents
        
        # Same hand - merge
        merged = []
        new_real_names = {o['name']: o for o in new_opponents if not is_action_word(o.get('name'))}
        
        for prev in self.last_opponents:
            name = prev.get('name')
            if name in new_real_names:
                merged.append(new_real_names[name])
            else:
                merged.append(prev)
        
        for name, opp in new_real_names.items():
            if not any(m.get('name') == name for m in merged):
                merged.append(opp)
        
        self.last_opponents = merged
        return merged

def compress_image(path, target_width=1280):
    """Compress image to target width, maintaining aspect ratio. Returns temp file path."""
    img = Image.open(path)
    w, h = img.size
    if w <= target_width:
        return path  # Already small enough
    ratio = target_width / w
    new_h = int(h * ratio)
    img_resized = img.resize((target_width, new_h), Image.LANCZOS)
    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img_resized.save(tmp.name, 'PNG')
    return tmp.name

def compare_v1_v2(v1_result, v2_result):
    """Compare V1 and V2 results, return list of differences."""
    diffs = []
    fields = ['hero_cards', 'community_cards', 'pot', 'to_call', 'big_blind']
    
    for field in fields:
        val1 = v1_result.get(field)
        val2 = v2_result.get(field)
        if val1 != val2:
            diffs.append(f"{field}: V1={val1} vs V2={val2}")
    
    return diffs

def test_compress(path, index=None, total=None):
    """Compare V1 (full) vs V2 (compressed to 1280px)."""
    prefix = f"[{index}/{total}] " if index else ""
    fname = os.path.basename(path)
    print(f"\n{prefix}{fname}", flush=True)
    print("-" * 50, flush=True)
    
    compressed_path = None
    try:
        v1 = VisionDetectorLite(model=VISION_MODEL)
        v2 = VisionDetectorV2(model=VISION_MODEL)
        
        # Get original size
        img = Image.open(path)
        orig_w, orig_h = img.size
        
        # Compress for V2
        compressed_path = compress_image(path, 1280)
        if compressed_path != path:
            comp_img = Image.open(compressed_path)
            comp_w, comp_h = comp_img.size
            print(f"  Original: {orig_w}x{orig_h} -> Compressed: {comp_w}x{comp_h}", flush=True)
        else:
            print(f"  Size: {orig_w}x{orig_h} (no compression needed)", flush=True)
        
        print(f"  V1 (full)...", end=" ", flush=True)
        v1_result = v1.detect_table(path)
        v1_time = v1_result.get('api_time', 0)
        print(f"done ({v1_time:.1f}s). V2 (compressed)...", end=" ", flush=True)
        v2_result = v2.detect_table(compressed_path)
        v2_time = v2_result.get('api_time', 0)
        print(f"done ({v2_time:.1f}s).", flush=True)
        
        diffs = compare_v1_v2(v1_result, v2_result)
        
        fields = ['hero_cards', 'community_cards', 'pot', 'to_call', 'hero_stack', 'big_blind']
        print(f"  {'Field':<18} {'V1 (full)':<25} {'V2 (1280px)':<25} {'Match'}", flush=True)
        print(f"  {'-'*18} {'-'*25} {'-'*25} {'-'*5}", flush=True)
        for field in fields:
            val1 = v1_result.get(field)
            val2 = v2_result.get(field)
            match = "OK" if val1 == val2 else "DIFF"
            print(f"  {field:<18} {str(val1):<25} {str(val2):<25} {match}", flush=True)
        
        opponents = v2_result.get('opponents', [])
        if opponents:
            in_hand = [p['name'] for p in opponents if p.get('has_cards')]
            print(f"  V2 opponents in hand: {in_hand}", flush=True)
        
        status = "MATCH" if len(diffs) == 0 else f"MISMATCH ({len(diffs)} diffs)"
        print(f"  Result: {status}", flush=True)
        print(f"  Time: V1={v1_time:.1f}s, V2={v2_time:.1f}s (diff={v2_time-v1_time:+.1f}s)", flush=True)
        
        return {'match': len(diffs) == 0, 'diffs': diffs, 'v1': v1_result, 'v2': v2_result,
                'v1_time': v1_time, 'v2_time': v2_time, 'orig_size': f"{orig_w}x{orig_h}"}
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {'match': False, 'error': str(e)}
    finally:
        if compressed_path and compressed_path != path:
            try:
                os.unlink(compressed_path)
            except:
                pass

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
                  'big_blind']
        
        print(f"  {'Field':<18} {'V1':<25} {'V2':<25} {'Match'}", flush=True)
        print(f"  {'-'*18} {'-'*25} {'-'*25} {'-'*5}", flush=True)
        for field in fields:
            val1 = v1_result.get(field)
            val2 = v2_result.get(field)
            match = "OK" if val1 == val2 else "DIFF"
            print(f"  {field:<18} {str(val1):<25} {str(val2):<25} {match}", flush=True)
        
        # V2 extra: opponents with cards (still in hand)
        opponents = v2_result.get('opponents', [])
        if opponents:
            in_hand = [p['name'] for p in opponents if p.get('has_cards')]
            print(f"  V2 opponents in hand: {in_hand} (players_in_hand={v2_result.get('players_in_hand')})", flush=True)
        
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
            opponents = result.get('opponents', [])
            if opponents:
                names = [p['name'] for p in opponents]
                if names:
                    print(f"  Opponents: {names}")
        
        return result
        
    except Exception as e:
        print(f"| ERROR: {e}")
        return None

def main():
    if COMPRESS_MODE:
        # Compare V1 (full) vs V2 (compressed to 1280px)
        print("COMPRESS MODE: V1 (full) vs V2 (1280px compressed)")
        print("=" * 60)
        
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
        total_v1_time = 0
        total_v2_time = 0
        all_results = []
        
        for i, path in enumerate(screenshots, 1):
            result = test_compress(path, i, len(screenshots))
            result['file'] = os.path.basename(path)
            all_results.append(result)
            if result.get('error'):
                errors += 1
            elif result.get('match'):
                matches += 1
                total_v1_time += result.get('v1_time', 0)
                total_v2_time += result.get('v2_time', 0)
            else:
                mismatches += 1
                total_v1_time += result.get('v1_time', 0)
                total_v2_time += result.get('v2_time', 0)
        
        print("\n" + "=" * 60)
        print(f"Results: {matches} matches, {mismatches} mismatches, {errors} errors")
        if matches + mismatches > 0:
            print(f"Match rate: {matches/(matches+mismatches)*100:.1f}%")
            n = matches + mismatches
            print(f"Avg time: V1={total_v1_time/n:.1f}s, V2 compressed={total_v2_time/n:.1f}s")
    
    elif COMPARE_MODE:
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
        out_file = os.path.join(os.path.dirname(__file__), 'logs', 'vision_compare_results.json')
        
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
            # Save after each screenshot
            with open(out_file, 'w') as f:
                json.dump(all_results, f, indent=2)
        
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
    
    elif TRACK_MODE:
        print("TRACK MODE: Test opponent tracking across screenshots", flush=True)
        print("=" * 70, flush=True)
        
        # Get screenshots
        if args and args[0].isdigit():
            limit = int(args[0])
        else:
            limit = 10
        screenshots = sorted(glob.glob(os.path.join(SCREENSHOTS_DIR, '*.png')))[:limit]
        
        if not screenshots:
            print(f"No screenshots found in {SCREENSHOTS_DIR}", flush=True)
            return
        
        print(f"Testing {len(screenshots)} screenshots with opponent tracking...\n", flush=True)
        
        v2 = VisionDetectorV2(model=VISION_MODEL)
        tracker = OpponentTracker()
        
        for i, path in enumerate(screenshots, 1):
            fname = os.path.basename(path)
            print(f"[{i}/{len(screenshots)}] {fname}", flush=True)
            print(f"  V2 detecting...", end=" ", flush=True)
            
            result = v2.detect_table(path)
            api_time = result.get('api_time', 0)
            print(f"done ({api_time:.1f}s)", flush=True)
            
            hero_cards = result.get('hero_cards')
            raw_opponents = result.get('opponents', [])
            
            # Show raw detection with has_cards
            raw_info = [(o.get('name', '?'), o.get('has_cards', '?')) for o in raw_opponents]
            action_detected = [o.get('name') for o in raw_opponents if is_action_word(o.get('name'))]
            
            print(f"  Hero cards: {hero_cards}", flush=True)
            print(f"  Raw opponents: {raw_info}", flush=True)
            if action_detected:
                print(f"  >>> Action words: {action_detected}", flush=True)
            
            # Apply tracking
            merged = tracker.merge(raw_opponents, hero_cards)
            merged_info = [(o.get('name', '?'), o.get('has_cards', '?')) for o in merged]
            in_hand = [o.get('name') for o in merged if o.get('has_cards')]
            
            print(f"  After tracking: {merged_info}", flush=True)
            print(f"  In hand (has_cards=True): {in_hand}", flush=True)
            print(f"  num_players would be: {len(in_hand) + 1}", flush=True)
            print("", flush=True)

if __name__ == '__main__':
    main()
