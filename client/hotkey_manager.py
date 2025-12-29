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
            # F9 - Capture and analyze
            keyboard.add_hotkey('f9', self.on_f9_capture)
            
            # F10 - Start/Stop bot
            keyboard.add_hotkey('f10', self.on_f10_toggle)
            
            # F11 - Emergency stop
            keyboard.add_hotkey('f11', self.on_f11_emergency)
            
            # F12 - Show/Hide main window
            keyboard.add_hotkey('f12', self.on_f12_toggle_window)
            
            # Ctrl+H - Toggle mini overlay
            keyboard.add_hotkey('ctrl+h', self.on_ctrl_h_toggle_overlay)
            
            self.registered = True
            self.parent.log("✅ Hotkeys registered:")
            self.parent.log("   F9 = Capture & Analyze")
            self.parent.log("   F10 = Start/Stop Bot")
            self.parent.log("   F11 = Emergency Stop")
            self.parent.log("   F12 = Toggle Main Window")
            self.parent.log("   Ctrl+H = Toggle Mini Overlay")
            
        except Exception as e:
            self.parent.log(f"⚠️ Could not register hotkeys: {e}", "WARNING")
            self.parent.log("💡 Try running as administrator for global hotkeys", "INFO")
    
    def unregister_hotkeys(self):
        """Unregister all hotkeys"""
        if not self.registered:
            return
        
        try:
            keyboard.remove_hotkey('f9')
            keyboard.remove_hotkey('f10')
            keyboard.remove_hotkey('f11')
            keyboard.remove_hotkey('f12')
            keyboard.remove_hotkey('ctrl+h')
            self.registered = False
            self.parent.log("Hotkeys unregistered")
        except:
            pass
    
    def on_f9_capture(self):
        """F9 - Capture screenshot and analyze"""
        try:
            self.parent.log("🔥 F9 pressed - Capturing and analyzing...")
            
            # Capture in main thread
            self.parent.root.after(0, self.parent.capture_debug)
            
            # Show mini overlay if hidden
            if hasattr(self.parent, 'mini_overlay') and self.parent.mini_overlay:
                self.parent.root.after(100, self.parent.mini_overlay.show)
                
        except Exception as e:
            self.parent.log(f"❌ F9 error: {e}", "ERROR")
    
    def on_f10_toggle(self):
        """F10 - Start/Stop bot"""
        try:
            if self.parent.running:
                self.parent.log("🔥 F10 pressed - Stopping bot...")
                self.parent.root.after(0, self.parent.stop_bot)
            else:
                self.parent.log("🔥 F10 pressed - Starting bot...")
                self.parent.root.after(0, self.parent.start_bot)
        except Exception as e:
            self.parent.log(f"❌ F10 error: {e}", "ERROR")
    
    def on_f11_emergency(self):
        """F11 - Emergency stop"""
        try:
            self.parent.log("🚨 F11 EMERGENCY STOP!")
            self.parent.root.after(0, self.parent.stop_bot)
            
            # Show main window
            self.parent.root.after(100, self.parent.root.deiconify)
            self.parent.root.after(100, self.parent.root.lift)
            
        except Exception as e:
            self.parent.log(f"❌ F11 error: {e}", "ERROR")
    
    def on_f12_toggle_window(self):
        """F12 - Show/Hide main window"""
        try:
            if self.parent.root.state() == 'withdrawn' or self.parent.root.state() == 'iconic':
                self.parent.log("🔥 F12 pressed - Showing main window...")
                self.parent.root.after(0, self.parent.root.deiconify)
                self.parent.root.after(0, self.parent.root.lift)
            else:
                self.parent.log("🔥 F12 pressed - Hiding main window...")
                self.parent.root.after(0, self.parent.root.withdraw)
        except Exception as e:
            self.parent.log(f"❌ F12 error: {e}", "ERROR")
    
    def on_ctrl_h_toggle_overlay(self):
        """Ctrl+H - Toggle mini overlay"""
        try:
            if hasattr(self.parent, 'mini_overlay') and self.parent.mini_overlay:
                self.parent.log("🔥 Ctrl+H pressed - Toggling mini overlay...")
                self.parent.root.after(0, self.parent.mini_overlay.toggle_visibility)
        except Exception as e:
            self.parent.log(f"❌ Ctrl+H error: {e}", "ERROR")
