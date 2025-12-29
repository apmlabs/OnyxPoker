"""
Calibration UI - Interactive window detection and element confirmation
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
from window_detector import WindowDetector
import config
import logging

logger = logging.getLogger(__name__)

class CalibrationUI:
    """Interactive calibration interface"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OnyxPoker - Auto Calibration")
        self.root.geometry("900x700")
        
        self.detector = WindowDetector()
        self.selected_window = None
        self.detected_elements = None
        self.preview_image = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Create UI layout"""
        
        # Header
        header = tk.Frame(self.root, bg='#2c3e50', height=60)
        header.pack(fill=tk.X)
        
        title = tk.Label(header, text="🎰 Auto-Calibration Wizard", 
                        font=('Arial', 18, 'bold'), bg='#2c3e50', fg='white')
        title.pack(pady=15)
        
        # Main content
        content = tk.Frame(self.root)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Step 1: Window Selection
        step1 = tk.LabelFrame(content, text="Step 1: Select Poker Window", 
                             font=('Arial', 12, 'bold'), padx=10, pady=10)
        step1.pack(fill=tk.X, pady=(0, 10))
        
        self.window_list = tk.Listbox(step1, height=4, font=('Arial', 10))
        self.window_list.pack(fill=tk.X, pady=5)
        
        btn_frame1 = tk.Frame(step1)
        btn_frame1.pack(fill=tk.X)
        
        tk.Button(btn_frame1, text="🔍 Scan for Windows", 
                 command=self.scan_windows, bg='#3498db', fg='white',
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame1, text="✓ Select Window", 
                 command=self.select_window, bg='#2ecc71', fg='white',
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        # Background capture warning
        if not self.detector.can_capture_background:
            warning = tk.Label(step1, 
                             text="⚠️ Window must be visible (not minimized) for capture",
                             fg='orange', font=('Arial', 9, 'italic'))
            warning.pack(pady=5)
        
        # Step 2: Auto-Detection
        step2 = tk.LabelFrame(content, text="Step 2: Auto-Detect Elements", 
                             font=('Arial', 12, 'bold'), padx=10, pady=10)
        step2.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = tk.Label(step2, text="Select a window first", 
                                    font=('Arial', 10), fg='gray')
        self.status_label.pack(pady=5)
        
        tk.Button(step2, text="🔎 Auto-Detect Elements", 
                 command=self.auto_detect, bg='#9b59b6', fg='white',
                 font=('Arial', 10, 'bold')).pack(pady=5)
        
        # Step 3: Preview
        step3 = tk.LabelFrame(content, text="Step 3: Verify Detection", 
                             font=('Arial', 12, 'bold'), padx=10, pady=10)
        step3.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Preview canvas
        self.preview_canvas = tk.Canvas(step3, bg='black', height=300)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Confidence indicator
        self.confidence_label = tk.Label(step3, text="Confidence: --", 
                                        font=('Arial', 10, 'bold'))
        self.confidence_label.pack(pady=5)
        
        # Step 4: Save
        step4 = tk.Frame(content)
        step4.pack(fill=tk.X)
        
        tk.Button(step4, text="💾 Save Configuration", 
                 command=self.save_config, bg='#27ae60', fg='white',
                 font=('Arial', 12, 'bold'), height=2).pack(side=tk.LEFT, 
                                                            fill=tk.X, expand=True, padx=5)
        
        tk.Button(step4, text="✖ Cancel", 
                 command=self.root.quit, bg='#e74c3c', fg='white',
                 font=('Arial', 12, 'bold'), height=2).pack(side=tk.LEFT, 
                                                            fill=tk.X, expand=True, padx=5)
    
    def scan_windows(self):
        """Scan for poker windows"""
        self.window_list.delete(0, tk.END)
        self.status_label.config(text="Scanning...", fg='blue')
        self.root.update()
        
        windows = self.detector.find_poker_windows()
        
        if not windows:
            self.status_label.config(text="❌ No poker windows found", fg='red')
            messagebox.showwarning("No Windows", 
                                  "No poker windows detected.\n\n"
                                  "Please:\n"
                                  "1. Open PokerStars\n"
                                  "2. Join a table\n"
                                  "3. Make sure window is visible\n"
                                  "4. Try scanning again")
            return
        
        for i, win in enumerate(windows):
            self.window_list.insert(tk.END, 
                f"{i+1}. {win['title']} ({win['width']}x{win['height']})")
        
        self.windows = windows
        self.status_label.config(text=f"✓ Found {len(windows)} window(s)", fg='green')
    
    def select_window(self):
        """Select window from list"""
        selection = self.window_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a window first")
            return
        
        idx = selection[0]
        self.selected_window = self.windows[idx]
        
        # Activate window
        if self.detector.activate_window(self.selected_window):
            self.status_label.config(
                text=f"✓ Selected: {self.selected_window['title']}", 
                fg='green')
        else:
            self.status_label.config(text="❌ Failed to activate window", fg='red')
    
    def auto_detect(self):
        """Auto-detect poker elements"""
        if not self.selected_window:
            messagebox.showwarning("No Window", "Please select a window first")
            return
        
        self.status_label.config(text="🔎 Detecting elements...", fg='blue')
        self.root.update()
        
        try:
            # Capture window
            img = self.detector.capture_window(self.selected_window)
            
            # Detect elements
            self.detected_elements = self.detector.detect_poker_elements(img)
            
            # Validate
            valid, message = self.detector.validate_elements(self.detected_elements)
            
            if valid:
                self.status_label.config(text=f"✓ {message}", fg='green')
                
                # Create preview
                self.preview_image = self.detector.create_preview(img, self.detected_elements)
                self.show_preview()
                
                # Update confidence
                conf = self.detected_elements.get('confidence', 0)
                self.confidence_label.config(
                    text=f"Confidence: {conf:.1%}",
                    fg='green' if conf > 0.7 else 'orange'
                )
            else:
                self.status_label.config(text=f"❌ {message}", fg='red')
                messagebox.showerror("Detection Failed", 
                                   f"{message}\n\n"
                                   "Please:\n"
                                   "1. Make sure you're at a poker table\n"
                                   "2. Window is fully visible\n"
                                   "3. Table is not minimized\n"
                                   "4. Try again")
        
        except Exception as e:
            logger.error(f"Detection error: {e}")
            self.status_label.config(text=f"❌ Error: {str(e)}", fg='red')
    
    def show_preview(self):
        """Display preview image"""
        if not self.preview_image:
            return
        
        # Resize to fit canvas
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        if canvas_width < 100:  # Not rendered yet
            canvas_width = 800
            canvas_height = 300
        
        img = self.preview_image.copy()
        img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(img)
        
        # Display
        self.preview_canvas.delete('all')
        self.preview_canvas.create_image(
            canvas_width//2, canvas_height//2, 
            image=photo, anchor=tk.CENTER
        )
        self.preview_canvas.image = photo  # Keep reference
    
    def save_config(self):
        """Save configuration to config.py"""
        if not self.detected_elements:
            messagebox.showwarning("No Detection", 
                                  "Please run auto-detection first")
            return
        
        valid, message = self.detector.validate_elements(self.detected_elements)
        if not valid:
            messagebox.showerror("Invalid Configuration", message)
            return
        
        try:
            # Build config content
            config_content = f'''"""
