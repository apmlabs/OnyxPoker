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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vision_detector import VisionDetector, MODEL


class HelperBar:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OnyxPoker")

        # Screen dimensions
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Helper bar: full width, 220px height, docked to bottom
        bar_height = 220
        self.root.geometry(f"{screen_w}x{bar_height}+0+{screen_h - bar_height - 40}")

        # Always on top
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)

        # State
        self.log_queue = queue.Queue()
        self._analyzing = False
        self.last_screenshot = None
        self.bot_running = False

        self.create_ui()
        self.register_hotkeys()
        self.update_log_display()

        self.log("OnyxPoker ready - Press F9 for advice", "INFO")

    def create_ui(self):
        """Three-column layout: Status | Log | Result"""
        main = tk.Frame(self.root, bg='#1e1e1e')
        main.pack(fill='both', expand=True)

        # === LEFT: Status & Hotkeys (150px) ===
        left = tk.Frame(main, bg='#2d2d2d', width=150)
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

        tk.Label(left, text=f"Model: {MODEL}", font=('Arial', 8),
                bg='#2d2d2d', fg='#888').pack(pady=2)

        # === CENTER: Live Log (expandable) ===
        center = tk.Frame(main, bg='#1a1a1a')
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
        self.log_text = scrolledtext.ScrolledText(center, font=('Courier', 9),
                                                  bg='#0d0d0d', fg='#ccc',
                                                  wrap='word', height=10)
        self.log_text.pack(fill='both', expand=True, pady=2)

        # Color tags
        self.log_text.tag_configure('INFO', foreground='#00ff00')
        self.log_text.tag_configure('DEBUG', foreground='#888888')
        self.log_text.tag_configure('ERROR', foreground='#ff4444')
        self.log_text.tag_configure('DECISION', foreground='#00ffff', font=('Courier', 10, 'bold'))

        # === RIGHT: Last Result (300px) ===
        right = tk.Frame(main, bg='#2d2d2d', width=300)
        right.pack(side='right', fill='y', padx=2, pady=2)
        right.pack_propagate(False)

        tk.Label(right, text="LAST RESULT", font=('Arial', 9, 'bold'),
                bg='#2d2d2d', fg='#888').pack(pady=3)

        # Screenshot thumbnail
        self.thumb_canvas = tk.Canvas(right, width=280, height=80, bg='#111', highlightthickness=0)
        self.thumb_canvas.pack(pady=2)

        # Game state
        state_frame = tk.Frame(right, bg='#2d2d2d')
        state_frame.pack(fill='x', padx=5)

        self.cards_label = tk.Label(state_frame, text="Cards: --", font=('Courier', 10, 'bold'),
                                   bg='#2d2d2d', fg='#00ffff', anchor='w')
        self.cards_label.pack(fill='x')

        self.board_label = tk.Label(state_frame, text="Board: --", font=('Courier', 9),
                                   bg='#2d2d2d', fg='#fff', anchor='w')
        self.board_label.pack(fill='x')

        self.pot_label = tk.Label(state_frame, text="Pot: $--", font=('Courier', 9),
                                 bg='#2d2d2d', fg='#ffff00', anchor='w')
        self.pot_label.pack(fill='x')

        tk.Frame(right, height=1, bg='#555').pack(fill='x', pady=3)

        # Decision
        self.decision_label = tk.Label(right, text="--", font=('Arial', 14, 'bold'),
                                      bg='#2d2d2d', fg='#00ffff')
        self.decision_label.pack(pady=2)

        self.reasoning_label = tk.Label(right, text="Press F9 for advice", font=('Arial', 8),
                                       bg='#2d2d2d', fg='#aaa', wraplength=280, justify='left')
        self.reasoning_label.pack(pady=2)

        # Confidence & time
        meta_frame = tk.Frame(right, bg='#2d2d2d')
        meta_frame.pack(fill='x', padx=5)

        self.conf_label = tk.Label(meta_frame, text="", font=('Arial', 8),
                                  bg='#2d2d2d', fg='#888')
        self.conf_label.pack(side='left')

        self.time_label = tk.Label(meta_frame, text="", font=('Arial', 8),
                                  bg='#2d2d2d', fg='#888')
        self.time_label.pack(side='right')

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

    def _analyze_thread(self):
        """Background analysis"""
        import time
        start = time.time()

        try:
            # Get active window (no calibration needed!)
            active = gw.getActiveWindow()
            if not active:
                self.root.after(0, lambda: self.log("No active window", "ERROR"))
                return

            # Screenshot active window directly
            region = (active.left, active.top, active.width, active.height)
            self.root.after(0, lambda: self.log(f"Window: {active.title[:40]}...", "DEBUG"))

            img = pyautogui.screenshot(region=region)
            self.last_screenshot = img

            # Save temp file for API
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                img.save(f.name)
                temp_path = f.name

            try:
                # AI analysis
                self.root.after(0, lambda: self.log(f"API call ({MODEL})...", "DEBUG"))
                vision = VisionDetector(logger=lambda m, l="DEBUG": self.root.after(0, lambda: self.log(m, l)))
                result = vision.detect_poker_elements(temp_path, include_decision=True)

                elapsed = time.time() - start
                self.root.after(0, lambda: self._display_result(result, elapsed, img))

            finally:
                os.unlink(temp_path)

        except Exception as e:
            import traceback
            self.root.after(0, lambda: self.log(f"Error: {e}", "ERROR"))
            self.root.after(0, lambda: self.log(traceback.format_exc(), "DEBUG"))
        finally:
            self._analyzing = False
            self.root.after(0, lambda: self.status_label.config(text="Ready", fg='#00ff00'))

    def _display_result(self, result, elapsed, screenshot):
        """Display analysis result"""
        if not result:
            self.log("No result from AI", "ERROR")
            return

        # Extract data
        cards = result.get('hero_cards', ['??', '??'])
        board = result.get('community_cards', [])
        pot = result.get('pot', 0) or 0
        action = result.get('recommended_action', 'fold')
        amount = result.get('recommended_amount', 0) or 0
        reasoning = result.get('reasoning', '')
        confidence = result.get('confidence', 0.95) or 0.95

        # Log result
        cards_str = ' '.join(cards) if cards else '--'
        board_str = ' '.join(board) if board else '--'
        self.log(f"Cards: {cards_str} | Board: {board_str} | Pot: ${pot}", "INFO")

        decision_str = f"=> {action.upper()}" + (f" ${amount}" if amount else "")
        self.log(decision_str, "INFO")

        if reasoning:
            self.log(reasoning[:150], "DEBUG")

        # Update right panel
        self.cards_label.config(text=f"Cards: {cards_str}")
        self.board_label.config(text=f"Board: {board_str}")
        self.pot_label.config(text=f"Pot: ${pot}")

        self.decision_label.config(text=decision_str.replace("=> ", ""))
        self.reasoning_label.config(text=reasoning[:100] + "..." if len(reasoning) > 100 else reasoning)

        conf_color = '#00ff00' if confidence > 0.9 else '#ffff00' if confidence > 0.7 else '#ff8800'
        self.conf_label.config(text=f"Conf: {confidence:.0%}", fg=conf_color)
        self.time_label.config(text=f"{elapsed:.1f}s")

        # Update thumbnail
        self._update_thumbnail(screenshot)

    def _update_thumbnail(self, img):
        """Update screenshot thumbnail"""
        try:
            # Resize to fit canvas
            thumb = img.copy()
            thumb.thumbnail((280, 80), Image.Resampling.LANCZOS)
            self._thumb_photo = ImageTk.PhotoImage(thumb)
            self.thumb_canvas.delete("all")
            self.thumb_canvas.create_image(140, 40, image=self._thumb_photo)
        except Exception as e:
            self.log(f"Thumbnail error: {e}", "DEBUG")

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

    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    app = HelperBar()
    app.run()


if __name__ == '__main__':
    main()
