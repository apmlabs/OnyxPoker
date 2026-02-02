#!/usr/bin/env python3
"""Validate CV detector against hand history ground truth."""

import os
import re
import sys
from datetime import datetime, timedelta
from glob import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vision_detector_cv import VisionDetectorCV

HH_DIR = "../../idealistslp_extracted"
SCREENSHOT_DIR = "../../server/uploads"

def parse_hh_file(filepath):
    """Parse hand history file, return list of hands with timestamps and data."""
    hands = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # Split by hand boundaries
    hand_blocks = re.split(r'\n\n+(?=PokerStars)', content)
    
    for block in hand_blocks:
        if not block.strip():
            continue
        
        # Extract timestamp: 2026/01/20 11:25:23 CET
        ts_match = re.search(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) CET', block)
        if not ts_match:
            continue
        
        ts = datetime.strptime(ts_match.group(1), '%Y/%m/%d %H:%M:%S')
        
        # Extract hero cards: Dealt to idealistslp [6d 8c]
        hero_match = re.search(r'Dealt to idealistslp \[([^\]]+)\]', block)
        hero_cards = hero_match.group(1).split() if hero_match else []
        
        # Extract community cards from FLOP/TURN/RIVER
        community = []
        flop = re.search(r'\*\*\* FLOP \*\*\* \[([^\]]+)\]', block)
        if flop:
            community.extend(flop.group(1).split())
        turn = re.search(r'\*\*\* TURN \*\*\* \[[^\]]+\] \[([^\]]+)\]', block)
        if turn:
            community.append(turn.group(1))
        river = re.search(r'\*\*\* RIVER \*\*\* \[[^\]]+\] \[([^\]]+)\]', block)
        if river:
            community.append(river.group(1))
        
        # Extract pot from SUMMARY
        pot_match = re.search(r'Total pot €([\d.]+)', block)
        pot = float(pot_match.group(1)) if pot_match else 0.0
        
        hands.append({
            'timestamp': ts,
            'hero_cards': hero_cards,
            'community_cards': community,
            'pot': pot,
            'raw': block[:200]  # First 200 chars for debugging
        })
    
    return hands

def parse_screenshot_timestamp(filename):
    """Parse screenshot filename to datetime: 20260120_112519.png -> datetime"""
    basename = os.path.basename(filename).replace('.png', '')
    if basename.startswith('BROKEN_'):
        return None
    try:
        return datetime.strptime(basename, '%Y%m%d_%H%M%S')
    except:
        return None

def find_matching_hand(screenshot_ts, hands, tolerance_sec=10):
    """Find hand history entry closest to screenshot timestamp."""
    best_match = None
    best_diff = timedelta(seconds=tolerance_sec + 1)
    
    for hand in hands:
        diff = abs(screenshot_ts - hand['timestamp'])
        if diff < best_diff:
            best_diff = diff
            best_match = hand
    
    if best_diff <= timedelta(seconds=tolerance_sec):
        return best_match, best_diff.total_seconds()
    return None, None

def find_matching_hand_by_cards(detected_hero, hands, screenshot_ts, tolerance_sec=30):
    """Find hand that matches detected hero cards within time window."""
    detected_norm = set(normalize_card(c) for c in detected_hero)
    
    for hand in hands:
        diff = abs((screenshot_ts - hand['timestamp']).total_seconds())
        if diff > tolerance_sec:
            continue
        
        truth_norm = set(normalize_card(c) for c in hand['hero_cards'])
        if detected_norm == truth_norm:
            return hand, diff
    
    return None, None

def normalize_card(card):
    """Normalize card format: Ah -> Ah, ah -> Ah"""
    if len(card) != 2:
        return card
    return card[0].upper() + card[1].lower()

def compare_cards(detected, ground_truth):
    """Compare card lists, return (matches, mismatches, missing)."""
    detected_norm = set(normalize_card(c) for c in detected)
    truth_norm = set(normalize_card(c) for c in ground_truth)
    
    matches = detected_norm & truth_norm
    mismatches = detected_norm - truth_norm  # Detected but wrong
    missing = truth_norm - detected_norm      # Should have detected
    
    return matches, mismatches, missing

