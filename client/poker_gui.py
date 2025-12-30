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
import pygetwindow as gw
from poker_bot import OnyxPokerBot
from poker_reader import PokerScreenReader
from automation_client import OnyxPokerClient
from mini_overlay import MiniOverlay
from hotkey_manager import HotkeyManager
from system_tray import SystemTrayIcon
import config
import logging

logger = logging.getLogger(__name__)

class OnyxPokerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OnyxPoker - AI Poker Bot")
        
        # Window geometry persistence
        self.geometry_file = "window_geometry.txt"
        self.saved_geometry = None
        
        # Load saved geometry or maximize
        self.load_window_geometry()
        
        # Track geometry changes
        self.root.bind('<Configure>', self.on_window_configure)
        
        # Bot state
        self.bot = None
        self.bot_thread = None
        self.running = False
        self.log_queue = queue.Queue()
        
        # Calibration state
        self.selected_window = None
        self.detected_elements = None
        self.windows = []
        
        # Debug state
        self.last_state = {}
        self.last_decision = {}
        self.last_screenshot = None
        
        # Mini overlay and hotkeys
        self.mini_overlay = None
        self.hotkey_manager = None
        self.system_tray = None
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create tabs
        self.create_control_tab()
        self.create_calibration_tab()
        self.create_debug_tab()
        self.create_help_tab()
        
        # Initialize mini overlay, hotkeys, system tray
        self.init_advanced_features()
        
        # Check setup status and update overlay
        self.check_setup_status()
        
        # Auto-hide main window after 2 seconds (only if already calibrated)
        self.root.after(2000, self.auto_hide_window)
        
        # Start log updater
        self.update_log()
    
    def auto_hide_window(self):
        """Auto-hide main window after launch (only if calibrated)"""
        # Disabled - user will hide manually with F12 when needed
        pass
    
    def check_setup_status(self):
        """Check setup status and update overlay guidance"""
        try:
            import os
            # Check if config exists and is calibrated
            if os.path.exists('config.py'):
                try:
                    import config
                    # Check if TABLE_REGION has real values (not placeholder 100, 100, 800, 600)
                    if (hasattr(config, 'TABLE_REGION') and 
                        config.TABLE_REGION != (0, 0, 0, 0) and
                        config.TABLE_REGION != (100, 100, 800, 600)):  # Not placeholder
                        # Already calibrated - show ready
                        self.mini_overlay.set_next_step("ready")
                        return
                except:
                    pass
            
            # Not calibrated - show calibration steps
            self.mini_overlay.set_next_step("calibrate")
                    
        except Exception as e:
            self.log(f"Error checking setup status: {e}", "ERROR")
            # Default to calibrate if error
            self.mini_overlay.set_next_step("calibrate")
        
    def init_advanced_features(self):
        """Initialize mini overlay, hotkeys, and system tray"""
        try:
            # Create mini overlay
            self.mini_overlay = MiniOverlay(self)
            self.mini_overlay.show()
            self.log("✅ Mini overlay created")
            
            # Register hotkeys
            self.hotkey_manager = HotkeyManager(self)
            self.hotkey_manager.register_hotkeys()
            
            # Create system tray icon
            self.system_tray = SystemTrayIcon(self)
            self.system_tray.run()
            self.log("✅ System tray icon created")
            
        except Exception as e:
            self.log(f"⚠️ Could not initialize advanced features: {e}", "WARNING")
            self.log("💡 Some features may require 'pip install keyboard pystray'", "INFO")
        
    def create_control_tab(self):
        """Main control panel"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🎮 Control Panel")
        
        # Settings
        settings = ttk.LabelFrame(tab, text="Bot Settings", padding=10)
        settings.pack(fill="x", padx=10, pady=5)
        
        # Execution
        ttk.Label(settings, text="Execution:").grid(row=0, column=0, sticky="w", padx=5)
        self.exec_var = tk.StringVar(value="analysis")
        ttk.Radiobutton(settings, text="Analysis Only", variable=self.exec_var, value="analysis").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(settings, text="Auto (Clicks)", variable=self.exec_var, value="auto").grid(row=0, column=2, sticky="w")
        
        # Max hands
        ttk.Label(settings, text="Max Hands:").grid(row=1, column=0, sticky="w", padx=5)
        self.hands_var = tk.StringVar(value="")
        ttk.Entry(settings, textvariable=self.hands_var, width=10).grid(row=1, column=1, sticky="w")
        
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
        
        inst_text = tk.Text(instructions, height=5, wrap="word", font=("Arial", 9), bg="#fffacd")
        inst_text.pack(fill="x")
        inst_text.insert("1.0",
            "1. Open PokerStars and sit at a table\n"
            "2. Click on poker window to make it active\n"
            "3. Press F8 to capture and detect elements\n"
            "4. Review preview below (red=buttons, green=pot)\n"
            "5. Click 'Save Configuration' if detection looks good\n"
            "6. Press F5 to test OCR accuracy"
        )
        inst_text.config(state="disabled")
        
        # Status
        status_frame = ttk.LabelFrame(tab, text="Calibration Status", padding=10)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        self.calib_status = ttk.Label(status_frame, text="Press F8 to capture active window", 
                                     foreground="gray", font=("Arial", 10))
        self.calib_status.pack(pady=5)
        
        # Step 3: Preview
        step3 = ttk.LabelFrame(tab, text="Preview (F8 will show screenshot here)", padding=10)
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
        
        # Description
        desc = ttk.LabelFrame(tab, text="About Debug Tab", padding=10)
        desc.pack(fill="x", padx=10, pady=5)
        
        desc_text = tk.Text(desc, height=3, wrap="word", font=("Arial", 9), bg="#e6f3ff")
        desc_text.pack(fill="x")
        desc_text.insert("1.0",
            "This tab is for testing OCR after calibration:\n"
            "• Press F5 to capture poker table and test OCR\n"
            "• Verify pot/stack amounts are read correctly\n"
            "• Use Kiro validation to check if game state makes sense"
        )
        desc_text.config(state="disabled")
        
        # Screenshot preview
        preview_frame = ttk.LabelFrame(tab, text="Table Screenshot (Press F5 to capture)", padding=10)
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.debug_canvas = tk.Canvas(preview_frame, bg="black", height=300)
        self.debug_canvas.pack(fill="both", expand=True)
        
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
            if amount and amount > 0:
                action += f" ${amount}"
            self.decision_label.config(text=action)
            
            reasoning = decision.get('reasoning', 'No reasoning')
            self.reasoning_text.delete("1.0", "end")
            self.reasoning_text.insert("1.0", reasoning)
        
        # Update debug tab
        self.state_text.delete("1.0", "end")
        self.state_text.insert("1.0", json.dumps(state, indent=2))
        
        # Update mini overlay
        if self.mini_overlay:
            try:
                self.mini_overlay.update_game_state(state=state, decision=decision)
            except Exception as e:
                self.log(f"ERROR: Overlay update failed: {e}", "ERROR")
                import traceback
                self.log(traceback.format_exc(), "ERROR")
        
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
            
        execution = self.exec_var.get()
        max_hands = self.hands_var.get()
        max_hands = int(max_hands) if max_hands else None
        
        self.log(f"Starting: exec={execution}, hands={max_hands}")
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.update_status("Running", 0)
        
        self.bot_thread = threading.Thread(target=self.run_bot, args=(execution, max_hands), daemon=True)
        self.bot_thread.start()
        
    def stop_bot(self):
        self.log("Stopping...")
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.update_status("Stopped")
        
    def run_bot(self, execution, max_hands):
        """Bot main loop - runs in separate thread"""
        try:
            from poker_bot import OnyxPokerBot
            bot = OnyxPokerBot(execution=execution)
            reader = bot.reader
            hands = 0
            
            self.log(f"🎰 Bot started: {execution} mode")
            
            while self.running and (max_hands is None or hands < max_hands):
                # Get game state with GPT-4o decision
                state = reader.parse_game_state(include_decision=True)
                
                # Check if our turn
                if not bot.is_hero_turn(state):
                    self.root.after(0, self.update_status, "Waiting for turn", hands)
                    import time
                    time.sleep(0.5)
                    continue
                
                # Log hand info
                cards = state.get('hero_cards', ['??', '??'])
                pot = state.get('pot', 0)
                action = state.get('recommended_action', 'fold')
                amount = state.get('recommended_amount', 0)
                reasoning = state.get('reasoning', 'No reasoning')
                
                self.log(f"\n🃏 Hand {hands+1}")
                self.log(f"Cards: {cards}, Pot: ${pot}")
                self.log(f"💡 Recommended: {action.upper()}" + (f" ${amount}" if amount else ""))
                self.log(f"📝 {reasoning[:80]}...")
                
                # Update GUI
                self.root.after(0, self.update_game_state, state, {
                    'action': action,
                    'amount': amount,
                    'reasoning': reasoning
                })
                self.root.after(0, self.update_status, "Playing", hands+1)
                
                # Execute or just advise
                if execution == 'auto':
                    bot.execute_action(state)
                    self.log(f"✅ Executed: {action}")
                else:
                    self.log(f"ℹ️  Advice only - no action taken")
                
                hands += 1
                import time
                time.sleep(2)  # Wait before next check
                
            self.log(f"✅ Finished: {hands} hands")
            self.root.after(0, self.update_status, "Finished", hands)
            
        except Exception as e:
            import traceback
            self.log(f"❌ Error: {e}", "ERROR")
            self.log(traceback.format_exc(), "ERROR")
            self.root.after(0, messagebox.showerror, "Error", str(e))
        finally:
            self.running = False
            self.root.after(0, self.start_btn.config, {"state": "normal"})
            self.root.after(0, self.stop_btn.config, {"state": "disabled"})
    
    def create_help_tab(self):
        """Help and documentation tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="❓ Help")
        
        # Setup Guide
        guide = ttk.LabelFrame(tab, text="📋 Setup Guide", padding=10)
        guide.pack(fill="x", padx=10, pady=5)
        
        guide_text = tk.Text(guide, height=8, wrap="word", font=("Arial", 9), bg="#f0f0f0")
        guide_text.pack(fill="x")
        guide_text.insert("1.0", 
            "🎯 First Time Setup:\n"
            "1. Press F7 to open Calibration tab\n"
            "2. Click 'Scan Windows' → Select your poker window\n"
            "3. Press F12 to hide this window (poker table visible)\n"
            "4. Press F8 to capture and auto-detect elements\n"
            "5. Review preview → Click 'Save Configuration'\n"
            "6. Press F8 to test OCR (optional)\n"
            "7. Press F9 anytime to get AI advice!\n\n"
            "💡 The mini overlay will guide you through each step"
        )
        guide_text.config(state="disabled")
        
        # Hotkeys Info
        hotkeys = ttk.LabelFrame(tab, text="⌨️ Global Hotkeys", padding=10)
        hotkeys.pack(fill="x", padx=10, pady=5)
        
        hotkeys_text = tk.Text(hotkeys, height=9, wrap="word", font=("Courier", 9), bg="#e8f4f8")
        hotkeys_text.pack(fill="x")
        hotkeys_text.insert("1.0",
            "F5       - Test OCR (capture screenshot, test OCR in Debug tab)\n"
            "F6       - Toggle Mini Overlay (show/hide mini panel)\n"
            "F7       - Open Calibration (open calibration tab)\n"
            "F8       - Capture & Detect (calibration - capture + CV detection)\n"
            "F9       - Capture & Analyze (take screenshot, get AI decision)\n"
            "F10      - Start/Stop Bot (toggle automation on/off)\n"
            "F11      - Emergency Stop (immediately stop bot, show main window)\n"
            "F12      - Toggle Main Window (show/hide this window)\n\n"
            "💡 All hotkeys work globally, even when PokerStars is focused!"
        )
        hotkeys_text.config(state="disabled")
        
        # Tips
        tips = ttk.LabelFrame(tab, text="💡 Tips & Tricks", padding=10)
        tips.pack(fill="x", padx=10, pady=5)
        
        tips_text = tk.Text(tips, height=6, wrap="word", font=("Arial", 9), bg="#fffacd")
        tips_text.pack(fill="x")
        tips_text.insert("1.0",
            "• Use F6 to hide overlay when playing manually\n"
            "• Press F12 before F8 during calibration (hides window for clean capture)\n"
            "• F9 works anytime - get advice on any hand\n"
            "• Check Activity Log (Control tab) if something goes wrong\n"
            "• Use 'Copy Logs' button to share logs for debugging\n"
            "• Mini overlay always shows what to do next"
        )
        tips_text.config(state="disabled")
    
    # Calibration actions
    def scan_windows(self):
        """Capture the window that was active before clicking this button"""
        self.window_list.delete(0, tk.END)
        self.calib_status.config(text="Waiting...", foreground="blue")
        self.log("🔍 Click on your poker window in 3 seconds...")
        self.root.update()
        
        # Give user 3 seconds to click on poker window
        import time
        for i in range(3, 0, -1):
            self.calib_status.config(text=f"Click poker window... {i}", foreground="orange")
            self.log(f"  {i}...")
            self.root.update()
            time.sleep(1)
        
        try:
            # Now get the active window (should be poker window)
            active_window = gw.getActiveWindow()
            
            if not active_window or not active_window.title:
                self.calib_status.config(text="❌ No active window", foreground="red")
                self.log("❌ No active window detected")
                self.log("💡 Make sure you clicked on poker window during countdown")
                messagebox.showwarning("No Active Window", "No window was focused during countdown.\nTry again and click on your poker window.")
                return
            
            # Store as single window
            self.windows = [{
                'title': active_window.title,
                'left': active_window.left,
                'top': active_window.top,
                'width': active_window.width,
                'height': active_window.height,
                'window': active_window
            }]
            
            display_text = f"{active_window.title} ({active_window.width}x{active_window.height})"
            self.window_list.insert(tk.END, display_text)
            self.log(f"✓ Captured: {display_text}")
            
            # Auto-select it
            self.window_list.selection_set(0)
            self.selected_window = self.windows[0]
            
            self.calib_status.config(text=f"✓ Ready: {active_window.title}", foreground="green")
            self.log("💡 Press F12 to hide this window, then F8 to capture")
            
            # Update overlay
            if hasattr(self, 'mini_overlay') and self.mini_overlay:
                self.mini_overlay.set_next_step("scan_done")
                
        except Exception as e:
            self.calib_status.config(text=f"❌ Error: {e}", foreground="red")
            self.log(f"❌ Error getting active window: {e}", "ERROR")
    
    def select_window(self):
        sel = self.window_list.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a window first")
            return
        
        self.selected_window = self.windows[sel[0]]
        window_title = self.selected_window['title']
        
        self.calib_status.config(text=f"✓ Selected: {window_title}", foreground="green")
        self.log(f"✓ Window selected: {window_title}")
        self.log("💡 Next steps:")
        self.log("   1. Press F12 to hide this window")
        self.log("   2. Press F8 to capture poker table")
        self.log("   3. Press F12 again to see results")
        
        # Update overlay
        if hasattr(self, 'mini_overlay') and self.mini_overlay:
            self.mini_overlay.set_next_step("scan_done")
    
    def auto_detect(self):
        """Capture active window and detect elements using GPT-4o"""
        # Immediate feedback
        self.calib_status.config(text="📸 Capturing active window...", foreground="blue")
        self.log("📸 Capturing currently active window...")
        if hasattr(self, 'mini_overlay') and self.mini_overlay:
            self.mini_overlay.update_status("📸 Capturing...")
        self.root.update()
        
        try:
            import pygetwindow as gw
            import pyautogui
            import tempfile
            from vision_detector import VisionDetector
            
            # Get active window
            active_window = gw.getActiveWindow()
            if not active_window or not active_window.title:
                self.log("❌ No active window detected", "ERROR")
                self.calib_status.config(text="❌ No active window", foreground="red")
                return
            
            self.log(f"✓ Active window: {active_window.title}")
            
            # Store window region
            window_region = (
                active_window.left,
                active_window.top,
                active_window.width,
                active_window.height
            )
            
            # Capture screenshot
            self.calib_status.config(text="🔎 Analyzing with GPT-4o...", foreground="blue")
            if hasattr(self, 'mini_overlay') and self.mini_overlay:
                self.mini_overlay.update_status("🔎 GPT-4o analyzing...")
            self.root.update()
            
            img = pyautogui.screenshot(region=window_region)
            
            # Save to temp file for GPT-4o
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                img.save(f.name)
                temp_path = f.name
            
            try:
                # Use GPT-4o to detect elements
                vision = VisionDetector()
                result = vision.detect_poker_elements(temp_path, include_decision=False)
                
                self.detected_elements = {
                    'window_region': window_region,
                    'button_regions': result.get('button_positions', {}),
                    'confidence': result.get('confidence', 0.95)
                }
                
                # Show preview
                self.show_preview(img, self.preview_canvas)
                
                conf = self.detected_elements.get('confidence', 0)
                self.confidence_label.config(text=f"Confidence: {conf:.1%}", 
                                            foreground="green" if conf > 0.7 else "orange")
                self.calib_status.config(text="✓ GPT-4o detection complete", foreground="green")
                self.log("✓ GPT-4o detected elements. Review and save if correct.")
                
                # Update overlay
                if hasattr(self, 'mini_overlay') and self.mini_overlay:
                    self.mini_overlay.update_status("✓ Detection complete")
                
            finally:
                import os
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
            # Show main window
            self.root.deiconify()
            self.root.lift()
            self.notebook.select(1)
        
        except Exception as e:
            self.calib_status.config(text=f"❌ Error: {e}", foreground="red")
            self.log(f"❌ Auto-detect error: {e}", "ERROR")
    
    def save_calibration(self):
        if not self.detected_elements:
            messagebox.showwarning("No Detection", "Press F8 to capture first")
            return
        
        if 'window_region' not in self.detected_elements:
            messagebox.showerror("Error", "No window region detected. Press F8 first.")
            return
        
        try:
            x, y, w, h = self.detected_elements['window_region']
            content = f'''"""Auto-generated configuration"""

TABLE_REGION = ({x}, {y}, {w}, {h})

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
            self.log("💡 Next: Press F8 to test OCR, or F9 to analyze a hand")
            self.log("   Calibration complete! Bot is ready to use.")
            
            # Update overlay
            self.mini_overlay.set_next_step("test")
        
        except Exception as e:
            messagebox.showerror("Save Failed", str(e))
    
    # Debug actions
    def capture_debug(self):
        try:
            reader = PokerScreenReader()
            
            # Capture only table region (what OCR sees)
            import pyautogui
            import config
            
            table_img = pyautogui.screenshot(region=config.TABLE_REGION)
            
            self.last_screenshot = table_img
            self.show_preview(table_img, self.debug_canvas)
            
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
            
        except Exception as e:
            self.log(f"❌ Capture error: {e}", "ERROR")
            messagebox.showerror("Error", str(e))
    
    def get_advice(self):
        """F9 - Get one-time advice from GPT-4o"""
        import time
        start_time = time.time()
        
        try:
            # Immediate feedback
            self.log("💡 Getting advice...")
            self.log("📸 Capturing screenshot...")
            if hasattr(self, 'mini_overlay') and self.mini_overlay:
                self.mini_overlay.update_status("🔍 Analyzing...")
            self.root.update()
            
            reader = PokerScreenReader()
            
            # Progress update
            self.log("🤖 Calling GPT-4o Vision API...")
            if hasattr(self, 'mini_overlay') and self.mini_overlay:
                self.mini_overlay.update_status("🤖 GPT-4o analyzing...")
            self.root.update()
            
            # Get state with decision from GPT-4o
            state = reader.parse_game_state(include_decision=True)
            
            elapsed = time.time() - start_time
            self.log(f"✓ Analysis complete in {elapsed:.1f}s")
            
            # Display in activity log
            cards = state.get('hero_cards', ['??', '??'])
            pot = state.get('pot', 0)
            board = state.get('community_cards', [])
            action = state.get('recommended_action', 'fold')
            amount = state.get('recommended_amount', 0)
            reasoning = state.get('reasoning', 'No reasoning')
            confidence = state.get('confidence', 0.0)
            
            self.log(f"\n🃏 Current Hand")
            self.log(f"Cards: {cards}, Board: {board}")
            self.log(f"Pot: ${pot}, Confidence: {confidence:.0%}")
            self.log(f"💡 Recommended: {action.upper()}" + (f" ${amount}" if amount else ""))
            self.log(f"📝 {reasoning}")
            
            # Debug: Log full state
            self.log(f"DEBUG: Full state: {json.dumps(state, indent=2)}")
            
            # Update game state display and overlay (unified)
            decision = {
                'action': action,
                'amount': amount,
                'reasoning': reasoning
            }
            
            self.update_game_state(state, decision)
            
            # Update state display
            self.state_text.delete("1.0", "end")
            self.state_text.insert("1.0", json.dumps(state, indent=2))
            
            self.log("📸 Debug capture complete - showing table region only")
        except Exception as e:
            self.log(f"❌ Capture error: {e}", "ERROR")
            if hasattr(self, 'mini_overlay') and self.mini_overlay:
                self.mini_overlay.update_status("❌ Error")
    
    def validate_with_kiro(self):
        """Validate current table state with Kiro CLI"""
        if not self.last_state:
            messagebox.showwarning("No State", "Please capture a screenshot first using '📸 Capture Now' button")
            return
        
        # Create progress window (centered)
        progress = tk.Toplevel(self.root)
        progress.title("Kiro Validation")
        
        # Center progress window
        progress_width = 500
        progress_height = 200
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - progress_width) // 2
        y = (screen_height - progress_height) // 2
        progress.geometry(f"{progress_width}x{progress_height}+{x}+{y}")
        
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
                # Use server for validation instead of local Kiro CLI
                client = OnyxPokerClient()
                
                # Send validation request to server
                import requests
                response = requests.post(
                    f"{client.server_url}/validate-state",
                    headers={"Authorization": f"Bearer {client.api_key}"},
                    json={"state": self.last_state},
                    timeout=180
                )
                
                if response.status_code == 200:
                    result = response.json()
                else:
                    raise Exception(f"Server error: {response.status_code}")
                
                progress.after(0, lambda: progress_bar.stop())
                progress.after(0, lambda: progress.destroy())
                
                # Log full interpretation to Activity Log
                interpretation = result.get('interpretation', 'No interpretation')
                self.log("=" * 50)
                self.log("🤖 KIRO VALIDATION RESULT")
                self.log("=" * 50)
                
                if result.get('understood', False):
                    conf = result.get('confidence', 0)
                    self.kiro_status.config(text=f"✓ Valid (conf: {conf:.2f})", foreground="green")
                    self.log(f"✅ Status: VALID (confidence: {conf:.2f})")
                else:
                    self.kiro_status.config(text="✗ Invalid", foreground="red")
                    concerns = result.get('concerns', ['Unknown issue'])
                    self.log(f"⚠️ Status: INVALID")
                    self.log(f"⚠️ Concerns: {', '.join(concerns)}")
                
                # Log full interpretation (line by line for readability)
                self.log("📝 Kiro's Analysis:")
                for line in interpretation.split('\n'):
                    if line.strip():
                        self.log(f"   {line.strip()}")
                
                self.log("=" * 50)
                
                # Show detailed response in popup with selectable text
                popup = tk.Toplevel(self.root)
                popup.title("Kiro Validation Result")
                
                # Center and size popup (80% of screen)
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                popup_width = int(screen_width * 0.6)
                popup_height = int(screen_height * 0.7)
                x = (screen_width - popup_width) // 2
                y = (screen_height - popup_height) // 2
                popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")
                
                popup.transient(self.root)
                
                # Header
                header_frame = ttk.Frame(popup)
                header_frame.pack(fill="x", padx=10, pady=10)
                
                status_text = "✅ VALID" if result.get('understood', False) else "⚠️ INVALID"
                status_color = "green" if result.get('understood', False) else "red"
                ttk.Label(header_frame, text=status_text, font=("Arial", 14, "bold"), 
                         foreground=status_color).pack()
                ttk.Label(header_frame, text=f"Confidence: {result.get('confidence', 0):.2f}",
                         font=("Arial", 10)).pack()
                
                if result.get('concerns'):
                    ttk.Label(header_frame, text=f"Concerns: {', '.join(result.get('concerns', []))}",
                             font=("Arial", 9), foreground="orange").pack()
                
                # Scrollable text area
                text_frame = ttk.Frame(popup)
                text_frame.pack(fill="both", expand=True, padx=10, pady=5)
                
                text_widget = scrolledtext.ScrolledText(text_frame, wrap="word", font=("Courier", 9))
                text_widget.pack(fill="both", expand=True)
                text_widget.insert("1.0", interpretation)
                text_widget.config(state="normal")  # Keep editable for copy-paste
                
                # Buttons
                btn_frame = ttk.Frame(popup)
                btn_frame.pack(fill="x", padx=10, pady=10)
                
                def copy_result():
                    popup.clipboard_clear()
                    popup.clipboard_append(interpretation)
                    popup.update()
                    messagebox.showinfo("Copied", "Validation result copied to clipboard!", parent=popup)
                
                ttk.Button(btn_frame, text="📋 Copy to Clipboard", command=copy_result).pack(side="left", padx=5)
                ttk.Button(btn_frame, text="Close", command=popup.destroy).pack(side="right", padx=5)
            except Exception as e:
                progress.after(0, lambda: progress_bar.stop())
                progress.after(0, lambda: progress.destroy())
                self.kiro_status.config(text="✗ Error", foreground="red")
                self.log(f"❌ Validation error: {e}", "ERROR")
                messagebox.showerror("Error", f"Validation failed:\n{str(e)}\n\nMake sure server is running and accessible.")
        
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
    
    def load_window_geometry(self):
        """Load saved window geometry or maximize"""
        try:
            with open(self.geometry_file, 'r') as f:
                self.saved_geometry = f.read().strip()
                if self.saved_geometry:
                    self.root.geometry(self.saved_geometry)
                    return
        except:
            pass
        
        # Default: maximize
        self.root.state('zoomed')
    
    def save_window_geometry(self):
        """Save current window geometry"""
        try:
            # Only save if not maximized/minimized
            if self.root.state() == 'normal':
                geometry = self.root.geometry()
                with open(self.geometry_file, 'w') as f:
                    f.write(geometry)
                self.saved_geometry = geometry
        except:
            pass
    
    def on_window_configure(self, event):
        """Handle window resize/move"""
        if event.widget == self.root:
            # Save geometry after user stops resizing (debounce)
            if hasattr(self, '_geometry_timer'):
                self.root.after_cancel(self._geometry_timer)
            self._geometry_timer = self.root.after(500, self.save_window_geometry)

def main():
    logging.basicConfig(level=logging.INFO)
    root = tk.Tk()
    app = OnyxPokerGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
