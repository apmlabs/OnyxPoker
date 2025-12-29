"""
OnyxPoker GUI - Control panel and monitoring interface
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import json
from datetime import datetime
from poker_bot import OnyxPokerBot
from poker_reader import PokerScreenReader
from automation_client import OnyxPokerClient
import config

class OnyxPokerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OnyxPoker Bot Control Panel")
        self.root.geometry("900x700")
        self.root.resizable(False, False)
        
        # Bot state
        self.bot = None
        self.bot_thread = None
        self.running = False
        self.log_queue = queue.Queue()
        
        # Create UI
        self.create_widgets()
        self.update_log()
        
    def create_widgets(self):
        # Top: Settings Panel
        settings_frame = ttk.LabelFrame(self.root, text="Settings", padding=10)
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        # Mode selection
        ttk.Label(settings_frame, text="Mode:").grid(row=0, column=0, sticky="w", padx=5)
        self.mode_var = tk.StringVar(value="remote")
        ttk.Radiobutton(settings_frame, text="Remote (Server)", variable=self.mode_var, value="remote").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(settings_frame, text="Local (Kiro CLI)", variable=self.mode_var, value="local").grid(row=0, column=2, sticky="w")
        
        # Execution mode
        ttk.Label(settings_frame, text="Execution:").grid(row=1, column=0, sticky="w", padx=5)
        self.exec_var = tk.StringVar(value="analysis")
        ttk.Radiobutton(settings_frame, text="Analysis Only", variable=self.exec_var, value="analysis").grid(row=1, column=1, sticky="w")
        ttk.Radiobutton(settings_frame, text="Auto (Clicks)", variable=self.exec_var, value="auto").grid(row=1, column=2, sticky="w")
        
        # Max hands
        ttk.Label(settings_frame, text="Max Hands:").grid(row=2, column=0, sticky="w", padx=5)
        self.hands_var = tk.StringVar(value="")
        ttk.Entry(settings_frame, textvariable=self.hands_var, width=10).grid(row=2, column=1, sticky="w")
        ttk.Label(settings_frame, text="(empty = unlimited)").grid(row=2, column=2, sticky="w")
        
        # Control buttons
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        self.start_btn = ttk.Button(control_frame, text="▶ Start Bot", command=self.start_bot, width=15)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="⏹ Stop Bot", command=self.stop_bot, width=15, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        ttk.Button(control_frame, text="🔧 Test Connection", command=self.test_connection, width=15).pack(side="left", padx=5)
        ttk.Button(control_frame, text="📸 Test OCR", command=self.test_ocr, width=15).pack(side="left", padx=5)
        
        # Status Panel
        status_frame = ttk.LabelFrame(self.root, text="Current Status", padding=10)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        # Status labels
        self.status_label = ttk.Label(status_frame, text="Status: Idle", font=("Arial", 10, "bold"))
        self.status_label.pack(anchor="w")
        
        self.hands_label = ttk.Label(status_frame, text="Hands Played: 0")
        self.hands_label.pack(anchor="w")
        
        # Game State Panel
        state_frame = ttk.LabelFrame(self.root, text="Last Game State", padding=10)
        state_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create two columns
        left_col = ttk.Frame(state_frame)
        left_col.pack(side="left", fill="both", expand=True)
        
        right_col = ttk.Frame(state_frame)
        right_col.pack(side="left", fill="both", expand=True)
        
        # Left column - Game info
        ttk.Label(left_col, text="Cards:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.cards_label = ttk.Label(left_col, text="--", font=("Courier", 12))
        self.cards_label.pack(anchor="w", pady=2)
        
        ttk.Label(left_col, text="Board:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.board_label = ttk.Label(left_col, text="--", font=("Courier", 12))
        self.board_label.pack(anchor="w", pady=2)
        
        ttk.Label(left_col, text="Pot:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.pot_label = ttk.Label(left_col, text="$0", font=("Courier", 12))
        self.pot_label.pack(anchor="w", pady=2)
        
        ttk.Label(left_col, text="Stack:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.stack_label = ttk.Label(left_col, text="$0", font=("Courier", 12))
        self.stack_label.pack(anchor="w", pady=2)
        
        # Right column - Decision
        ttk.Label(right_col, text="Decision:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.decision_label = ttk.Label(right_col, text="--", font=("Courier", 14, "bold"), foreground="blue")
        self.decision_label.pack(anchor="w", pady=2)
        
        ttk.Label(right_col, text="Reasoning:", font=("Arial", 9, "bold")).pack(anchor="w")
        self.reasoning_text = tk.Text(right_col, height=6, width=40, wrap="word", font=("Arial", 9))
        self.reasoning_text.pack(anchor="w", pady=2)
        
        # Log Panel
        log_frame = ttk.LabelFrame(self.root, text="Activity Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap="word", font=("Courier", 9))
        self.log_text.pack(fill="both", expand=True)
        
        # Clear log button
        ttk.Button(log_frame, text="Clear Log", command=self.clear_log).pack(anchor="e", pady=5)
        
    def log(self, message, level="INFO"):
        """Add message to log queue"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {level}: {message}")
        
    def update_log(self):
        """Update log display from queue"""
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
        
    def update_status(self, status, hands=None):
        """Update status display"""
        self.status_label.config(text=f"Status: {status}")
        if hands is not None:
            self.hands_label.config(text=f"Hands Played: {hands}")
            
    def update_game_state(self, state, decision=None):
        """Update game state display"""
        # Cards
        cards = ', '.join(state.get('hero_cards', ['??', '??']))
        self.cards_label.config(text=cards)
        
        # Board
        board = ', '.join(state.get('community_cards', [])) or "None"
        self.board_label.config(text=board)
        
        # Pot
        pot = state.get('pot', 0)
        self.pot_label.config(text=f"${pot}")
        
        # Stack
        stacks = state.get('stacks', [])
        stack = stacks[2] if len(stacks) > 2 else 0
        self.stack_label.config(text=f"${stack}")
        
        # Decision
        if decision:
            action = decision.get('action', '--').upper()
            amount = decision.get('amount', 0)
            if amount > 0:
                action += f" ${amount}"
            self.decision_label.config(text=action)
            
            # Reasoning
            reasoning = decision.get('reasoning', 'No reasoning provided')
            self.reasoning_text.delete("1.0", "end")
            self.reasoning_text.insert("1.0", reasoning)
            
    def test_connection(self):
        """Test server connection"""
        self.log("Testing server connection...")
        try:
            client = OnyxPokerClient()
            if client.test_connection():
                self.log("✅ Server connection successful!", "SUCCESS")
                messagebox.showinfo("Success", "Connected to server!")
            else:
                self.log("❌ Server connection failed", "ERROR")
                messagebox.showerror("Error", "Cannot connect to server")
        except Exception as e:
            self.log(f"❌ Connection error: {str(e)}", "ERROR")
            messagebox.showerror("Error", str(e))
            
    def test_ocr(self):
        """Test OCR reading"""
        self.log("Testing OCR...")
        try:
            reader = PokerScreenReader()
            state = reader.parse_game_state()
            self.log(f"OCR Result: {json.dumps(state, indent=2)}", "INFO")
            self.update_game_state(state)
            messagebox.showinfo("OCR Test", f"Pot: ${state['pot']}\nStacks: {state['stacks']}")
        except Exception as e:
            self.log(f"❌ OCR error: {str(e)}", "ERROR")
            messagebox.showerror("Error", str(e))
            
    def start_bot(self):
        """Start the bot in a separate thread"""
        if self.running:
            return
            
        mode = self.mode_var.get()
        execution = self.exec_var.get()
        max_hands = self.hands_var.get()
        max_hands = int(max_hands) if max_hands else None
        
        self.log(f"Starting bot: mode={mode}, execution={execution}, max_hands={max_hands}")
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.update_status("Running", 0)
        
        # Start bot in thread
        self.bot_thread = threading.Thread(target=self.run_bot, args=(mode, execution, max_hands), daemon=True)
        self.bot_thread.start()
        
    def stop_bot(self):
        """Stop the bot"""
        self.log("Stopping bot...")
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.update_status("Stopped")
        
    def run_bot(self, mode, execution, max_hands):
        """Bot main loop (runs in thread)"""
        try:
            bot = OnyxPokerBot(mode=mode, execution=execution)
            reader = bot.reader
            hands_played = 0
            
            self.log("Bot started, waiting for your turn...")
            
            while self.running and (max_hands is None or hands_played < max_hands):
                # Check turn
                if not reader.is_hero_turn():
                    self.root.after(0, self.update_status, "Waiting for turn", hands_played)
                    import time
                    time.sleep(config.POLL_INTERVAL)
                    continue
                
                # Parse state
                state = reader.parse_game_state()
                self.log(f"Hand {hands_played + 1}: Pot=${state['pot']}, Actions={list(state['actions'].keys())}")
                
                # Get decision
                decision = bot.get_decision(state)
                self.log(f"Decision: {decision['action'].upper()} - {decision.get('reasoning', '')[:50]}...")
                
                # Update UI
                self.root.after(0, self.update_game_state, state, decision)
                self.root.after(0, self.update_status, "Playing", hands_played + 1)
                
                # Execute
                if execution == 'auto':
                    bot.execute_action(decision)
                    self.log(f"✅ Executed: {decision['action']}")
                else:
                    self.log(f"ℹ️  Analysis only: {decision['action']}")
                
                hands_played += 1
                import time
                time.sleep(config.ACTION_DELAY)
                
            self.log(f"Bot finished. Hands played: {hands_played}")
            self.root.after(0, self.update_status, "Finished", hands_played)
            
        except Exception as e:
            self.log(f"❌ Bot error: {str(e)}", "ERROR")
            self.root.after(0, messagebox.showerror, "Bot Error", str(e))
        finally:
            self.running = False
            self.root.after(0, self.start_btn.config, {"state": "normal"})
            self.root.after(0, self.stop_btn.config, {"state": "disabled"})

def main():
    root = tk.Tk()
    app = OnyxPokerGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
