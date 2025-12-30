#!/usr/bin/env python3
"""
Simple hotkey test - run this to see if keyboard library works
"""

import keyboard
import time

print("Testing keyboard library...")
print("Press F8 or F9 to test (Ctrl+C to exit)")

def test_f8():
    print("🔥 F8 DETECTED!")

def test_f9():
    print("🔥 F9 DETECTED!")

try:
    keyboard.add_hotkey('f8', test_f8)
    keyboard.add_hotkey('f9', test_f9)
    print("Hotkeys registered. Press F8 or F9...")
    
    # Keep running
    keyboard.wait()
    
except KeyboardInterrupt:
    print("Exiting...")
except Exception as e:
    print(f"Error: {e}")
    print("Try running as administrator/sudo")