def main():
    # Load all HH files
    hh_files = glob(os.path.join(HH_DIR, "HH20260120*.txt"))
    print(f"Loading {len(hh_files)} hand history files...")
    
    all_hands = []
    for hh_file in hh_files:
        hands = parse_hh_file(hh_file)
        all_hands.extend(hands)
        print(f"  {os.path.basename(hh_file)}: {len(hands)} hands")
    
    print(f"Total: {len(all_hands)} hands")
    
    # Sort by timestamp
    all_hands.sort(key=lambda h: h['timestamp'])
    
    # Get Jan 20 screenshots
    screenshots = sorted(glob(os.path.join(SCREENSHOT_DIR, "20260120*.png")))
    print(f"\nFound {len(screenshots)} screenshots from Jan 20")
    
    # Initialize detector
    detector = VisionDetectorCV()
    
    # Stats
    total = 0
    matched = 0
    hero_correct = 0
    hero_partial = 0
    hero_wrong = 0
    hero_timing = 0  # Wrong due to timing mismatch
    community_correct = 0
    community_partial = 0
    pot_correct = 0
    pot_close = 0  # Within 10%
    
    errors = []
    
    # Test first N screenshots
    test_count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    
    for screenshot in screenshots[:test_count]:
        ss_ts = parse_screenshot_timestamp(screenshot)
        if not ss_ts:
            continue
        
        hand, diff = find_matching_hand(ss_ts, all_hands)
        if not hand:
            print(f"\n{os.path.basename(screenshot)}: No matching hand within 10s")
            continue
        
        total += 1
        matched += 1
        
        # Run CV detector
        try:
            result = detector.detect_table(screenshot)
        except Exception as e:
            errors.append((screenshot, str(e)))
            print(f"\n{os.path.basename(screenshot)}: ERROR - {e}")
            continue
        
        # Compare hero cards
        h_match, h_wrong, h_missing = compare_cards(
            result.get('hero_cards', []), 
            hand['hero_cards']
        )
        
        if len(h_wrong) == 0 and len(h_missing) == 0:
            hero_correct += 1
            h_status = "✓"
        elif len(h_match) > 0:
            hero_partial += 1
            h_status = f"PARTIAL: got {result.get('hero_cards')}, expected {hand['hero_cards']}"
        else:
            # Check if detected cards match a different nearby hand (timing issue)
            alt_hand, alt_diff = find_matching_hand_by_cards(
                result.get('hero_cards', []), all_hands, ss_ts, tolerance_sec=60
            )
            if alt_hand:
                hero_timing += 1
                h_status = f"TIMING: got {result.get('hero_cards')} (matches hand at {alt_hand['timestamp'].strftime('%H:%M:%S')})"
            else:
                hero_wrong += 1
                h_status = f"WRONG: got {result.get('hero_cards')}, expected {hand['hero_cards']}"
        
        # Compare community cards
        c_match, c_wrong, c_missing = compare_cards(
            result.get('community_cards', []),
            hand['community_cards']
        )
        
        if len(c_wrong) == 0 and len(c_missing) == 0:
            community_correct += 1
            c_status = "✓"
        elif len(c_match) > 0:
            community_partial += 1
            c_status = f"PARTIAL: got {result.get('community_cards')}, expected {hand['community_cards']}"
        else:
            c_status = f"WRONG: got {result.get('community_cards')}, expected {hand['community_cards']}"
        
        # Compare pot (screenshot might be mid-hand, so pot may differ)
        detected_pot = result.get('pot', 0)
        expected_pot = hand['pot']
        
        if abs(detected_pot - expected_pot) < 0.01:
            pot_correct += 1
            p_status = "✓"
        elif expected_pot > 0 and abs(detected_pot - expected_pot) / expected_pot < 0.5:
            pot_close += 1
            p_status = f"CLOSE: {detected_pot} vs {expected_pot}"
        else:
            p_status = f"DIFF: {detected_pot} vs {expected_pot}"
        
        print(f"\n{os.path.basename(screenshot)} (diff: {diff:.1f}s)")
        print(f"  Hero: {h_status}")
        print(f"  Community: {c_status}")
        print(f"  Pot: {p_status}")
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"Screenshots tested: {total}")
    print(f"Matched to HH: {matched}")
    print(f"\nHero cards:")
    print(f"  Correct: {hero_correct}/{total} ({100*hero_correct/total:.1f}%)")
    print(f"  Partial: {hero_partial}/{total}")
    print(f"  Timing mismatch: {hero_timing}/{total}")
    print(f"  Wrong: {hero_wrong}/{total}")
    print(f"\nCommunity cards:")
    print(f"  Correct: {community_correct}/{total} ({100*community_correct/total:.1f}%)")
    print(f"  Partial: {community_partial}/{total}")
    print(f"\nPot:")
    print(f"  Exact: {pot_correct}/{total}")
    print(f"  Close (<50% diff): {pot_close}/{total}")
    
    if errors:
        print(f"\nErrors: {len(errors)}")
        for ss, err in errors[:5]:
            print(f"  {os.path.basename(ss)}: {err}")

if __name__ == '__main__':
    main()
