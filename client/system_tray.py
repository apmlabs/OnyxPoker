"""
OnyxPoker System Tray Icon
"""

import pystray
from PIL import Image, ImageDraw
import threading

class SystemTrayIcon:
    def __init__(self, parent_gui):
        self.parent = parent_gui
        self.icon = None
        self.running = False
        
    def create_icon_image(self):
        """Create a simple icon image"""
        # Create 64x64 image
        image = Image.new('RGB', (64, 64), color='black')
        draw = ImageDraw.Draw(image)
        
        # Draw poker chip
        draw.ellipse([8, 8, 56, 56], fill='red', outline='white', width=3)
        draw.ellipse([20, 20, 44, 44], fill='white')
        draw.text((24, 22), "OP", fill='red')
        
        return image
    
    def create_menu(self):
        """Create system tray menu"""
        return pystray.Menu(
            pystray.MenuItem("Show Main Window (F12)", self.show_main),
            pystray.MenuItem("Toggle Mini Overlay (Ctrl+H)", self.toggle_mini),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start Bot (F10)", self.start_bot),
            pystray.MenuItem("Stop Bot (F10)", self.stop_bot),
            pystray.MenuItem("Capture & Analyze (F9)", self.capture),
            pystray.MenuItem("Emergency Stop (F11)", self.emergency_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Hotkeys Help", self.show_hotkeys),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.exit_app)
        )
    
    def show_main(self):
        """Show main GUI window"""
        self.parent.root.deiconify()
        self.parent.root.lift()
    
    def toggle_mini(self):
        """Toggle mini overlay"""
        if hasattr(self.parent, 'mini_overlay') and self.parent.mini_overlay:
            self.parent.mini_overlay.toggle_visibility()
    
    def capture(self):
        """Capture and analyze"""
        self.parent.capture_debug()
    
    def emergency_stop(self):
        """Emergency stop"""
        self.parent.stop_bot()
        self.parent.root.deiconify()
        self.parent.root.lift()
    
    def show_hotkeys(self):
        """Show hotkeys help"""
        import tkinter.messagebox as messagebox
        help_text = """OnyxPoker Global Hotkeys:

F9 - Capture & Analyze
     Take screenshot and get AI decision

F10 - Start/Stop Bot
      Toggle bot automation on/off

F11 - Emergency Stop
      Immediately stop bot and show main window

F12 - Toggle Main Window
      Show/hide the main control window

Ctrl+H - Toggle Mini Overlay
         Show/hide the mini overlay panel

All hotkeys work globally, even when
PokerStars is in focus!"""
        
        self.parent.root.after(0, lambda: messagebox.showinfo("Hotkeys Help", help_text))
    
    def start_bot(self):
        """Start the bot"""
        self.parent.start_bot()
    
    def stop_bot(self):
        """Stop the bot"""
        self.parent.stop_bot()
    
    def exit_app(self):
        """Exit application"""
        self.running = False
        if self.icon:
            self.icon.stop()
        self.parent.root.quit()
    
    def run(self):
        """Run system tray icon"""
        self.running = True
        image = self.create_icon_image()
        menu = self.create_menu()
        
        self.icon = pystray.Icon(
            "OnyxPoker",
            image,
            "OnyxPoker Bot",
            menu
        )
        
        # Run in separate thread
        thread = threading.Thread(target=self.icon.run, daemon=True)
        thread.start()
    
    def update_tooltip(self, text):
        """Update tray icon tooltip"""
        if self.icon:
            self.icon.title = f"OnyxPoker - {text}"
    
    def stop(self):
        """Stop system tray icon"""
        self.running = False
        if self.icon:
            self.icon.stop()
