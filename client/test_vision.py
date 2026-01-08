#!/usr/bin/env python3
"""
Test GPT-5-mini vision detection on a poker table screenshot
"""

import sys
import os
from vision_detector import VisionDetector

def test_vision(screenshot_path):
    """Test GPT-5-mini vision on screenshot"""
    
    # Check file exists
    if not os.path.exists(screenshot_path):
        print(f"File not found: {screenshot_path}")
        return
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("OPENAI_API_KEY not set in environment")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        return
    
    print(f"Analyzing: {screenshot_path}")
    print(f"🔑 API Key: {api_key[:10]}...")
    print()
    
    # Initialize detector
    detector = VisionDetector(api_key=api_key)
    
    # Analyze
    print("Calling GPT-5-mini...")
    result = detector.detect_poker_elements(screenshot_path)
    
    # Display results
    print("\nDetection Results:")
    print("=" * 60)
    print(f"Hero Cards:       {result.get('hero_cards', '??')}")
    print(f"Community Cards:  {result.get('community_cards', [])}")
    print(f"Pot:              ${result.get('pot', 0)}")
    print(f"Hero Stack:       ${result.get('hero_stack', 0)}")
    print(f"Opponent Stacks:  {result.get('opponent_stacks', [])}")
    print(f"To Call:          ${result.get('to_call', 0)}")
    print(f"Min Raise:        ${result.get('min_raise', 0)}")
    print(f"Actions:          {result.get('available_actions', [])}")
    print(f"Confidence:       {result.get('confidence', 0):.2f}")
    print("=" * 60)
    
    # Button positions
    if result.get('button_positions'):
        print("\n📍 Button Positions:")
        for action, pos in result['button_positions'].items():
            print(f"  {action}: {pos}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_vision.py <screenshot.png>")
        print()
        print("Example:")
        print("  export OPENAI_API_KEY='sk-...'")
        print("  python test_vision.py poker_table.png")
        sys.exit(1)
    
    test_vision(sys.argv[1])
