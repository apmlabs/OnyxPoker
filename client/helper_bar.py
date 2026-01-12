"""
OnyxPoker Helper Bar - Wide, short UI docked to bottom of screen
Replaces poker_gui.py and mini_overlay.py
"""

import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
from datetime import datetime
from PIL import Image, ImageTk
import pyautogui
import pygetwindow as gw
import keyboard
import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Parse command line arguments
import argparse
parser = argparse.ArgumentParser(description='OnyxPoker Helper Bar')
parser.add_argument('--ai-only', action='store_true', help='Use AI for both vision and decisions (old mode)')
parser.add_argument('--strategy', type=str, default='gpt3', help='Strategy to use (default: gpt3)')
args = parser.parse_args()

# Default: gpt-5.2 vision + strategy_engine (hardcoded strategy)
# --ai-only: gpt-5.2 does both vision + decision (old behavior)
AI_ONLY_MODE = args.ai_only
STRATEGY = args.strategy

if AI_ONLY_MODE:
    from vision_detector import VisionDetector, MODEL
else:
    from vision_detector_lite import VisionDetectorLite, DEFAULT_MODEL
    from strategy_engine import StrategyEngine

# Session log file
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
SESSION_LOG = os.path.join(LOG_DIR, f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")


class HelperBar:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OnyxPoker")

        # Screen dimensions
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Helper bar: full width, 880px height (4x original), docked to bottom
        bar_height = 880
        self.root.geometry(f"{screen_w}x{bar_height}+0+{screen_h - bar_height - 40}")

        # Keep window decorations for resizing
        self.root.overrideredirect(False)
        
        # Always on top
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)

        # State
        self.log_queue = queue.Queue()
        self._analyzing = False
        self.last_screenshot = None
        self.bot_running = False
        
        # Drag state
        self._drag_start_x = 0
        self._drag_start_y = 0

        self.create_ui()
        self.register_hotkeys()
        self.update_log_display()

        self.log("OnyxPoker ready - Press F9 for advice", "INFO")

    def create_ui(self):
        """Three-column layout: Status | Log | Result"""
        main = tk.Frame(self.root, bg='#1e1e1e')
        main.pack(fill='both', expand=True)

        # === TOP: Title bar (draggable) ===
        top_bar = tk.Frame(main, bg='#2d2d2d', height=30)
        top_bar.pack(side='top', fill='x')
        top_bar.pack_propagate(False)
        
        # Make draggable
        top_bar.bind('<Button-1>', self._start_drag)
        top_bar.bind('<B1-Motion>', self._on_drag)
        
        tk.Label(top_bar, text="OnyxPoker - All Position Advisor", font=('Arial', 10, 'bold'),
                bg='#2d2d2d', fg='#00ffff').pack(side='left', padx=10)
        
        # Close button on right
        tk.Button(top_bar, text="✕", font=('Arial', 10, 'bold'),
                 bg='#2d2d2d', fg='#ff4444', relief='flat', padx=5,
                 command=self.root.quit).pack(side='right', padx=2)

        # === BOTTOM: Three columns ===
        bottom = tk.Frame(main, bg='#1e1e1e')
        bottom.pack(side='top', fill='both', expand=True)

        # === LEFT: Status & Hotkeys (150px) ===
        left = tk.Frame(bottom, bg='#2d2d2d', width=150)
        left.pack(side='left', fill='y', padx=2, pady=2)
        left.pack_propagate(False)

        tk.Label(left, text="OnyxPoker", font=('Arial', 12, 'bold'),
                bg='#2d2d2d', fg='#00ffff').pack(pady=5)

        self.status_label = tk.Label(left, text="Ready", font=('Arial', 10, 'bold'),
                                    bg='#2d2d2d', fg='#00ff00')
        self.status_label.pack(pady=2)

        tk.Frame(left, height=1, bg='#555').pack(fill='x', pady=5)

        # Hotkey hints
        hints = [("F9", "Advice"), ("F10", "Bot"), ("F11", "Stop"), ("F12", "Hide")]
        for key, action in hints:
            f = tk.Frame(left, bg='#2d2d2d')
            f.pack(fill='x', padx=5)
            tk.Label(f, text=key, font=('Courier', 9, 'bold'), bg='#2d2d2d', fg='#ffff00', width=4).pack(side='left')
            tk.Label(f, text=action, font=('Arial', 9), bg='#2d2d2d', fg='#aaa').pack(side='left')

        tk.Frame(left, height=1, bg='#555').pack(fill='x', pady=5)

        if AI_ONLY_MODE:
            tk.Label(left, text=f"AI ONLY: {MODEL}", font=('Arial', 8),
                    bg='#2d2d2d', fg='#ff8800').pack(pady=1)
        else:
            tk.Label(left, text=f"Vision: {DEFAULT_MODEL}", font=('Arial', 8),
                    bg='#2d2d2d', fg='#888').pack(pady=1)
            tk.Label(left, text=f"Strategy: {STRATEGY}", font=('Arial', 8),
                    bg='#2d2d2d', fg='#00ff00').pack(pady=1)

        # === CENTER: Live Log (expandable) ===
        center = tk.Frame(bottom, bg='#1a1a1a')
        center.pack(side='left', fill='both', expand=True, padx=2, pady=2)

        # Log buttons
        btn_frame = tk.Frame(center, bg='#1a1a1a')
        btn_frame.pack(fill='x')

        tk.Button(btn_frame, text="Clear", font=('Arial', 8),
                 bg='#333', fg='#fff', relief='flat', padx=8, pady=2,
                 command=self.clear_log).pack(side='right', padx=1)

        tk.Button(btn_frame, text="Copy", font=('Arial', 8),
                 bg='#333', fg='#fff', relief='flat', padx=8, pady=2,
                 command=self.copy_log).pack(side='right', padx=1)

        # Log text
        self.log_text = scrolledtext.ScrolledText(center, font=('Courier', 10),
                                                  bg='#0d0d0d', fg='#ccc',
                                                  wrap='word', height=10)
        self.log_text.pack(fill='both', expand=True, pady=2)

        # Color tags
        self.log_text.tag_configure('INFO', foreground='#00ff00', font=('Courier', 10))
        self.log_text.tag_configure('DEBUG', foreground='#00ffff', font=('Courier', 10))
        self.log_text.tag_configure('ERROR', foreground='#ff4444', font=('Courier', 10, 'bold'))
        self.log_text.tag_configure('DECISION', foreground='#ffff00', font=('Courier', 11, 'bold'))

        # === RIGHT: Last Result (400px) ===
        right = tk.Frame(bottom, bg='#2d2d2d', width=400)
        right.pack(side='right', fill='y', padx=2, pady=2)
        right.pack_propagate(False)

        tk.Label(right, text="LAST RESULT", font=('Arial', 9, 'bold'),
                bg='#2d2d2d', fg='#888').pack(pady=3)

        # Game state
        state_frame = tk.Frame(right, bg='#2d2d2d')
        state_frame.pack(fill='x', padx=5)

        self.cards_label = tk.Label(state_frame, text="Cards: --", font=('Courier', 12, 'bold'),
                                   bg='#2d2d2d', fg='#00ffff', anchor='w')
        self.cards_label.pack(fill='x')

        self.board_label = tk.Label(state_frame, text="Board: --", font=('Courier', 10),
                                   bg='#2d2d2d', fg='#fff', anchor='w')
        self.board_label.pack(fill='x')

        self.pot_label = tk.Label(state_frame, text="Pot: --", font=('Courier', 10),
                                 bg='#2d2d2d', fg='#ffff00', anchor='w')
        self.pot_label.pack(fill='x')

        tk.Frame(right, height=1, bg='#555').pack(fill='x', pady=5)

        # Decision - big and clear
        self.decision_label = tk.Label(right, text="--", font=('Arial', 18, 'bold'),
                                      bg='#2d2d2d', fg='#00ff00')
        self.decision_label.pack(pady=5)

        # To call info
        self.maxcall_label = tk.Label(right, text="", font=('Arial', 12),
                                     bg='#2d2d2d', fg='#ffff00')
        self.maxcall_label.pack(pady=2)

        # Time
        self.time_label = tk.Label(right, text="", font=('Arial', 9),
                                  bg='#2d2d2d', fg='#888')
        self.time_label.pack(pady=2)

    def log(self, message, level="INFO"):
        """Add message to log queue"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put((timestamp, level, message))

    def update_log_display(self):
        """Process log queue"""
        try:
            while True:
                timestamp, level, message = self.log_queue.get_nowait()
                line = f"[{timestamp}] {message}\n"
                tag = 'DECISION' if '=>' in message else level
                self.log_text.insert('end', line, tag)
                self.log_text.see('end')
        except queue.Empty:
            pass
        self.root.after(50, self.update_log_display)

    def clear_log(self):
        self.log_text.delete('1.0', 'end')

    def copy_log(self):
        text = self.log_text.get('1.0', 'end-1c')
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log("Logs copied", "INFO")

    def register_hotkeys(self):
        """Register global hotkeys"""
        keyboard.add_hotkey('f9', self.on_f9, suppress=True)
        keyboard.add_hotkey('f10', self.on_f10, suppress=True)
        keyboard.add_hotkey('f11', self.on_f11, suppress=True)
        keyboard.add_hotkey('f12', self.on_f12, suppress=True)
        self.log("Hotkeys: F9=Advice F10=Bot F11=Stop F12=Hide", "DEBUG")

    def on_f9(self):
        """Get AI advice - screenshots active window, no calibration needed"""
        if self._analyzing:
            self.log("Already analyzing...", "DEBUG")
            return

        self._analyzing = True
        self.status_label.config(text="Analyzing...", fg='#ffff00')
        self.log("F9: Analyzing...", "INFO")

        thread = threading.Thread(target=self._analyze_thread, daemon=True)
        thread.start()

    def _analyze_thread(self, test_image_path=None):
        """Background analysis. If test_image_path provided, use that instead of screenshot."""
        import time
        from datetime import datetime
        start = time.time()
        screenshot_name = None

        try:
            if test_image_path:
                # Test mode - use existing image
                from PIL import Image
                img = Image.open(test_image_path)
                temp_path = test_image_path
                screenshot_name = os.path.basename(test_image_path)
                self.root.after(0, lambda: self.log(f"Test: {screenshot_name}", "DEBUG"))
                delete_temp = False
            else:
                # Live mode - screenshot active window
                active = gw.getActiveWindow()
                if not active:
                    self.root.after(0, lambda: self.log("No active window", "ERROR"))
                    return

                region = (active.left, active.top, active.width, active.height)
                self.root.after(0, lambda: self.log(f"Window: {active.title[:40]}...", "DEBUG"))

                img = pyautogui.screenshot(region=region)
                self.last_screenshot = img

                # Save to screenshots folder for future testing
                screenshots_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
                os.makedirs(screenshots_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_name = f'{timestamp}.png'
                saved_path = os.path.join(screenshots_dir, screenshot_name)
                img.save(saved_path)
                self.root.after(0, lambda p=saved_path: self.log(f"Saved: {os.path.basename(p)}", "DEBUG"))

                # Also save temp for API
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                    img.save(f.name)
                    temp_path = f.name
                delete_temp = True

            try:
                # AI analysis
                if AI_ONLY_MODE:
                    # AI-only mode: gpt-5.2 does both vision + decision
                    self.root.after(0, lambda: self.log(f"API call ({MODEL})...", "DEBUG"))
                    api_start = time.time()
                    vision = VisionDetector(logger=lambda m, l="DEBUG": self.root.after(0, lambda: self.log(m, l)))
                    result = vision.detect_poker_elements(temp_path, include_decision=True)
                    api_time = time.time() - api_start
                    
                    # For AI-only mode, just use the single result
                    all_position_results = None
                else:
                    # Default mode: gpt-5.2 for vision, strategy_engine for decision
                    self.root.after(0, lambda: self.log(f"API call ({DEFAULT_MODEL})...", "DEBUG"))
                    api_start = time.time()
                    vision = VisionDetectorLite(logger=lambda m, l="DEBUG": self.root.after(0, lambda: self.log(m, l)))
                    table_data = vision.detect_table(temp_path)
                    api_time = time.time() - api_start
                    
                    # Calculate action for ALL 6 positions
                    engine = StrategyEngine(STRATEGY)
                    all_position_results = {}
                    
                    for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
                        pos_data = {**table_data, 'position': pos}
                        decision = engine.get_action(pos_data)
                        all_position_results[pos] = decision
                    
                    # Use BTN as default for display
                    result = {**table_data, **all_position_results['BTN']}
                    result['api_time'] = api_time
                    result['all_positions'] = all_position_results

                elapsed = time.time() - start
                self.root.after(0, lambda t=api_time: self.log(f"API done: {t:.1f}s", "DEBUG"))
                self.root.after(0, lambda: self._display_result(result, elapsed, img, screenshot_name))

            finally:
                if delete_temp:
                    os.unlink(temp_path)

        except Exception as e:
            import traceback
            self.root.after(0, lambda: self.log(f"Error: {e}", "ERROR"))
            self.root.after(0, lambda: self.log(traceback.format_exc(), "DEBUG"))
        finally:
            self._analyzing = False
            self.root.after(0, lambda: self.status_label.config(text="Ready", fg='#00ff00'))

    def _display_result(self, result, elapsed, screenshot, screenshot_name=None):
        """Display analysis result"""
        if not result:
            self.log("No result from AI", "ERROR")
            return

        # Extract data
        cards = result.get('hero_cards') or []
        # Filter out null values from cards
        cards = [c for c in cards if c] if cards else []
        board = result.get('community_cards', [])
        pot = result.get('pot', 0) or 0
        action = result.get('action') or 'unknown'
        bet_size = result.get('bet_size') or 0
        reasoning = result.get('reasoning') or ''
        confidence = result.get('confidence', 0.95) or 0.95

        to_call = result.get('to_call')
        
        # Save to session log (JSONL format) - includes screenshot name for correlation
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'screenshot': screenshot_name,
            'hero_cards': cards,
            'board': board,
            'pot': pot,
            'is_hero_turn': result.get('is_hero_turn', True),
            'action': action,
            'amount': bet_size,
            'to_call': to_call,
            'reasoning': reasoning,
            'confidence': confidence,
            'elapsed': round(elapsed, 2)
        }
        with open(SESSION_LOG, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

        # Log result
        cards_str = ' '.join(cards) if cards else '--'
        board_str = ' '.join(board) if board else '--'
        self.log(f"Cards: {cards_str} | Board: {board_str} | Pot: ${pot}", "INFO")

        # Show decision if we have any useful info (pot > 0 means table detected)
        if pot > 0 or cards or board:
            # If we have all position results (preflop), show them
            all_positions = result.get('all_positions')
            if all_positions and not board:  # Preflop only
                # Build one-line summary
                pos_actions = []
                for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
                    pos_result = all_positions[pos]
                    action = pos_result.get('action', 'fold')
                    bet_size = pos_result.get('bet_size', 0)
                    
                    if action in ('bet', 'raise') and bet_size:
                        action_str = f"{action.upper()} €{bet_size:.2f}"
                    else:
                        action_str = action.upper()
                    
                    pos_actions.append(f"{pos}:{action_str}")
                
                self.log(" | ".join(pos_actions), "DECISION")
            else:
                # Postflop or AI-only mode - show single decision
                decision_str = f"=> {action.upper()}"
                if bet_size and action in ('bet', 'raise'):
                    decision_str += f" €{bet_size:.2f}"
                self.log(decision_str, "DECISION")
            
            if reasoning:
                self.log(reasoning, "DEBUG")
        else:
            decision_str = "No poker table detected"
            self.log(decision_str, "ERROR")

        # Update right panel
        is_hero_turn = result.get('is_hero_turn', True)
        
        if is_hero_turn:
            self.cards_label.config(text=cards_str)
            self.decision_label.config(text=action.upper())
            self.maxcall_label.config(text="")
        else:
            # Not hero's turn - show to_call and pre-action status
            self.cards_label.config(text="[PRE-ACTION]")
            self.decision_label.config(text=f"=> {action.upper()}")
            to_call_str = f"To call: €{to_call}" if to_call else "To call: €0 (check)"
            self.maxcall_label.config(text=to_call_str)
            self.log(f"Pre-action | {to_call_str}", "INFO")
        
        self.board_label.config(text=f"Board: {board_str}")
        self.pot_label.config(text=f"Pot: €{pot}")
        
        self.time_label.config(text=f"{elapsed:.1f}s")

    def on_f10(self):
        """Toggle bot mode"""
        if self.bot_running:
            self.bot_running = False
            self.status_label.config(text="Stopped", fg='#ff8800')
            self.log("Bot stopped", "INFO")
        else:
            self.bot_running = True
            self.status_label.config(text="Bot Running", fg='#00ffff')
            self.log("Bot started (F11 to stop)", "INFO")
            thread = threading.Thread(target=self._bot_loop, daemon=True)
            thread.start()

    def _bot_loop(self):
        """Continuous bot loop"""
        import time
        while self.bot_running:
            self.on_f9()
            # Wait for analysis to complete
            while self._analyzing:
                time.sleep(0.1)
            time.sleep(2)  # Wait between hands

    def on_f11(self):
        """Emergency stop"""
        self.bot_running = False
        self._analyzing = False
        self.status_label.config(text="STOPPED", fg='#ff4444')
        self.log("F11: Emergency stop!", "ERROR")

    def on_f12(self):
        """Toggle visibility"""
        if self.root.state() == 'withdrawn':
            self.root.deiconify()
            self.log("Window shown", "DEBUG")
        else:
            self.root.withdraw()

    def _start_drag(self, event):
        """Start dragging window"""
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event):
        """Drag window"""
        x = self.root.winfo_x() + event.x - self._drag_start_x
        y = self.root.winfo_y() + event.y - self._drag_start_y
        self.root.geometry(f"+{x}+{y}")

    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    app = HelperBar()
    app.run()


if __name__ == '__main__':
    main()
