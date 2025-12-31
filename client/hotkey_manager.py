"""
OnyxPoker Global Hotkeys
"""

import keyboard
import threading

class HotkeyManager:
    def __init__(self, parent_gui):
        self.parent = parent_gui
        self.registered = False
        
    def register_hotkeys(self):
        """Register global hotkeys"""
        if self.registered:
            return
        
        try:
            # Test keyboard library
            print("DEBUG: Testing keyboard library...")
            
            # F5 - Test OCR (debug)
            keyboard.add_hotkey('f5', self.on_f5_test_ocr)
            print("DEBUG: F5 registered")
            
            # F6 - Toggle mini overlay
            keyboard.add_hotkey('f6', self.on_f6_toggle_overlay)
            print("DEBUG: F6 registered")
            
            # F8 - Capture & detect (calibration)
            keyboard.add_hotkey('f8', self.on_f8_calibrate)
            print("DEBUG: F8 registered")
            
            # F9 - Get advice (one-time analysis)
            keyboard.add_hotkey('f9', self.on_f9_advice)
            print("DEBUG: F9 registered")
            
            # F10 - Start/Stop bot (auto mode)
            keyboard.add_hotkey('f10', self.on_f10_toggle_bot)
            print("DEBUG: F10 registered")
            
            # F11 - Emergency stop
            keyboard.add_hotkey('f11', self.on_f11_emergency)
            print("DEBUG: F11 registered")
            
            # F12 - Show/Hide main window
            keyboard.add_hotkey('f12', self.on_f12_toggle_window)
            print("DEBUG: F12 registered")
            
            self.registered = True
            self.parent.log("Hotkeys registered:")
            self.parent.log("   F5 = Test OCR (Debug)")
            self.parent.log("   F6 = Toggle Mini Overlay")
            self.parent.log("   F8 = Capture & Detect (Calibration)")
            self.parent.log("   F9 = Get Advice (one-time)")
            self.parent.log("   F10 = Start/Stop Bot (auto mode)")
            self.parent.log("   F11 = Emergency Stop")
            self.parent.log("   F12 = Toggle Main Window")
            
        except Exception as e:
            self.parent.log(f"Could not register hotkeys: {e}", "WARNING")
            self.parent.log("Try running as administrator for global hotkeys", "INFO")
    
    def unregister_hotkeys(self):
        """Unregister all hotkeys"""
        if not self.registered:
            return
        
        try:
            keyboard.remove_hotkey('f5')
            keyboard.remove_hotkey('f6')
            keyboard.remove_hotkey('f8')
            keyboard.remove_hotkey('f9')
            keyboard.remove_hotkey('f10')
            keyboard.remove_hotkey('f11')
            keyboard.remove_hotkey('f12')
            self.registered = False
            self.parent.log("Hotkeys unregistered")
        except:
            pass
    
    def on_f5_test_ocr(self):
        """F5 - Test OCR (Debug)"""
        try:
            self.parent.log("F5 pressed - Testing OCR...")
            self.parent.root.after(0, self.parent.capture_debug)
            self.parent.root.after(100, self.parent.root.deiconify)
            self.parent.root.after(100, self.parent.root.lift)
            self.parent.root.after(200, lambda: self.parent.notebook.select(2))
        except Exception as e:
            self.parent.log(f"F5 error: {e}", "ERROR")
    
    def on_f6_toggle_overlay(self):
        """F6 - Toggle mini overlay"""
        try:
            if hasattr(self.parent, 'mini_overlay') and self.parent.mini_overlay:
                self.parent.log("F6 pressed - Toggling mini overlay...")
                self.parent.root.after(0, self.parent.mini_overlay.toggle_visibility)
        except Exception as e:
            self.parent.log(f"F6 error: {e}", "ERROR")
    
    def on_f9_advice(self):
        """F9 - Get advice (one-time analysis)"""
        try:
            print("DEBUG: F9 hotkey method called!")
            self.parent.log("F9 pressed - Getting advice...")
            
            # Capture and analyze with decision
            self.parent.root.after(0, self.parent.get_advice)
            
            # Show mini overlay if hidden
            if hasattr(self.parent, 'mini_overlay') and self.parent.mini_overlay:
                self.parent.root.after(100, self.parent.mini_overlay.show)
                
        except Exception as e:
            print(f"DEBUG: F9 error: {e}")
            self.parent.log(f"F9 error: {e}", "ERROR")
    
    def on_f10_toggle_bot(self):
        """F10 - Start/Stop bot (auto mode)"""
        try:
            if self.parent.running:
                self.parent.log("F10 pressed - Stopping bot...")
                self.parent.root.after(0, self.parent.stop_bot)
            else:
                self.parent.log("F10 pressed - Starting bot...")
                self.parent.root.after(0, self.parent.start_bot)
        except Exception as e:
            self.parent.log(f"F10 error: {e}", "ERROR")
    
    def on_f11_emergency(self):
        """F11 - Emergency stop"""
        try:
            self.parent.log("🚨 F11 EMERGENCY STOP!")
            self.parent.root.after(0, self.parent.stop_bot)
            
            # Show main window
            self.parent.root.after(100, self.parent.root.deiconify)
            self.parent.root.after(100, self.parent.root.lift)
            
        except Exception as e:
            self.parent.log(f"F11 error: {e}", "ERROR")
    
    def on_f12_toggle_window(self):
        """F12 - Show/Hide main window"""
        try:
            if self.parent.root.state() == 'withdrawn' or self.parent.root.state() == 'iconic':
                self.parent.log("F12 pressed - Showing main window...")
                self.parent.root.after(0, self.parent.root.deiconify)
                self.parent.root.after(0, self.parent.root.lift)
            else:
                self.parent.log("F12 pressed - Hiding main window...")
                self.parent.root.after(0, self.parent.root.withdraw)
        except Exception as e:
            self.parent.log(f"F12 error: {e}", "ERROR")
    
    def on_f8_calibrate(self):
        """F8 - Capture & detect (calibration)"""
        try:
            print("DEBUG: F8 hotkey method called!")
            self.parent.log("F8 pressed - Capturing and detecting...")
            self.parent.root.after(0, self.parent.auto_detect)
        except Exception as e:
            print(f"DEBUG: F8 error: {e}")
            self.parent.log(f"F8 error: {e}", "ERROR")
