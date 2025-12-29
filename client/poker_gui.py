"""
OnyxPoker GUI - Unified control panel with calibration and debug
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import json
from datetime import datetime
from PIL import Image, ImageTk
from poker_bot import OnyxPokerBot
from poker_reader import PokerScreenReader
from automation_client import OnyxPokerClient
from window_detector import WindowDetector
import config
import logging

logger = logging.getLogger(__name__)

class OnyxPokerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OnyxPoker - AI Poker Bot")
        self.root.geometry("1200x800")
        
        # Bot state
        self.bot = None
        self.bot_thread = None
        self.running = False
        self.log_queue = queue.Queue()
        
        # Calibration state
        self.detector = WindowDetector()
        self.selected_window = None
        self.detected_elements = None
        self.windows = []
        
        # Debug state
        self.last_state = {}
        self.last_decision = {}
        self.last_screenshot = None
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create tabs
        self.create_control_tab()
        self.create_calibration_tab()
        self.create_debug_tab()
        
        # Start log updater
        self.update_log()
        
    def create_control_tab(self):
        """Main control panel"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🎮 Control Panel")
        
        # Setup Guide
        guide = ttk.LabelFrame(tab, text="📋 Setup Guide", padding=10)
        guide.pack(fill="x", padx=10, pady=5)
        
        guide_text = tk.Text(guide, height=6, wrap="word", font=("Arial", 9), bg="#f0f0f0")
        guide_text.pack(fill="x")
        guide_text.insert("1.0", 
            "🎯 First Time Setup:\n"
            "1. Run 'python setup_cards.py' in client folder (one-time)\n"
            "2. Go to Calibration tab → Scan Windows → Select poker window\n"
            "3. Click 'Auto-Detect Elements' → Save Config\n"
            "4. Go to Debug tab → Capture Now → Validate State (wait 3 min)\n"
            "5. If validation passes, come back here and Start Bot!\n\n"
            "⚠️ Note: Kiro CLI takes ~15-180 seconds to respond during validation"
        )
        guide_text.config(state="disabled")
        
        # Settings
        settings = ttk.LabelFrame(tab, text="Bot Settings", padding=10)
        settings.pack(fill="x", padx=10, pady=5)
        
        # Mode
        ttk.Label(settings, text="Mode:").grid(row=0, column=0, sticky="w", padx=5)
        self.mode_var = tk.StringVar(value="remote")
        ttk.Radiobutton(settings, text="Remote (Server)", variable=self.mode_var, value="remote").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(settings, text="Local (Kiro CLI)", variable=self.mode_var, value="local").grid(row=0, column=2, sticky="w")
        
        # Execution
        ttk.Label(settings, text="Execution:").grid(row=1, column=0, sticky="w", padx=5)
        self.exec_var = tk.StringVar(value="analysis")
        ttk.Radiobutton(settings, text="Analysis Only", variable=self.exec_var, value="analysis").grid(row=1, column=1, sticky="w")
        ttk.Radiobutton(settings, text="Auto (Clicks)", variable=self.exec_var, value="auto").grid(row=1, column=2, sticky="w")
        
        # Max hands
        ttk.Label(settings, text="Max Hands:").grid(row=2, column=0, sticky="w", padx=5)
        self.hands_var = tk.StringVar(value="")
        ttk.Entry(settings, textvariable=self.hands_var, width=10).grid(row=2, column=1, sticky="w")
        
        # Controls
        controls = ttk.Frame(tab)
        controls.pack(fill="x", padx=10, pady=5)
        
        self.start_btn = ttk.Button(controls, text="▶ Start Bot", command=self.start_bot, width=15)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(controls, text="⏹ Stop Bot", command=self.stop_bot, width=15, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        ttk.Button(controls, text="🔧 Test Connection", command=self.test_connection, width=15).pack(side="left", padx=5)
        ttk.Button(controls, text="📸 Test OCR", command=self.test_ocr, width=15).pack(side="left", padx=5)
        
        # Status
        status = ttk.LabelFrame(tab, text="Status", padding=10)
        status.pack(fill="x", padx=10, pady=5)
        
        self.status_label = ttk.Label(status, text="Status: Idle", font=("Arial", 10, "bold"))
        self.status_label.pack(anchor="w")
        
        self.hands_label = ttk.Label(status, text="Hands: 0")
        self.hands_label.pack(anchor="w")
        
        # Game State
        state_frame = ttk.LabelFrame(tab, text="Current Hand", padding=10)
        state_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Two columns
        left = ttk.Frame(state_frame)
        left.pack(side="left", fill="both", expand=True, padx=10)
        
        right = ttk.Frame(state_frame)
        right.pack(side="left", fill="both", expand=True, padx=10)
        
        # Left - Game info
        ttk.Label(left, text="Your Cards:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.cards_label = ttk.Label(left, text="--", font=("Courier", 14, "bold"))
        self.cards_label.pack(anchor="w", pady=2)
        
        ttk.Label(left, text="Board:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.board_label = ttk.Label(left, text="--", font=("Courier", 12))
        self.board_label.pack(anchor="w", pady=2)
        
        ttk.Label(left, text="Pot:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.pot_label = ttk.Label(left, text="$0", font=("Courier", 12))
        self.pot_label.pack(anchor="w", pady=2)
        
        ttk.Label(left, text="Your Stack:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.stack_label = ttk.Label(left, text="$0", font=("Courier", 12))
        self.stack_label.pack(anchor="w", pady=2)
        
        # Right - Decision
        ttk.Label(right, text="AI Decision:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.decision_label = ttk.Label(right, text="--", font=("Courier", 16, "bold"), foreground="blue")
        self.decision_label.pack(anchor="w", pady=2)
        
        ttk.Label(right, text="Reasoning:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.reasoning_text = tk.Text(right, height=8, width=45, wrap="word", font=("Arial", 9))
        self.reasoning_text.pack(fill="both", expand=True, pady=2)
        
        # Log
        log_frame = ttk.LabelFrame(tab, text="Activity Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap="word", font=("Courier", 9))
        self.log_text.pack(fill="both", expand=True)
        
        log_buttons = ttk.Frame(log_frame)
        log_buttons.pack(anchor="e", pady=5)
        ttk.Button(log_buttons, text="📋 Copy Logs", command=self.copy_logs).pack(side="left", padx=5)
        ttk.Button(log_buttons, text="💾 Save Logs", command=self.save_logs).pack(side="left", padx=5)
        ttk.Button(log_buttons, text="Clear Log", command=self.clear_log).pack(side="left", padx=5)
        
    def create_calibration_tab(self):
        """Calibration wizard tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🔧 Calibration")
        
        # Instructions
        instructions = ttk.LabelFrame(tab, text="📖 Calibration Instructions", padding=10)
        instructions.pack(fill="x", padx=10, pady=5)
        
        inst_text = tk.Text(instructions, height=4, wrap="word", font=("Arial", 9), bg="#fffacd")
        inst_text.pack(fill="x")
        inst_text.insert("1.0",
            "1. Open PokerStars and sit at a table\n"
            "2. Click 'Scan Windows' to find poker window\n"
            "3. Select your poker window from the list\n"
            "4. Click 'Auto-Detect Elements' to find buttons/pot (uses computer vision)\n"
            "5. Review the preview and click 'Save Config' if it looks good\n"
            "6. Go to Debug tab to validate with Kiro CLI"
        )
        inst_text.config(state="disabled")
        
        # Step 1: Window Selection
        step1 = ttk.LabelFrame(tab, text="Step 1: Find Poker Window", padding=10)
        step1.pack(fill="x", padx=10, pady=5)
        
        self.window_list = tk.Listbox(step1, height=4, font=("Arial", 10))
        self.window_list.pack(fill="x", pady=5)
        
        btn_frame1 = ttk.Frame(step1)
        btn_frame1.pack(fill="x")
        
        ttk.Button(btn_frame1, text="🔍 Scan Windows", command=self.scan_windows).pack(side="left", padx=5)
        ttk.Button(btn_frame1, text="✓ Select", command=self.select_window).pack(side="left", padx=5)
        
        if not self.detector.can_capture_background:
            ttk.Label(step1, text="⚠️ Window must be visible (not minimized)", 
                     foreground="orange", font=("Arial", 9, "italic")).pack(pady=5)
        
        # Step 2: Auto-Detect
        step2 = ttk.LabelFrame(tab, text="Step 2: Auto-Detect Elements", padding=10)
        step2.pack(fill="x", padx=10, pady=5)
        
        self.calib_status = ttk.Label(step2, text="Select window first", foreground="gray")
        self.calib_status.pack(pady=5)
        
        ttk.Button(step2, text="🔎 Auto-Detect", command=self.auto_detect).pack(pady=5)
        
        # Step 3: Preview
        step3 = ttk.LabelFrame(tab, text="Step 3: Verify Detection", padding=10)
        step3.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.preview_canvas = tk.Canvas(step3, bg="black", height=300)
        self.preview_canvas.pack(fill="both", expand=True, pady=5)
        
        self.confidence_label = ttk.Label(step3, text="Confidence: --", font=("Arial", 10, "bold"))
        self.confidence_label.pack(pady=5)
        
        # Step 4: Save
        step4 = ttk.Frame(tab)
        step4.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(step4, text="💾 Save Configuration", command=self.save_calibration).pack(fill="x", pady=5)
        
    def create_debug_tab(self):
        """Debug and analysis tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🐛 Debug")
        
        # Screenshot preview
        preview_frame = ttk.LabelFrame(tab, text="Table Screenshot", padding=10)
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.debug_canvas = tk.Canvas(preview_frame, bg="black", height=300)
        self.debug_canvas.pack(fill="both", expand=True)
        
        ttk.Button(preview_frame, text="📸 Capture Now", command=self.capture_debug).pack(pady=5)
        
        # Kiro Validation Panel
        kiro_frame = ttk.LabelFrame(tab, text="🤖 Kiro CLI Validation", padding=10)
        kiro_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(kiro_frame, text="✓ Validate State", command=self.validate_with_kiro).pack(side="left", padx=5)
        ttk.Button(kiro_frame, text="✓ Validate UI", command=self.validate_ui_with_kiro).pack(side="left", padx=5)
        
        self.kiro_status = ttk.Label(kiro_frame, text="Not validated", foreground="gray")
        self.kiro_status.pack(side="left", padx=10)
        
        # Card Validation Panel (NEW)
        card_val_frame = ttk.LabelFrame(tab, text="🎴 Card Validation & Learning", padding=10)
        card_val_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(card_val_frame, text="Detected Cards:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.detected_cards_label = ttk.Label(card_val_frame, text="--", font=("Courier", 14, "bold"))
        self.detected_cards_label.pack(anchor="w", pady=5)
        
        btn_frame = ttk.Frame(card_val_frame)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="✓ Correct", command=self.confirm_cards, 
                  style="success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✗ Wrong - Let Me Fix", command=self.open_card_correction,
                  style="warning.TButton").pack(side="left", padx=5)
        
        self.card_validation_status = ttk.Label(card_val_frame, text="", foreground="gray")
        self.card_validation_status.pack(anchor="w", pady=5)
        
        # OCR Results
        ocr_frame = ttk.LabelFrame(tab, text="OCR Analysis", padding=10)
        ocr_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.ocr_text = scrolledtext.ScrolledText(ocr_frame, height=8, wrap="word", font=("Courier", 9))
        self.ocr_text.pack(fill="both", expand=True)
        
        ttk.Button(ocr_frame, text="📋 Copy OCR", command=self.copy_ocr).pack(anchor="e", pady=2)
        
        # Raw State
        state_frame = ttk.LabelFrame(tab, text="Raw Game State (JSON)", padding=10)
        state_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.state_text = scrolledtext.ScrolledText(state_frame, height=6, wrap="word", font=("Courier", 9))
        self.state_text.pack(fill="both", expand=True)
        
        ttk.Button(state_frame, text="📋 Copy State", command=self.copy_state).pack(anchor="e", pady=2)
        
    # Logging
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {level}: {message}")
        
    def update_log(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
        except queue.Empty:
            pass
        self.root.after(100, self.update_log)
        
    def clear_log(self):
        self.log_text.delete("1.0", "end")
        
    def copy_logs(self):
        """Copy all logs to clipboard"""
        logs = self.log_text.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(logs)
        self.root.update()
        messagebox.showinfo("Copied", "Logs copied to clipboard!")
        
    def save_logs(self):
        """Save logs to file"""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"onyxpoker_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filename:
            try:
                logs = self.log_text.get("1.0", "end-1c")
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(logs)
                messagebox.showinfo("Saved", f"Logs saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save logs:\n{str(e)}")
    
    def copy_ocr(self):
        """Copy OCR analysis to clipboard"""
        ocr = self.ocr_text.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(ocr)
        self.root.update()
        messagebox.showinfo("Copied", "OCR analysis copied to clipboard!")
    
    def copy_state(self):
        """Copy game state to clipboard"""
        state = self.state_text.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(state)
        self.root.update()
        messagebox.showinfo("Copied", "Game state copied to clipboard!")
        
    # Status updates
    def update_status(self, status, hands=None):
        self.status_label.config(text=f"Status: {status}")
        if hands is not None:
            self.hands_label.config(text=f"Hands: {hands}")
            
    def update_game_state(self, state, decision=None):
        # Store for debug
        self.last_state = state
        if decision:
            self.last_decision = decision
        
        # Update display
        cards = ', '.join(state.get('hero_cards', ['??', '??']))
        self.cards_label.config(text=cards)
        
        board = ', '.join(state.get('community_cards', [])) or "None"
        self.board_label.config(text=board)
        
        pot = state.get('pot', 0)
        self.pot_label.config(text=f"${pot}")
        
        stacks = state.get('stacks', [])
        stack = stacks[2] if len(stacks) > 2 else 0
        self.stack_label.config(text=f"${stack}")
        
        if decision:
            action = decision.get('action', '--').upper()
            amount = decision.get('amount', 0)
            if amount > 0:
                action += f" ${amount}"
            self.decision_label.config(text=action)
            
            reasoning = decision.get('reasoning', 'No reasoning')
            self.reasoning_text.delete("1.0", "end")
            self.reasoning_text.insert("1.0", reasoning)
        
        # Update debug tab
        self.state_text.delete("1.0", "end")
        self.state_text.insert("1.0", json.dumps(state, indent=2))
        
    # Control actions
    def test_connection(self):
        self.log("Testing server connection...")
        try:
            client = OnyxPokerClient()
            if client.test_connection():
                self.log("✅ Connected!", "SUCCESS")
                messagebox.showinfo("Success", "Server connected!")
            else:
                self.log("❌ Failed", "ERROR")
                messagebox.showerror("Error", "Cannot connect")
        except Exception as e:
            self.log(f"❌ Error: {e}", "ERROR")
            messagebox.showerror("Error", str(e))
            
    def test_ocr(self):
        self.log("Testing OCR...")
        try:
            reader = PokerScreenReader()
            state = reader.parse_game_state()
            self.log(f"OCR: Pot=${state['pot']}, Stacks={state['stacks']}")
            self.update_game_state(state)
            
            # Update OCR debug
            self.ocr_text.delete("1.0", "end")
            self.ocr_text.insert("1.0", f"Pot: ${state['pot']}\n")
            self.ocr_text.insert("end", f"Stacks: {state['stacks']}\n")
            self.ocr_text.insert("end", f"Actions: {state['actions']}\n")
            self.ocr_text.insert("end", f"Cards: {state['hero_cards']}\n")
            
            messagebox.showinfo("OCR Test", f"Pot: ${state['pot']}\nCheck Debug tab for details")
        except Exception as e:
            self.log(f"❌ OCR error: {e}", "ERROR")
            messagebox.showerror("Error", str(e))
            
    def start_bot(self):
        if self.running:
            return
            
        mode = self.mode_var.get()
        execution = self.exec_var.get()
        max_hands = self.hands_var.get()
        max_hands = int(max_hands) if max_hands else None
        
        self.log(f"Starting: mode={mode}, exec={execution}, hands={max_hands}")
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.update_status("Running", 0)
        
        self.bot_thread = threading.Thread(target=self.run_bot, args=(mode, execution, max_hands), daemon=True)
        self.bot_thread.start()
        
    def stop_bot(self):
        self.log("Stopping...")
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.update_status("Stopped")
        
    def run_bot(self, mode, execution, max_hands):
        try:
            bot = OnyxPokerBot(mode=mode, execution=execution)
            reader = bot.reader
            hands = 0
            
            while self.running and (max_hands is None or hands < max_hands):
                if not reader.is_hero_turn():
                    self.root.after(0, self.update_status, "Waiting", hands)
                    import time
                    time.sleep(config.POLL_INTERVAL)
                    continue
                
                state = reader.parse_game_state()
                self.log(f"Hand {hands+1}: Pot=${state['pot']}")
                
                decision = bot.get_decision(state)
                self.log(f"Decision: {decision['action'].upper()}")
                
                self.root.after(0, self.update_game_state, state, decision)
                self.root.after(0, self.update_status, "Playing", hands+1)
                
                if execution == 'auto':
                    bot.execute_action(decision)
                    self.log(f"✅ Executed: {decision['action']}")
                
                hands += 1
                import time
                time.sleep(config.ACTION_DELAY)
                
            self.log(f"Finished: {hands} hands")
            self.root.after(0, self.update_status, "Finished", hands)
            
        except Exception as e:
            self.log(f"❌ Error: {e}", "ERROR")
            self.root.after(0, messagebox.showerror, "Error", str(e))
        finally:
            self.running = False
            self.root.after(0, self.start_btn.config, {"state": "normal"})
            self.root.after(0, self.stop_btn.config, {"state": "disabled"})
    
    # Calibration actions
    def scan_windows(self):
        self.window_list.delete(0, tk.END)
        self.calib_status.config(text="Scanning...", foreground="blue")
        self.root.update()
        
        self.windows = self.detector.find_poker_windows()
        
        if not self.windows:
            self.calib_status.config(text="❌ No windows found", foreground="red")
            messagebox.showwarning("No Windows", "No poker windows detected.\nOpen PokerStars and try again.")
            return
        
        for i, win in enumerate(self.windows):
            self.window_list.insert(tk.END, f"{i+1}. {win['title']} ({win['width']}x{win['height']})")
        
        self.calib_status.config(text=f"✓ Found {len(self.windows)} window(s)", foreground="green")
    
    def select_window(self):
        sel = self.window_list.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a window first")
            return
        
        self.selected_window = self.windows[sel[0]]
        
        if self.detector.activate_window(self.selected_window):
            self.calib_status.config(text=f"✓ Selected: {self.selected_window['title']}", foreground="green")
        else:
            self.calib_status.config(text="❌ Failed to activate", foreground="red")
    
    def auto_detect(self):
        if not self.selected_window:
            messagebox.showwarning("No Window", "Select window first")
            return
        
        self.calib_status.config(text="🔎 Detecting...", foreground="blue")
        self.root.update()
        
        try:
            img = self.detector.capture_window(self.selected_window)
            self.detected_elements = self.detector.detect_poker_elements(img)
            
            valid, msg = self.detector.validate_elements(self.detected_elements)
            
            if valid:
                self.calib_status.config(text=f"✓ {msg}", foreground="green")
                preview = self.detector.create_preview(img, self.detected_elements)
                self.show_preview(preview, self.preview_canvas)
                
                conf = self.detected_elements.get('confidence', 0)
                self.confidence_label.config(text=f"Confidence: {conf:.1%}", 
                                            foreground="green" if conf > 0.7 else "orange")
            else:
                self.calib_status.config(text=f"❌ {msg}", foreground="red")
                messagebox.showerror("Detection Failed", msg)
        
        except Exception as e:
            self.calib_status.config(text=f"❌ Error: {e}", foreground="red")
    
    def save_calibration(self):
        if not self.detected_elements:
            messagebox.showwarning("No Detection", "Run auto-detect first")
            return
        
        valid, msg = self.detector.validate_elements(self.detected_elements)
        if not valid:
            messagebox.showerror("Invalid", msg)
            return
        
        try:
            content = f'''"""Auto-generated configuration"""

TABLE_REGION = ({self.selected_window['left']}, {self.selected_window['top']}, 
                {self.selected_window['width']}, {self.selected_window['height']})

BUTTON_REGIONS = {{
'''
            for name, region in self.detected_elements['button_regions'].items():
                x, y, w, h = region
                content += f'    "{name}": ({x}, {y}, {w}, {h}),\n'
            
            content += '}\n\n'
            
            if self.detected_elements.get('pot_region'):
                x, y, w, h = self.detected_elements['pot_region']
                content += f'POT_REGION = ({x}, {y}, {w}, {h})\n\n'
            
            content += '''HOLE_CARD_REGIONS = [(350, 500, 50, 70), (420, 500, 50, 70)]
STACK_REGIONS = [(200, 150, 80, 30), (600, 150, 80, 30), (700, 350, 80, 30), 
                 (600, 550, 80, 30), (200, 550, 80, 30), (100, 350, 80, 30)]
POLL_INTERVAL = 0.5
ACTION_DELAY = 2.0
'''
            
            with open('config.py', 'w') as f:
                f.write(content)
            
            messagebox.showinfo("Success", "Configuration saved!")
            self.log("✅ Calibration saved to config.py", "SUCCESS")
        
        except Exception as e:
            messagebox.showerror("Save Failed", str(e))
    
    # Debug actions
    def capture_debug(self):
        try:
            reader = PokerScreenReader()
            img = reader.capture_screenshot()
            
            # Decode base64 to image
            import base64
            import io
            img_data = base64.b64decode(img)
            pil_img = Image.open(io.BytesIO(img_data))
            
            self.last_screenshot = pil_img
            self.show_preview(pil_img, self.debug_canvas)
            
            # Run OCR
            state = reader.parse_game_state()
            self.last_state = state
            
            # Update detected cards display
            cards = state.get('hero_cards', ['??', '??'])
            self.detected_cards_label.config(text=f"{cards[0]}, {cards[1]}")
            
            self.ocr_text.delete("1.0", "end")
            self.ocr_text.insert("1.0", f"Pot: ${state['pot']}\n")
            self.ocr_text.insert("end", f"Stacks: {state['stacks']}\n")
            self.ocr_text.insert("end", f"Actions: {state['actions']}\n")
            self.ocr_text.insert("end", f"Cards: {state['hero_cards']}\n")
            self.ocr_text.insert("end", f"Board: {state['community_cards']}\n")
            
            # Update state display
            self.state_text.delete("1.0", "end")
            self.state_text.insert("1.0", json.dumps(state, indent=2))
            
            self.log("📸 Debug capture complete")
        except Exception as e:
            self.log(f"❌ Capture error: {e}", "ERROR")
            img_data = base64.b64decode(img)
            pil_img = Image.open(io.BytesIO(img_data))
            
            self.last_screenshot = pil_img
            self.show_preview(pil_img, self.debug_canvas)
            
            # Run OCR
            state = reader.parse_game_state()
            self.last_state = state
            self.ocr_text.delete("1.0", "end")
            self.ocr_text.insert("1.0", f"Pot: ${state['pot']}\n")
            self.ocr_text.insert("end", f"Stacks: {state['stacks']}\n")
            self.ocr_text.insert("end", f"Actions: {state['actions']}\n")
            self.ocr_text.insert("end", f"Cards: {state['hero_cards']}\n")
            self.ocr_text.insert("end", f"Board: {state['community_cards']}\n")
            
            self.log("📸 Debug capture complete")
        except Exception as e:
            self.log(f"❌ Capture error: {e}", "ERROR")
    
    def validate_with_kiro(self):
        """Validate current table state with Kiro CLI"""
        if not self.last_state:
            messagebox.showwarning("No State", "Please capture a screenshot first using '📸 Capture Now' button")
            return
        
        # Create progress window
        progress = tk.Toplevel(self.root)
        progress.title("Kiro Validation")
        progress.geometry("400x150")
        progress.transient(self.root)
        progress.grab_set()
        
        ttk.Label(progress, text="🤖 Validating with Kiro CLI...", font=("Arial", 12, "bold")).pack(pady=10)
        ttk.Label(progress, text="This may take 15-180 seconds", font=("Arial", 10)).pack(pady=5)
        ttk.Label(progress, text="Kiro is loading and analyzing the poker state", font=("Arial", 9)).pack(pady=5)
        
        progress_bar = ttk.Progressbar(progress, mode='indeterminate', length=300)
        progress_bar.pack(pady=10)
        progress_bar.start(10)
        
        status_label = ttk.Label(progress, text="Please wait...", font=("Arial", 9), foreground="blue")
        status_label.pack(pady=5)
        
        self.log("🤖 Validating state with Kiro CLI (this may take up to 3 minutes)...")
        self.kiro_status.config(text="⏳ Validating...", foreground="orange")
        self.root.update()
        
        def run_validation():
            try:
                from kiro_validator import KiroValidator
                validator = KiroValidator()
                result = validator.validate_table_state(self.last_state)
                
                progress.after(0, lambda: progress_bar.stop())
                progress.after(0, lambda: progress.destroy())
                
                if result['understood']:
                    self.kiro_status.config(text=f"✓ Valid (conf: {result['confidence']:.2f})", foreground="green")
                    self.log(f"✅ Kiro validated: {result['interpretation'][:100]}", "SUCCESS")
                else:
                    self.kiro_status.config(text="✗ Invalid", foreground="red")
                    self.log(f"⚠️ Kiro concerns: {result['concerns']}", "WARNING")
                
                # Show detailed response
                msg = f"Valid: {result['understood']}\n"
                msg += f"Confidence: {result['confidence']:.2f}\n"
                msg += f"Concerns: {', '.join(result['concerns'])}\n\n"
                msg += f"Interpretation:\n{result['interpretation']}"
                
                messagebox.showinfo("Kiro Validation", msg)
            except Exception as e:
                progress.after(0, lambda: progress_bar.stop())
                progress.after(0, lambda: progress.destroy())
                self.kiro_status.config(text="✗ Error", foreground="red")
                self.log(f"❌ Validation error: {e}", "ERROR")
                messagebox.showerror("Error", f"Validation failed:\n{str(e)}\n\nMake sure Kiro CLI is installed and accessible.")
        
        # Run in thread to keep UI responsive
        import threading
        thread = threading.Thread(target=run_validation, daemon=True)
        thread.start()
    
    def confirm_cards(self):
        """User confirms detected cards are correct"""
        if not self.last_state or not self.last_state.get('hero_cards'):
            messagebox.showwarning("No Cards", "Capture a screenshot first")
            return
        
        cards = self.last_state['hero_cards']
        if '??' in cards:
            messagebox.showinfo("Unknown Cards", "Cards were not detected. Please use 'Wrong - Let Me Fix' to teach the system.")
            return
        
        self.card_validation_status.config(text="✅ Cards confirmed correct", foreground="green")
        self.log(f"✅ User confirmed cards: {cards}", "SUCCESS")
    
    def open_card_correction(self):
        """Open dialog to correct detected cards and save real templates"""
        if not self.last_state:
            messagebox.showwarning("No State", "Capture a screenshot first")
            return
        
        # Create correction dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Correct Card Detection")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="What are the actual cards?", font=("Arial", 12, "bold")).pack(pady=10)
        
        detected = self.last_state.get('hero_cards', ['??', '??'])
        ttk.Label(dialog, text=f"Bot detected: {', '.join(detected)}", font=("Arial", 10)).pack(pady=5)
        
        # Card 1
        frame1 = ttk.Frame(dialog)
        frame1.pack(pady=10)
        
        ttk.Label(frame1, text="Card 1:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        ranks = ['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2']
        suits = ['♠ (s)', '♥ (h)', '♦ (d)', '♣ (c)']
        
        rank1_var = tk.StringVar(value='A')
        suit1_var = tk.StringVar(value='♠ (s)')
        
        ttk.Combobox(frame1, textvariable=rank1_var, values=ranks, width=5, state="readonly").pack(side="left", padx=5)
        ttk.Combobox(frame1, textvariable=suit1_var, values=suits, width=8, state="readonly").pack(side="left", padx=5)
        
        # Card 2
        frame2 = ttk.Frame(dialog)
        frame2.pack(pady=10)
        
        ttk.Label(frame2, text="Card 2:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        rank2_var = tk.StringVar(value='K')
        suit2_var = tk.StringVar(value='♥ (h)')
        
        ttk.Combobox(frame2, textvariable=rank2_var, values=ranks, width=5, state="readonly").pack(side="left", padx=5)
        ttk.Combobox(frame2, textvariable=suit2_var, values=suits, width=8, state="readonly").pack(side="left", padx=5)
        
        def save_correction():
            # Get corrected cards
            suit_map = {'♠ (s)': 's', '♥ (h)': 'h', '♦ (d)': 'd', '♣ (c)': 'c'}
            card1 = rank1_var.get() + suit_map[suit1_var.get()]
            card2 = rank2_var.get() + suit_map[suit2_var.get()]
            
            self.log(f"📝 User corrected cards to: {card1}, {card2}")
            
            # Capture and save real card images
            try:
                from poker_reader import PokerScreenReader
                from card_matcher import CardMatcher
                import config
                import cv2
                import numpy as np
                
                reader = PokerScreenReader()
                matcher = CardMatcher()
                
                # Capture card regions
                for i, (region, card_name) in enumerate(zip(config.HOLE_CARD_REGIONS, [card1, card2])):
                    img = reader.capture_region(region)
                    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    
                    # Save as real template
                    matcher.save_real_card(img_cv, card_name)
                    self.log(f"✅ Saved real template for {card_name}")
                
                self.card_validation_status.config(text=f"✅ Learned: {card1}, {card2}", foreground="green")
                messagebox.showinfo("Success", f"Saved real card templates!\n\n{card1}, {card2}\n\nNext time these cards appear, recognition will be more accurate.")
                dialog.destroy()
                
            except Exception as e:
                self.log(f"❌ Error saving cards: {e}", "ERROR")
                messagebox.showerror("Error", f"Failed to save cards:\n{str(e)}")
        
        ttk.Button(dialog, text="💾 Save & Learn", command=save_correction).pack(pady=20)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=5)
    
    def validate_ui_with_kiro(self):
        """Validate UI detection with Kiro CLI"""
        if not self.detected_elements:
            messagebox.showwarning("No Detection", 
                "Please run calibration first:\n\n"
                "1. Go to Calibration tab\n"
                "2. Click 'Scan Windows'\n"
                "3. Select poker window\n"
                "4. Click 'Auto-Detect Elements'\n"
                "5. Then come back here to validate")
            return
        
        self.log("🤖 Validating UI with Kiro CLI (this may take up to 3 minutes)...")
        self.kiro_status.config(text="⏳ Validating...", foreground="orange")
        self.root.update()
        
        try:
            from kiro_validator import KiroValidator
            validator = KiroValidator()
            result = validator.validate_ui_detection(self.detected_elements)
            
            if result['valid']:
                self.kiro_status.config(text="✓ UI Valid", foreground="green")
                self.log("✅ Kiro validated UI layout", "SUCCESS")
            else:
                self.kiro_status.config(text="✗ UI Invalid", foreground="red")
                self.log(f"⚠️ UI concerns: {result['concerns']}", "WARNING")
            
            messagebox.showinfo("UI Validation", result['response'])
        except Exception as e:
            self.kiro_status.config(text="✗ Error", foreground="red")
            self.log(f"❌ Validation error: {e}", "ERROR")
            messagebox.showerror("Error", f"Validation failed:\n{str(e)}\n\nMake sure Kiro CLI is installed and accessible.")
    
    def show_preview(self, img, canvas):
        """Display image on canvas"""
        canvas_w = canvas.winfo_width()
        canvas_h = canvas.winfo_height()
        
        if canvas_w < 100:
            canvas_w, canvas_h = 800, 300
        
        img_copy = img.copy()
        img_copy.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
        
        photo = ImageTk.PhotoImage(img_copy)
        canvas.delete('all')
        canvas.create_image(canvas_w//2, canvas_h//2, image=photo, anchor=tk.CENTER)
        canvas.image = photo

def main():
    logging.basicConfig(level=logging.INFO)
    root = tk.Tk()
    app = OnyxPokerGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
