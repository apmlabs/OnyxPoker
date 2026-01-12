#!/usr/bin/env python3
"""
Analyze session logs and correlate with screenshots.
Run on server after receiving logs via send_logs.py

Usage: python analyze_session.py [log_file]
"""
import os
import sys
import json
from datetime import datetime

UPLOADS_DIR = '/home/ubuntu/mcpprojects/onyxpoker-server/server/uploads'

def analyze_log(log_path):
    print(f"\n{'='*60}")
    print(f"SESSION ANALYSIS: {os.path.basename(log_path)}")
    print(f"{'='*60}\n")
    
    with open(log_path) as f:
        entries = [json.loads(line) for line in f if line.strip()]
    
    print(f"Total decisions: {len(entries)}\n")
    
    # Group by action
    actions = {}
    for e in entries:
        a = e.get('action', 'unknown')
        actions[a] = actions.get(a, 0) + 1
    
    print("Action breakdown:")
    for a, count in sorted(actions.items(), key=lambda x: -x[1]):
        print(f"  {a}: {count}")
    
    print(f"\n{'='*60}")
    print("HAND-BY-HAND REVIEW")
    print(f"{'='*60}\n")
    
    for i, e in enumerate(entries, 1):
        screenshot = e.get('screenshot', 'unknown')
        cards = ' '.join(e.get('hero_cards', [])) or '--'
        board = ' '.join(e.get('board', [])) or 'preflop'
        pot = e.get('pot', 0)
        pos = e.get('position', '?')
        action = e.get('action', '?')
        amount = e.get('amount')
        reasoning = e.get('reasoning', '')[:80]
        conf = e.get('confidence', 0)
        
        # Check if screenshot exists
        screenshot_path = os.path.join(UPLOADS_DIR, screenshot) if screenshot else None
        has_screenshot = screenshot_path and os.path.exists(screenshot_path)
        
        print(f"[{i}] {screenshot} {'[IMG]' if has_screenshot else '[NO IMG]'}")
        print(f"    {pos} | {cards} | {board} | Pot: ${pot}")
        print(f"    => {action.upper()}" + (f" ${amount}" if amount else "") + f" (conf: {conf:.0%})")
        print(f"    {reasoning}...")
        print()
    
    print(f"{'='*60}")
    print("SCREENSHOTS IN UPLOADS (for manual review):")
    print(f"{'='*60}\n")
    
    if os.path.isdir(UPLOADS_DIR):
        files = sorted([f for f in os.listdir(UPLOADS_DIR) if f.endswith('.png')])
        print(f"Total: {len(files)} screenshots")
        print(f"Path: {UPLOADS_DIR}")
        print(f"\nTo view: ls -la {UPLOADS_DIR}")
    else:
        print(f"Uploads dir not found: {UPLOADS_DIR}")

def main():
    if len(sys.argv) > 1:
        analyze_log(sys.argv[1])
    else:
        # Find latest log in uploads
        if os.path.isdir(UPLOADS_DIR):
            logs = sorted([f for f in os.listdir(UPLOADS_DIR) if f.endswith('.jsonl')])
            if logs:
                analyze_log(os.path.join(UPLOADS_DIR, logs[-1]))
            else:
                print("No logs found. Run send_logs.py from Windows first.")
        else:
            print(f"Uploads dir not found: {UPLOADS_DIR}")

if __name__ == '__main__':
    main()