Configuration for OnyxPoker bot
Auto-generated by calibration wizard
"""

# Table window region (x, y, width, height)
TABLE_REGION = ({self.selected_window['left']}, {self.selected_window['top']}, 
                {self.selected_window['width']}, {self.selected_window['height']})

# Action buttons
BUTTON_REGIONS = {{
'''
            
            for name, region in self.detected_elements['button_regions'].items():
                x, y, w, h = region
                config_content += f'    "{name}": ({x}, {y}, {w}, {h}),\n'
            
            config_content += '}\n\n'
            
            # Pot region
            if self.detected_elements.get('pot_region'):
                x, y, w, h = self.detected_elements['pot_region']
                config_content += f'POT_REGION = ({x}, {y}, {w}, {h})\n\n'
            
            # Placeholder regions
            config_content += '''# Hole cards (placeholder - adjust manually)
HOLE_CARD_REGIONS = [
    (350, 500, 50, 70),
    (420, 500, 50, 70),
]

# Stack regions (placeholder - adjust manually)
STACK_REGIONS = [
    (200, 150, 80, 30),  # Seat 1
    (600, 150, 80, 30),  # Seat 2
    (700, 350, 80, 30),  # Seat 3 (hero)
    (600, 550, 80, 30),  # Seat 4
    (200, 550, 80, 30),  # Seat 5
    (100, 350, 80, 30),  # Seat 6
]

# Timing
POLL_INTERVAL = 0.5
ACTION_DELAY = 2.0
'''
            
            # Write to file
            with open('config.py', 'w') as f:
                f.write(config_content)
            
            messagebox.showinfo("Success", 
                              "Configuration saved to config.py!\n\n"
                              "You can now use the poker bot.")
            self.root.quit()
        
        except Exception as e:
            logger.error(f"Save error: {e}")
            messagebox.showerror("Save Failed", f"Error: {str(e)}")
    
    def run(self):
        """Start UI"""
        self.root.mainloop()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = CalibrationUI()
    app.run()
