#!/usr/bin/env python3
"""
Test overlay update - run this to see if overlay updates work
"""

import sys
import os
sys.path.append('/home/ubuntu/mcpprojects/onyxpoker/client')

from mini_overlay import MiniOverlay
import tkinter as tk
import time

# Create test window
root = tk.Tk()
root.withdraw()  # Hide main window

# Create overlay
overlay = MiniOverlay(None)

print("Testing overlay updates...")

# Test 1: Basic update
print("1. Testing basic update...")
overlay.update_game_state(
    cards=['As', 'Kh'],
    pot=150,
    stack=500,
    decision={'action': 'raise', 'amount': 60, 'reasoning': 'Strong hand with good position'},
    reasoning='Strong hand with good position'
)

time.sleep(3)

# Test 2: Status update
print("2. Testing status update...")
overlay.update_status("🔍 Analyzing...")
time.sleep(2)

# Test 3: Another decision
print("3. Testing another decision...")
overlay.update_game_state(
    cards=['7c', '6h'],
    pot=700,
    stack=450,
    decision={'action': 'fold', 'amount': 0, 'reasoning': 'Weak cards, fold is best'},
    reasoning='Weak cards, fold is best'
)

print("Test complete. Check if overlay updated correctly.")
print("Press Ctrl+C to exit")

try:
    root.mainloop()
except KeyboardInterrupt:
    print("Exiting...")
    root.destroy()
