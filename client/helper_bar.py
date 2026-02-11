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
IS_WINDOWS = sys.platform == 'win32'
import tempfile
import json
import traceback
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategy_engine import DEFAULT_STRATEGY

# Parse command line arguments
import argparse
parser = argparse.ArgumentParser(description='OnyxPoker Helper Bar')
parser.add_argument('--ai-only', action='store_true', help='Use AI for both vision and decisions')
parser.add_argument('--v1', action='store_true', help='Use V1 vision (no player detection)')
parser.add_argument('--v2', action='store_true', default=True, help='Use V2 vision with player detection (default)')
parser.add_argument('--strategy', type=str, default=DEFAULT_STRATEGY, help=f'Strategy to use (default: {DEFAULT_STRATEGY})')
parser.add_argument('--calibrate', action='store_true', help='Memory calibration mode: scan memory alongside screenshots')
parser.add_argument('--bot', action='store_true', help='Enable bot mode: auto-plays using strategy + clicks buttons')
args = parser.parse_args()

# Default: V2 vision with player names + opponent stats
# --v1: V1 vision (no player detection)
# --ai-only: gpt-5.2 does both vision + decision
# --calibrate: Memory calibration mode
AI_ONLY_MODE = args.ai_only
V1_MODE = args.v1
VISION_V2_MODE = args.v2
STRATEGY = args.strategy
CALIBRATE_MODE = args.calibrate
BOT_MODE = args.bot

if AI_ONLY_MODE:
    from vision_detector import VisionDetector, MODEL
elif V1_MODE:
    from vision_detector_lite import VisionDetectorLite, DEFAULT_MODEL
    from strategy_engine import StrategyEngine
else:
    from vision_detector_v2 import VisionDetectorV2, DEFAULT_MODEL
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
        bar_height = 440
        self.root.geometry(f"{screen_w}x{bar_height}+0+{screen_h - bar_height - 40}")

        # No window decorations
        self.root.overrideredirect(True)
        
        # Always on top
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)

        # State
        self.log_queue = queue.Queue()
        self._analyzing = False
        self.last_screenshot = None
        self.bot_running = False
        
        # Session state for aggressor tracking
        self.last_preflop_action = None  # 'open', 'call', or None
        self.last_pot = 0  # Track pot to detect new hands
        self.last_street = None  # Track street for raise detection
        self.last_hero_action = None  # Track hero's last action this street
        self.last_hero_cards = None  # Track hero cards to detect new hand
        self.last_opponents = []  # Track opponents across screenshots
        
        # Memory polling state
        self._mem_buf_addr = None  # Known buffer address for fast rescan
        self._mem_hand_id = None   # Current hand_id being tracked
        self._mem_polling = False  # Whether polling loop is active
        self._mem_last_entries = 0 # Last known entry count (detect updates)
        self._last_result = None   # Last GPT result for re-evaluation during polling
        self._pending_mem_poll = None  # (buf_addr, hand_id) to start after display
        self._last_mem_display = None  # Last memory display data (for STALE warning)
        self._last_mem_time = None     # Timestamp of last memory update
        
        # Drag state
        self._drag_start_x = 0
        self._drag_start_y = 0
        
        # Resize state
        self._resize_edge = None
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_w = 0
        self._resize_start_h = 0

        self.create_ui()
        self.register_hotkeys()
        self.update_log_display()

        # Startup validation
        self.log("OnyxPoker ready | F9=Advice F10=Bot F11=Stop F12=Hide", "INFO")
        if IS_WINDOWS:
            self.log(f"Memory: Windows detected, live scanning enabled", "DEBUG")
            if CALIBRATE_MODE:
                self.log(f"Memory: Calibration mode - dumps will be saved", "DEBUG")
        else:
            self.log(f"Memory: Linux - memory scanning disabled", "DEBUG")
        self.log(f"Strategy: {STRATEGY}", "DEBUG")
        self.log(f"Vision: {'V1 (no opponents)' if V1_MODE else 'V2 (opponent detection)'}", "DEBUG")
        if AI_ONLY_MODE:
            self.log(f"Mode: AI-only (GPT does vision + decision)", "DEBUG")

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

        # === LEFT: Live Log (expandable) ===
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
        self.log_text = scrolledtext.ScrolledText(center, font=('Courier', 9),
                                                  bg='#0d0d0d', fg='#ccc',
                                                  wrap='word', height=10)
        self.log_text.pack(fill='both', expand=True, pady=2)

        # Color tags
        self.log_text.tag_configure('INFO', foreground='#00ff00', font=('Courier', 9))
        self.log_text.tag_configure('DEBUG', foreground='#00ffff', font=('Courier', 9))
        self.log_text.tag_configure('ERROR', foreground='#ff4444', font=('Courier', 10, 'bold'))
        self.log_text.tag_configure('DECISION', foreground='#ffff00', font=('Courier', 11, 'bold'))

        # === RIGHT: Decision Stats (50% of screen width) ===
        right_width = int(self.root.winfo_screenwidth() * 0.5)
        right = tk.Frame(bottom, bg='#2d2d2d', width=right_width)
        right.pack(side='right', fill='y', padx=2, pady=2)
        right.pack_propagate(False)

        # Stats display (scrollable) - same font as main log
        stats_scroll = scrolledtext.ScrolledText(right, font=('Courier', 9),
                                                bg='#1a1a1a', fg='#ccc',
                                                wrap='word', height=8)
        stats_scroll.pack(fill='both', expand=True, padx=5, pady=2)
        self.stats_text = stats_scroll

        # Color tags for stats - same font as main log
        self.stats_text.tag_configure('HAND', foreground='#00ff00', font=('Courier', 10, 'bold'))
        self.stats_text.tag_configure('DRAW', foreground='#00ffff', font=('Courier', 9))
        self.stats_text.tag_configure('DANGER', foreground='#ff8800', font=('Courier', 9))
        self.stats_text.tag_configure('OPPONENT', foreground='#ff66ff', font=('Courier', 10, 'bold'))
        self.stats_text.tag_configure('ADVICE', foreground='#ffcc00', font=('Courier', 9))
        self.stats_text.tag_configure('MEM', foreground='#00ff88', font=('Courier', 9, 'bold'))
        self.stats_text.tag_configure('MEMDATA', foreground='#88ffcc', font=('Courier', 9))
        self.stats_text.tag_configure('ACTION', foreground='#ffff00', font=('Courier', 12, 'bold'))

        # Time
        self.time_label = tk.Label(right, text="", font=('Arial', 9),
                                  bg='#2d2d2d', fg='#888')
        self.time_label.pack(pady=2)

    def log(self, message, level="INFO"):
        """Add message to log queue and buffer for session log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put((timestamp, level, message))
        # Buffer for session log
        if not hasattr(self, 'ui_log_buffer'):
            self.ui_log_buffer = []
        self.ui_log_buffer.append(f"[{timestamp}] {level}: {message}")

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

    def _load_player_stats(self):
        """Load player stats from JSON file"""
        stats_path = os.path.join(os.path.dirname(__file__), 'player_stats.json')
        if os.path.exists(stats_path):
            with open(stats_path) as f:
                return json.load(f)
        return {}

    def _get_advice(self, archetype):
        """Get advice text for archetype - just returns what's in the DB"""
        # Fallback only if DB doesn't have advice
        fallback = {
            'fish': "Isolate wide | Value bet | Calls too much | Never bluff",
            'nit': "Steal blinds | Fold to bets | Too tight | Raise IP, fold to 3bet",
            'rock': "Steal more | Bet = nuts | Raises monsters | Raise IP, fold vs bet",
            'tag': "Respect raises | Play solid | Avoid | vs raise: TT+/AK",
            'lag': "Tighten up | Call down | Over-aggro | vs raise: 99+/AQ+, call down",
            'maniac': "Only premiums | Call everything | Can't fold | vs raise: QQ+/AK, call down",
        }
        return fallback.get(archetype, "no reads")

    def _is_action_word(self, name):
        """Check if name is actually an action word (shown when player acts)"""
        if not name:
            return True
        action_words = ['fold', 'check', 'call', 'raise', 'bet', 'all-in', 'allin', 
                        'post', 'muck', 'show', 'sit out', 'sitting out']
        name_lower = name.lower()
        # Check if starts with action word (e.g., "Call €0.10", "Raise €0.50")
        for word in action_words:
            if name_lower.startswith(word):
                return True
        return False

    def _merge_opponents(self, new_opponents, hero_cards):
        """Merge new opponent detection with previous, handling action word names"""
        hero_cards_changed = (hero_cards != self.last_hero_cards)
        
        if hero_cards_changed:
            # New hand - reset, but filter out action words
            self.last_hero_cards = hero_cards
            self.last_opponents = [o for o in new_opponents if not self._is_action_word(o.get('name'))]
            return new_opponents
        
        # Same hand - merge with previous opponents
        # Keep all previous names, update has_cards from new detection
        merged = []
        new_real_names = {o['name']: o for o in new_opponents if not self._is_action_word(o.get('name'))}
        
        for prev in self.last_opponents:
            name = prev.get('name')
            if name in new_real_names:
                # Found in new detection - use new has_cards
                merged.append(new_real_names[name])
            else:
                # Not in new detection - keep previous (might have folded or showing action)
                merged.append(prev)
        
        # Add any new real names not in previous
        for name, opp in new_real_names.items():
            if not any(m.get('name') == name for m in merged):
                merged.append(opp)
        
        self.last_opponents = merged
        return merged

    def _lookup_opponent_stats(self, opponents):
        """Lookup stats for detected opponents - advice comes from DB"""
        stats_db = self._load_player_stats()
        opponent_stats = []
        for p in opponents:
            name = p.get('name', '')
            if name in stats_db:
                s = stats_db[name]
                opponent_stats.append({
                    'name': name,
                    'hands': s.get('hands', 0),
                    'archetype': s.get('archetype', 'unknown'),
                    'advice': s.get('advice', self._get_advice(s.get('archetype', 'unknown')))
                })
            else:
                opponent_stats.append({
                    'name': name,
                    'hands': 0,
                    'archetype': 'unknown',
                    'advice': 'no reads'
                })
        return opponent_stats

    def _format_opponent_line(self, opponent_stats):
        """Format compact opponent line for sidebar"""
        parts = []
        for o in opponent_stats:
            if o['hands'] > 0:
                parts.append(f"{o['name']}: {o['archetype'].upper()} ({o['hands']}h)")
        return ' | '.join(parts) if parts else 'No known opponents'

    def _format_advice_line(self, opponent_stats):
        """Format advice for all opponents (known and unknown)"""
        lines = []
        unknown_count = 0
        for o in opponent_stats:
            if o['hands'] > 0:
                lines.append(f"{o['name']}: {o['advice']}")
            else:
                unknown_count += 1
        if unknown_count > 0:
            lines.append(f"UNKNOWN - {unknown_count}")
        return '\n'.join(lines) if lines else 'No opponent data'

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

        # Stop any active memory polling from previous hand
        self._mem_polling = False

        self._analyzing = True
        #self.status_label.config(text="Analyzing...", fg='#ffff00')
        self.log("F9: Analyzing...", "INFO")

        thread = threading.Thread(target=self._analyze_thread, daemon=True)
        thread.start()

    def _analyze_thread(self, test_image_path=None):
        """Background analysis. If test_image_path provided, use that instead of screenshot."""
        start = time.time()
        screenshot_name = None
        memory_candidates = None  # For calibration mode

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
                # Removed verbose log

                img = pyautogui.screenshot(region=region)
                self.last_screenshot = img

                # Save to screenshots folder for future testing
                screenshots_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
                os.makedirs(screenshots_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_name = f'{timestamp}.png'
                saved_path = os.path.join(screenshots_dir, screenshot_name)
                img.save(saved_path)
                # Removed verbose log

                # Memory scan (parallel with GPT) + ALWAYS dump (decide later to keep/delete)
                dump_id_holder = [None]
                mem_result = [None]  # mutable for thread
                mem_thread = None
                dump_thread = None
                if IS_WINDOWS:
                    def _mem_scan():
                        try:
                            from memory_calibrator import scan_live
                            mem_result[0] = scan_live()
                        except Exception as e:
                            mem_result[0] = {'error': str(e)}
                    mem_thread = threading.Thread(target=_mem_scan, daemon=True)
                    mem_thread.start()
                    
                    # ALWAYS dump at same instant as screenshot (not just --calibrate)
                    def _dump():
                        try:
                            from memory_calibrator import save_dump
                            dump_id_holder[0] = save_dump(timestamp)
                        except Exception as e:
                            print(f"[DUMP] Error: {e}")
                    dump_thread = threading.Thread(target=_dump, daemon=True)
                    dump_thread.start()

                # Also save temp for API
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                    img.save(f.name)
                    temp_path = f.name
                delete_temp = True

            try:
                # AI analysis
                if AI_ONLY_MODE:
                    # AI-only mode: gpt-5.2 does both vision + decision
                    # Removed verbose API log
                    api_start = time.time()
                    vision = VisionDetector(logger=lambda m, l="DEBUG": self.root.after(0, lambda: self.log(m, l)))
                    result = vision.detect_poker_elements(temp_path, include_decision=True)
                    api_time = time.time() - api_start
                    
                    # For AI-only mode, just use the single result
                    all_position_results = None
                elif V1_MODE:
                    # V1 mode: gpt-5.2 for vision, strategy_engine for decision (no player detection)
                    # Removed verbose API log
                    api_start = time.time()
                    vision = VisionDetectorLite(logger=lambda m, l="DEBUG": self.root.after(0, lambda: self.log(m, l)))
                    table_data = vision.detect_table(temp_path)
                    api_time = time.time() - api_start
                    
                    engine = StrategyEngine(STRATEGY)
                    board = table_data.get('community_cards', [])
                    
                    if board:  # Postflop - use real to_call
                        if self.last_preflop_action == 'open':
                            is_aggressor = True
                        elif self.last_preflop_action == 'call':
                            is_aggressor = False
                        else:
                            is_aggressor = True
                        table_data['is_aggressor'] = is_aggressor
                        
                        # Detect villain raise: hero already acted this street, now faces bet
                        current_street = 'flop' if len(board) == 3 else ('turn' if len(board) == 4 else 'river')
                        if current_street != self.last_street:
                            self.last_hero_action = None
                            self.last_street = current_street
                        to_call = table_data.get('to_call', 0)
                        is_facing_raise = self.last_hero_action in ('bet', 'raise', 'check') and to_call and to_call > 0
                        if is_facing_raise:
                            self.log(f"Villain raised on {current_street}!", "INFO")
                        table_data['is_facing_raise'] = is_facing_raise
                        
                        # Single decision with real to_call
                        decision = engine.get_action(table_data)
                        result = {**table_data, **decision}
                        result['api_time'] = api_time
                        result['all_positions'] = None
                    else:  # Preflop - calculate for all 6 positions with to_call=0
                        all_position_results = {}
                        for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
                            pos_data = {**table_data, 'position': pos, 'to_call': 0}
                            decision = engine.get_action(pos_data)
                            all_position_results[pos] = decision
                        result = {**table_data, **all_position_results['BTN']}
                        result['api_time'] = api_time
                        result['all_positions'] = all_position_results
                else:
                    # Default: V2 mode - vision with player detection + strategy engine
                    # Removed verbose API log
                    api_start = time.time()
                    vision = VisionDetectorV2(logger=lambda m, l="DEBUG": self.root.after(0, lambda: self.log(m, l)))
                    table_data = vision.detect_table(temp_path)
                    api_time = time.time() - api_start
                    
                    # Merge opponents with previous detection (handles action words as names)
                    hero_cards = table_data.get('hero_cards')
                    raw_opponents = table_data.get('opponents', [])
                    merged_opponents = self._merge_opponents(raw_opponents, hero_cards)
                    table_data['opponents'] = merged_opponents
                    
                    # Lookup opponent stats
                    opponent_stats = self._lookup_opponent_stats(merged_opponents)
                    table_data['opponent_stats'] = opponent_stats
                    table_data['opponent_line'] = self._format_opponent_line(opponent_stats)
                    table_data['advice_line'] = self._format_advice_line(opponent_stats)
                    
                    # Debug: log opponent stats
                    self.root.after(0, lambda n=len(opponent_stats): 
                        self.log(f"[DEBUG] Opponent stats: {n} players", "DEBUG"))
                    
                    # Calculate num_players from opponents array (V2 doesn't return num_players)
                    opponents = table_data.get('opponents', [])
                    active_opponents = sum(1 for o in opponents if o.get('has_cards', False))
                    table_data['num_players'] = active_opponents + 1  # +1 for hero
                    
                    engine = StrategyEngine(STRATEGY)
                    board = table_data.get('community_cards', [])
                    
                    if board:  # Postflop
                        table_data['is_aggressor'] = self.last_preflop_action == 'open'
                        decision = engine.get_action(table_data)
                        result = {**table_data, **decision}
                    else:  # Preflop - all positions
                        all_position_results = {}
                        for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
                            pos_data = {**table_data, 'position': pos, 'to_call': 0}
                            decision = engine.get_action(pos_data)
                            all_position_results[pos] = decision
                        result = {**table_data, **all_position_results['BTN']}
                        result['all_positions'] = all_position_results
                        # Ensure opponent_stats is preserved
                        result['opponent_stats'] = table_data.get('opponent_stats', [])
                    result['api_time'] = api_time

                # CALIBRATION: Wait for dump, then tag with GPT results
                if CALIBRATE_MODE and dump_thread:
                    dump_thread.join(timeout=120)
                    dump_id = dump_id_holder[0]
                    if dump_id:
                        try:
                            from memory_calibrator import tag_dump
                            tag_dump(dump_id, result)
                            print(f"[CALIBRATE] Tagged {dump_id}: hand={result.get('hand_id')} cards={result.get('hero_cards')}")
                        except Exception as e:
                            print(f"[CALIBRATE] Tag error: {e}")
                

                # Merge memory scan results (if running on Windows)
                if IS_WINDOWS and mem_thread:
                    mem_thread.join(timeout=10)
                    mr = mem_result[0]
                    if mr and not mr.get('error'):
                        result['memory_cards'] = mr.get('hero_cards')
                        result['memory_hand_id'] = mr.get('hand_id')
                        result['memory_players'] = mr.get('players')
                        result['memory_actions'] = mr.get('actions')
                        result['memory_community'] = mr.get('community_cards')
                        result['memory_scan_time'] = mr.get('scan_time')
                        result['memory_container_addr'] = mr.get('container_addr')
                        result['memory_buf_addr'] = mr.get('buf_addr')
                        result['memory_entry_count'] = mr.get('entry_count')
                        mc = mr.get('hero_cards')
                        if mc and len(mc) == 4:
                            gpt_cards = result.get('hero_cards', [])
                            mem_cards = [mc[0:2], mc[2:4]]
                            if gpt_cards != mem_cards:
                                result['memory_status'] = f"OVERRIDE {gpt_cards}->{mem_cards}"
                                self.root.after(0, lambda g=gpt_cards, m=mem_cards:
                                    self.log(f"[MEM] Cards override: GPT {g} -> MEM {m}", "INFO"))
                            else:
                                result['memory_status'] = 'CONFIRMED'
                            result['hero_cards'] = mem_cards
                        if not result.get('hand_id') and mr.get('hand_id'):
                            result['hand_id'] = mr['hand_id']
                        # Position from memory (hero_seat + bb_seat → exact position)
                        if mr.get('position'):
                            result['position'] = mr['position']
                            self.root.after(0, lambda p=mr['position']:
                                self.log(f"[MEM] Position: {p}", "DEBUG"))
                        st = mr.get('scan_time', '?')
                        self.root.after(0, lambda s=st, c=mr.get('hero_cards'):
                            self.log(f"[MEM] {c} hand={mr.get('hand_id')} ({s}s)", "INFO"))
                        # Save poll params — polling starts AFTER _display_result
                        if mr.get('buf_addr') and mr.get('hand_id'):
                            self._pending_mem_poll = (mr['buf_addr'], mr['hand_id'])
                    elif mr and mr.get('error'):
                        result['memory_error'] = mr['error']
                        result['memory_status'] = 'ERROR'
                        self.root.after(0, lambda e=mr['error']:
                            self.log(f"[MEM] Error: {e}", "ERROR"))
                    else:
                        result['memory_status'] = 'NO_BUFFER'
                        self.root.after(0, lambda: self.log("[MEM] No buffer found", "DEBUG"))
                
                # Tag dump with GPT results (for offline analysis)
                if IS_WINDOWS and dump_id_holder[0]:
                    def _tag_and_cleanup():
                        try:
                            from memory_calibrator import tag_dump
                            import os
                            tag_dump(dump_id_holder[0], result)
                            # Delete dump if memory scan succeeded (keep only failures)
                            if result.get('memory_status') in ('CONFIRMED', 'OVERRIDE'):
                                dump_dir = os.path.join(os.path.dirname(__file__), 'memory_dumps')
                                bin_path = os.path.join(dump_dir, f"{dump_id_holder[0]}.bin")
                                json_path = os.path.join(dump_dir, f"{dump_id_holder[0]}.json")
                                if os.path.exists(bin_path):
                                    os.remove(bin_path)
                                if os.path.exists(json_path):
                                    os.remove(json_path)
                            else:
                                # Keep failure dumps for debugging
                                self.root.after(0, lambda d=dump_id_holder[0]:
                                    self.log(f"[MEM] Failure dump saved: {d}", "DEBUG"))
                        except Exception as e:
                            print(f"[DUMP] Tag error: {e}")
                    threading.Thread(target=_tag_and_cleanup, daemon=True).start()

                elapsed = time.time() - start
                # Removed verbose API timing log
                self._last_result = result  # Store for memory re-evaluation
                
                # Add user-friendly summary log
                cards = result.get('hero_cards', [])
                cards_str = ' '.join(cards) if cards else '??'
                board = result.get('community_cards', [])
                board_str = ' '.join(board) if board else '--'
                pot = result.get('pot', 0)
                action = result.get('action', '').upper()
                amt = result.get('bet_size')
                if amt and action in ('BET', 'RAISE'):
                    action_str = f"{action} €{amt:.2f}"
                else:
                    action_str = action
                
                self.root.after(0, lambda c=cards_str, b=board_str, p=pot: 
                    self.log(f"F9: {c} | {b} | Pot €{p:.2f}", "INFO"))
                self.root.after(0, lambda a=action_str, r=result.get('reasoning', ''): 
                    self.log(f"=> {a} ({r})", "INFO"))
                
                self.root.after(0, lambda: self._display_result(result, elapsed, img, screenshot_name))

            finally:
                if delete_temp:
                    os.unlink(temp_path)

        except Exception as e:
            self.root.after(0, lambda: self.log(f"Error: {e}", "ERROR"))
            self.root.after(0, lambda: self.log(traceback.format_exc(), "DEBUG"))
        finally:
            self._analyzing = False
            self.root.after(0, lambda: None)  # status update removed

    def _start_mem_poll(self, buf_addr, hand_id):
        """Start polling the known buffer address for live updates."""
        # ALWAYS update tracking (even if already polling)
        # This handles F9 detecting new hand while old hand still polling
        self._mem_buf_addr = buf_addr
        self._mem_hand_id = hand_id
        self._mem_last_entries = 0
        
        if not self._mem_polling:
            self._mem_polling = True
            threading.Thread(target=self._mem_poll_loop, daemon=True).start()
            self._mem_polling = True
            threading.Thread(target=self._mem_poll_loop, daemon=True).start()

    def _mem_poll_loop(self):
        """Background thread: rescan buffer every 200ms, push UI updates."""
        from memory_calibrator import rescan_buffer, scan_live
        self.root.after(0, lambda: self.log("[MEM] Polling started", "DEBUG"))
        while self._mem_polling:
            try:
                hd = rescan_buffer(self._mem_buf_addr, self._mem_hand_id)
                if hd is None:
                    # Buffer lost - try full rescan (with retry)
                    self.root.after(0, lambda: self.log("[MEM] Buffer lost, rescanning...", "DEBUG"))
                    fresh_data = None
                    for attempt in range(3):  # Try 3 times
                        fresh_data = scan_live()
                        if fresh_data and fresh_data.get('hero_cards'):
                            break
                        time.sleep(0.1)  # Wait 100ms between attempts
                    
                    if fresh_data and fresh_data.get('hero_cards'):
                        # Re-scan success - update tracking
                        self._mem_hand_id = fresh_data['hand_id']
                        self._mem_buf_addr = fresh_data['buf_addr']
                        self._mem_last_entries = 0
                        hd = fresh_data
                        self.root.after(0, lambda h=fresh_data['hand_id'], c=fresh_data.get('hero_cards'): 
                            self.log(f"[MEM] Re-scan OK: hand {h}, cards {c[0:2]} {c[2:4]}", "INFO"))
                    else:
                        # Re-scan failed after 3 attempts - keep trying (don't stop)
                        self.root.after(0, lambda: self.log("[MEM] Re-scan failed, retrying...", "DEBUG"))
                        time.sleep(0.5)  # Wait longer before next poll cycle
                        continue  # Skip this cycle, try again
                
                # Check if hand changed
                if hd.get('hand_id_changed'):
                    new_hand_id = hd.get('hand_id')
                    new_buf_addr = hd.get('buf_addr')
                    
                    # Update tracking
                    self._mem_hand_id = new_hand_id
                    self._mem_buf_addr = new_buf_addr
                    self._mem_last_entries = 0
                    
                    # Log new hand
                    cards = hd.get('hero_cards', '')
                    if cards and len(cards) == 4:
                        self.root.after(0, lambda h=new_hand_id, c=cards: 
                            self.log(f"[MEM] New hand {h}, cards {c[0:2]} {c[2:4]}", "INFO"))
                    else:
                        self.root.after(0, lambda h=new_hand_id: 
                            self.log(f"[MEM] New hand {h}", "INFO"))
                    
                    # CRITICAL: Update display immediately when hand changes
                    # This shows the new cards without waiting for F9
                    self.root.after(0, lambda d=hd: self._update_mem_display(d, hd.get('entry_count', 0)))
                
                n = hd.get('entry_count', 0)
                # Always update UI (not just when entry count changes)
                # This ensures right panel shows live data even if no new actions
                
                # Log new actions to left panel
                if n > self._mem_last_entries and not hd.get('hand_id_changed'):
                    actions = hd.get('actions', [])
                    # Get last few actions (new ones)
                    new_actions = actions[-(n - self._mem_last_entries):]
                    for name, act, amt in new_actions:
                        if act not in ('POST_SB', 'POST_BB', 'DEAL', '0x77', 'WIN'):
                            if amt > 0:
                                self.root.after(0, lambda n=name, a=act, m=amt: 
                                    self.log(f"[MEM] {n}: {a} €{m/100:.2f}", "INFO"))
                            else:
                                self.root.after(0, lambda n=name, a=act: 
                                    self.log(f"[MEM] {n}: {a}", "INFO"))
                
                self._mem_last_entries = n
                # Update UI on every poll (not just when count changes)
                self.root.after(0, lambda d=hd, cnt=n: self._update_mem_display(d, cnt))
            except Exception as e:
                self._mem_polling = False
                self.root.after(0, lambda e=e: self.log(f"[MEM] Poll error: {e}", "ERROR"))
                break
            time.sleep(0.2)

    def _update_mem_display(self, hd, entry_count=0):
        """Update right panel: show context + advice + live actions."""
        cc = hd.get('community_cards', [])
        actions = hd.get('actions', [])
        mc = hd.get('hero_cards', '')
        
        # Save display data and timestamp
        self._last_mem_display = hd
        self._last_mem_time = time.time()
        
        # Re-evaluate strategy with memory data
        advice = self._reeval_with_memory(hd)
        
        # Check if data is stale (no cards but we have cached data)
        is_stale = not mc and hd.get('hand_id') and advice
        
        # Rebuild right panel
        self.stats_text.delete('1.0', 'end')

        # === SECTION 1: CONTEXT HEADER ===
        # Use POLL data (hd), not cached F9 data
        
        # Cards from poll
        if mc and len(mc) == 4:
            cards_str = f"{mc[0:2]} {mc[2:4]}"
        else:
            cards_str = "??"
        
        # Board from poll
        board_str = ' '.join(cc) if cc else '--'
        
        # Pot and to_call from advice debug (calculated from poll actions)
        debug = advice.get('_mem_debug', {}) if advice else {}
        pot = debug.get('pot', 0.07)
        to_call = debug.get('to_call', 0)
        
        # Position from poll players data
        players = hd.get('players', {})
        position = '?'
        if players:
            # Find hero seat
            hero_seat = None
            for seat, name in players.items():
                if name == 'idealistslp':
                    hero_seat = int(seat)
                    break
            # Find BB seat (first POST_BB action)
            bb_seat = None
            for name, act, amt in actions:
                if act == 'POST_BB':
                    for seat, pname in players.items():
                        if pname == name:
                            bb_seat = int(seat)
                            break
                    break
            # Calculate position
            if hero_seat is not None and bb_seat is not None:
                n_players = len(players)
                pos_idx = (hero_seat - bb_seat - 1) % n_players
                positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
                if n_players == 6:
                    position = positions[pos_idx]
                elif n_players < 6:
                    position = positions[pos_idx] if pos_idx < len(positions) else '?'
        
        # Num players from poll
        num_players = len(players) if players else debug.get('num_players', '?')
        
        # Display header
        self.stats_text.insert('end', f"{cards_str} | {board_str} | €{pot:.2f} | Call €{to_call:.2f}\n", 'MEM')
        self.stats_text.insert('end', f"{position} | {num_players}p", 'MEMDATA')
        if is_stale:
            self.stats_text.insert('end', " | STALE", 'DANGER')
        self.stats_text.insert('end', "\n", 'MEMDATA')

        # === SECTION 2: Hero Advice (LARGE) ===
        if advice:
            act = advice.get('action', '').upper()
            amt = advice.get('bet_size')
            act_str = f"{act} €{amt:.2f}" if amt and act in ('BET', 'RAISE') else act
            
            self.stats_text.insert('end', f"=> {act_str}\n", 'ACTION')
            
            reason = advice.get('reasoning', '')
            if reason:
                self.stats_text.insert('end', f"{reason}\n", 'DRAW')
            
            # Hand strength
            ha = advice.get('hand_analysis', {})
            if ha and ha.get('valid'):
                self.stats_text.insert('end', self._hand_strength_str(ha) + '\n', 'HAND')
        else:
            self.stats_text.insert('end', f"[Calculating...]\n", 'MEM')

        # === SECTION 3: Opponent Info (from last F9 only) ===
        lr = self._last_result or {}
        if lr.get('opponent_stats'):
            self.stats_text.insert('end', '---\n', 'MEMDATA')
            for opp in lr['opponent_stats']:
                if opp.get('hands', 0) > 0:
                    self.stats_text.insert('end',
                        f"{opp['name']} ({opp['archetype'].upper()})\n", 'OPPONENT')

        # === SECTION 4: Live Actions (last 8 only) ===
        if actions:
            self.stats_text.insert('end', '---\n', 'MEMDATA')
            
            # Build action list (skip blinds, DEAL markers, WIN messages)
            action_lines = []
            for name, act_code, amt in actions:
                if act_code in ('POST_SB', 'POST_BB', 'DEAL', '0x77'):
                    continue
                if name is None:
                    continue
                    
                line = f"{name}: {act_code}"
                if amt > 0:
                    line += f" €{amt/100:.2f}"
                is_hero = (name == 'idealistslp')
                action_lines.append(('hero' if is_hero else 'villain', line))
            
            # Show last 8 actions only
            for kind, line in action_lines[-8:]:
                if kind == 'hero':
                    self.stats_text.insert('end', line + '\n', 'MEM')
                else:
                    self.stats_text.insert('end', line + '\n', 'MEMDATA')
        
        # === SECTION 5: Memory Status (container/buffer info) ===
        buf_addr = hd.get('buf_addr')
        container_addr = hd.get('container_addr')
        scan_time = hd.get('scan_time', 0)
        
        if buf_addr or container_addr:
            self.stats_text.insert('end', '---\n', 'MEMDATA')
            if container_addr:
                self.stats_text.insert('end', f"Container: {hex(container_addr)}\n", 'MEMDATA')
            if buf_addr:
                self.stats_text.insert('end', f"Buffer: {hex(buf_addr)}", 'MEMDATA')
                if scan_time > 0:
                    self.stats_text.insert('end', f" ({scan_time:.1f}s)\n", 'MEMDATA')
                else:
                    self.stats_text.insert('end', "\n", 'MEMDATA')

        # Update time label
        if is_stale:
            self.time_label.config(text=f"STALE ({entry_count})")
        else:
            self.time_label.config(text=f"LIVE ({entry_count})")

        # Log to session file with full debug info
        self._log_mem_update(hd, advice)

    def _log_mem_update(self, hd, advice):
        """Append a memory poll update to the session log with full debug info."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'mem_poll',
            'hand_id': hd.get('hand_id'),
            'memory_cards': hd.get('hero_cards'),
            'memory_community': hd.get('community_cards', []),
            'memory_actions': hd.get('actions', []),
            'entry_count': hd.get('entry_count', 0),
            'buf_addr': hex(hd['buf_addr']) if hd.get('buf_addr') else None,
            'hand_id_changed': hd.get('hand_id_changed', False),
        }
        if advice:
            entry['action'] = advice.get('action')
            entry['bet_size'] = advice.get('bet_size')
            entry['reasoning'] = advice.get('reasoning')
            # Include debug info for analysis
            debug = advice.get('_mem_debug', {})
            if debug:
                entry['debug'] = debug
        try:
            with open(SESSION_LOG, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception:
            pass

    def _reeval_with_memory(self, hd):
        """Re-run strategy engine using memory data. Returns decision dict or None."""
        try:
            # Get hero cards from memory, fall back to cached F9 cards
            mc = hd.get('hero_cards', '')
            lr = self._last_result or {}
            if mc and len(mc) == 4:
                cards = [mc[0:2], mc[2:4]]
            elif lr.get('memory_cards'):  # Use cached memory cards from initial scan
                mc = lr['memory_cards']
                cards = [mc[0:2], mc[2:4]]
            elif lr.get('hero_cards'):  # Last resort: F9 GPT cards
                cards = lr['hero_cards']
            else:
                self.log("[MEM] No cards available", "DEBUG")
                return None
            
            cc = hd.get('community_cards', [])
            board = cc if cc else []
            actions = hd.get('actions', [])
            
            # Parse actions to calculate pot, to_call, is_aggressor, is_facing_raise
            pot_cents = 0
            current_street_start = 0
            hero_acted_this_street = False
            hero_last_action = None
            
            # Find current street start (last DEAL marker)
            for i, (name, act, amt) in enumerate(actions):
                if act == 'DEAL':
                    current_street_start = i + 1
                    hero_acted_this_street = False
                    hero_last_action = None
            
            # Calculate pot (all actions) and track current street
            for i, (name, act, amt) in enumerate(actions):
                if act not in ('DEAL',):
                    pot_cents += amt
                if i >= current_street_start and name == 'idealistslp' and act in ('BET', 'RAISE', 'CALL', 'CHECK'):
                    hero_acted_this_street = True
                    hero_last_action = act
            
            pot = pot_cents / 100.0 if pot_cents > 0 else 0.07
            
            # Calculate to_call on current street
            to_call = 0.0
            last_villain_bet = 0
            hero_street_total = 0
            
            for i, (name, act, amt) in enumerate(actions):
                if i < current_street_start:
                    continue
                if name == 'idealistslp' and act in ('BET', 'RAISE', 'CALL'):
                    hero_street_total += amt / 100.0
                elif act in ('BET', 'RAISE'):
                    last_villain_bet = amt / 100.0
            
            if last_villain_bet > hero_street_total:
                to_call = last_villain_bet - hero_street_total
            
            # is_facing_raise: hero acted, then villain raised
            is_facing_raise = False
            if hero_acted_this_street and to_call > 0:
                # Check if there was a raise AFTER hero's last action
                hero_last_idx = -1
                for i, (name, act, amt) in enumerate(actions):
                    if i >= current_street_start and name == 'idealistslp' and act in ('BET', 'RAISE', 'CALL', 'CHECK'):
                        hero_last_idx = i
                if hero_last_idx >= 0:
                    for i, (name, act, amt) in enumerate(actions):
                        if i > hero_last_idx and act == 'RAISE':
                            is_facing_raise = True
                            break
            
            # is_aggressor: who was last raiser on CURRENT street (or preflop if no flop action yet)
            is_aggressor = False
            last_raiser = None
            search_start = 0 if not board else current_street_start
            for i, (name, act, amt) in enumerate(actions):
                if i < search_start:
                    continue
                if act == 'DEAL':
                    break
                if act == 'RAISE':
                    last_raiser = name
            if last_raiser == 'idealistslp':
                is_aggressor = True
            
            # num_players: count unique players who acted (not folded)
            active_players = set()
            for name, act, amt in actions:
                if name and name != 'idealistslp' and act != 'FOLD':
                    active_players.add(name)
            num_players = len(active_players) + 1  # +1 for hero
            
            # position from memory
            position = hd.get('position') or lr.get('position', 'BTN')
            
            table_data = {
                'hero_cards': cards,
                'community_cards': board,
                'pot': pot,
                'to_call': to_call,
                'big_blind': lr.get('big_blind', 0.05),
                'position': position,
                'num_players': num_players,
                'is_aggressor': is_aggressor,
                'is_facing_raise': is_facing_raise,
                'opponent_stats': lr.get('opponent_stats', []),
                'opponents': lr.get('opponents', []),
            }
            
            engine = StrategyEngine(STRATEGY)
            result = engine.get_action(table_data)
            
            # Add debug info
            if result:
                result['_mem_debug'] = {
                    'pot': pot, 'to_call': to_call, 'is_aggressor': is_aggressor,
                    'is_facing_raise': is_facing_raise, 'num_players': num_players,
                    'hero_acted': hero_acted_this_street, 'hero_last': hero_last_action
                }
            
            return result
            
        except Exception as e:
            self.log(f"[MEM] Reeval error: {e}", "ERROR")
            import traceback
            self.log(f"[MEM] {traceback.format_exc()}", "DEBUG")
            return None

    def _hand_strength_str(self, hand):
        """Return compact hand strength string from hand_analysis dict."""
        s = hand.get('strength', 0)
        if s >= 8: return "STRAIGHT FLUSH"
        if s == 7: return "QUADS"
        if s == 6: return "FULL HOUSE"
        if hand.get('has_flush'):
            return "FLUSH (NUT)" if hand.get('is_nut_flush') else "FLUSH"
        if hand.get('has_straight'): return "STRAIGHT"
        if hand.get('has_set'): return "SET"
        if hand.get('has_trips'): return "TRIPS"
        if hand.get('has_two_pair'):
            return f"TWO PAIR ({hand.get('two_pair_type', '')})"
        if hand.get('is_overpair'): return "OVERPAIR"
        if hand.get('has_top_pair'):
            k = "good K" if hand.get('has_good_kicker') else "weak K"
            return f"TOP PAIR ({k})"
        if hand.get('has_middle_pair'): return "MIDDLE PAIR"
        if hand.get('has_bottom_pair'): return "BOTTOM PAIR"
        if hand.get('is_pocket_pair'): return "UNDERPAIR"
        return "HIGH CARD"

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
        
        # Detect new hand (pot reset to blinds ~$0.07)
        if pot > 0 and pot <= 0.10 and self.last_pot > 0.10:
            self.last_preflop_action = None  # New hand started
            self.last_street = None
            self.last_hero_action = None
            self.log("New hand detected", "DEBUG")
        self.last_pot = pot
        
        # Track hero's action for next F9 press (used for raise detection)
        if action in ('bet', 'raise', 'call', 'check', 'fold'):
            self.last_hero_action = action
        
        # Track preflop aggressor for postflop decisions
        if not board:  # Preflop
            if action in ('bet', 'raise'):
                self.last_preflop_action = 'open'
            elif action == 'call':
                self.last_preflop_action = 'call'
            elif action == 'fold':
                self.last_preflop_action = None
        
        # Save to session log (JSONL format) - includes screenshot name for correlation
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'screenshot': screenshot_name,
            'mode': 'bot' if BOT_MODE else 'manual',
            'hand_id': result.get('hand_id'),
            'hero_cards': cards,
            'board': board,
            'pot': pot,
            'action': action,
            'amount': bet_size,
            'to_call': to_call,
            'big_blind': result.get('big_blind', 0.05),
            'num_players': result.get('num_players', 2),
            'position': result.get('position'),
            'is_aggressor': result.get('is_aggressor'),
            'opponents': result.get('opponents', []),
            'opponent_stats': result.get('opponent_stats', []),  # ADD THIS!
            'reasoning': reasoning,
            'confidence': confidence,
            'elapsed': round(elapsed, 2)
        }
        if board:
            log_entry['equity'] = result.get('equity', 0)
            log_entry['hand_desc'] = result.get('hand_desc', '')
            log_entry['draws'] = result.get('draws', [])
            log_entry['outs'] = result.get('outs', 0)
            log_entry['pot_odds'] = result.get('pot_odds', 0)
        
        # Memory calibration info
        if result.get('memory_error'):
            log_entry['memory_error'] = result['memory_error']
        if result.get('memory_cards'):
            log_entry['memory_cards'] = result['memory_cards']
        if result.get('memory_status'):
            log_entry['memory_status'] = result['memory_status']
        if result.get('memory_hand_id'):
            log_entry['memory_hand_id'] = result['memory_hand_id']
        if result.get('memory_players'):
            log_entry['memory_players'] = result['memory_players']
        if result.get('memory_scan_time'):
            log_entry['memory_scan_time'] = result['memory_scan_time']
        if result.get('memory_community'):
            log_entry['memory_community'] = result['memory_community']
        if result.get('memory_actions'):
            log_entry['memory_actions'] = result['memory_actions']
        if result.get('memory_container_addr'):
            log_entry['memory_container_addr'] = hex(result['memory_container_addr'])
        if result.get('memory_buf_addr'):
            log_entry['memory_buf_addr'] = hex(result['memory_buf_addr'])
        if result.get('memory_entry_count'):
            log_entry['memory_entry_count'] = result['memory_entry_count']
        
        # Preflop: log all position actions for review
        all_positions = result.get('all_positions')
        if all_positions and not board:
            log_entry['all_positions'] = {
                p: {'action': v.get('action'), 'bet_size': v.get('bet_size')}
                for p, v in all_positions.items()
            }
        
        # UI logs - what user sees
        if hasattr(self, 'ui_log_buffer') and self.ui_log_buffer:
            log_entry['ui_logs'] = self.ui_log_buffer.copy()
            self.ui_log_buffer.clear()
        
        with open(SESSION_LOG, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

        # Log result
        cards_str = ' '.join(cards) if cards else '--'
        board_str = ' '.join(board) if board else '--'
        to_call_str = f" | To call: ${to_call:.2f}" if to_call is not None else ""
        self.log(f"Cards: {cards_str} | Board: {board_str} | Pot: ${pot}{to_call_str}", "INFO")

        # Show decision if we have any useful info (pot > 0 means table detected)
        if pot > 0 or cards or board:
            # If we have all position results (preflop), show them
            all_positions = result.get('all_positions')
            if all_positions and not board:  # Preflop only
                # Line 1: Opening actions (BB shows defense threshold)
                pos_actions = []
                for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
                    pos_result = all_positions[pos]
                    action = pos_result.get('action', 'fold')
                    
                    if pos == 'BB':
                        # BB: show defense threshold instead of CHECK
                        bb_defense = pos_result.get('bb_defense', 'FOLD')
                        action_str = bb_defense
                    elif action in ('bet', 'raise'):
                        action_str = "RAISE"
                    else:
                        action_str = action.upper()
                    
                    pos_actions.append(f"{pos}:{action_str}")
                
                self.log(" | ".join(pos_actions), "DECISION")
                
                # Line 2: vs raise advice for all positions (if different)
                vs_raise_by_pos = {}
                for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
                    vs_raise_by_pos[pos] = all_positions[pos].get('call_info', 'FOLD')
                
                # Check if all positions have same advice
                unique_advice = set(vs_raise_by_pos.values())
                if len(unique_advice) == 1:
                    # All same - show single advice
                    self.log(f"vs raise: {list(unique_advice)[0]}", "INFO")
                else:
                    # Different advice - group by advice
                    advice_to_pos = {}
                    for pos, advice in vs_raise_by_pos.items():
                        if advice not in advice_to_pos:
                            advice_to_pos[advice] = []
                        advice_to_pos[advice].append(pos)
                    
                    # Format: "EP/MP: FOLD | CO/BTN: 3BET | BB: CALL 3bb"
                    parts = []
                    for advice, positions in advice_to_pos.items():
                        pos_str = '/'.join(positions)
                        parts.append(f"{pos_str}: {advice}")
                    self.log(f"vs raise: {' | '.join(parts)}", "INFO")
            else:
                # Postflop or AI-only mode - show single decision
                decision_str = f"=> {action.upper()}"
                if bet_size and action in ('bet', 'raise'):
                    decision_str += f" €{bet_size:.2f}"
                self.log(decision_str, "DECISION")
            
            if reasoning:
                self.log(reasoning, "DEBUG")
            
            # Log equity info for postflop
            if board:
                equity = result.get('equity', 0)
                outs = result.get('outs', 0)
                draws = result.get('draws', [])
                pot_odds = result.get('pot_odds', 0)
                
                info_parts = []
                if equity > 0:
                    info_parts.append(f"Win: {equity:.0f}%")
                if outs > 0:
                    info_parts.append(f"Outs: {outs}")
                if pot_odds > 0:
                    info_parts.append(f"Pot odds: {pot_odds:.0f}%")
                if draws:
                    info_parts.append(' '.join(d.replace('_', ' ') for d in draws))
                
                if info_parts:
                    self.log(" | ".join(info_parts), "INFO")
        else:
            decision_str = "No poker table detected"
            self.log(decision_str, "ERROR")

        # Update right panel
        
        # Build equity/info string for postflop
        equity_str = ""
        if board:  # Postflop
            equity = result.get('equity', 0)
            outs = result.get('outs', 0)
            draws = result.get('draws', [])
            pot_odds = result.get('pot_odds', 0)
            hand_desc = result.get('hand_desc', '')
            
            parts = []
            if equity > 0:
                parts.append(f"Win: {equity}%")
            if outs > 0:
                out_types = result.get('out_types', [])
                parts.append(f"Outs: {outs} ({', '.join(out_types)})" if out_types else f"Outs: {outs}")
            if pot_odds > 0:
                parts.append(f"Odds: {pot_odds}%")
            if draws:
                parts.append(' '.join(d.replace('_', ' ') for d in draws))
            
            equity_str = " | ".join(parts) if parts else hand_desc
        
        self._update_stats_display(result)
        
        self.time_label.config(text=f"{elapsed:.1f}s")

        # Start memory polling NOW (after stats panel is drawn)
        if self._pending_mem_poll:
            buf_addr, hand_id = self._pending_mem_poll
            self._pending_mem_poll = None
            self._start_mem_poll(buf_addr, hand_id)

    def _update_stats_display(self, result):
        """Update the right panel — advice first, data second."""
        self.stats_text.delete('1.0', 'end')

        # [MEM] status line
        mem_status = result.get('memory_status', '')
        if mem_status and mem_status != 'NO_BUFFER':
            mc = result.get('memory_cards', '')
            cards_str = f"{mc[0:2]} {mc[2:4]}" if mc and len(mc) == 4 else ''
            cc = result.get('memory_community', [])
            board_str = f" | {' '.join(cc)}" if cc else ''
            label = 'OK' if 'CONFIRMED' in mem_status else 'OVERRIDE'
            st = result.get('memory_scan_time', '')
            tag = 'MEM' if 'CONFIRMED' in mem_status else 'DANGER'
            self.stats_text.insert('end', f"[MEM] {cards_str}{board_str} ({label} {st}s)\n", tag)

        # ADVICE — the main event
        action = result.get('action', '')
        bet_size = result.get('bet_size')
        reasoning = result.get('reasoning', '')
        board = result.get('community_cards', [])
        all_positions = result.get('all_positions')

        if all_positions and not board:
            # Preflop: show position advice
            pos = result.get('position', 'BTN')
            pr = all_positions.get(pos, {})
            act = pr.get('action', 'fold').upper()
            if act in ('BET', 'RAISE'):
                bs = pr.get('bet_size')
                act_str = f"RAISE {bs:.2f}" if bs else "RAISE"
            else:
                act_str = act
            self.stats_text.insert('end', f"=> {act_str}\n", 'ACTION')
            ci = pr.get('call_info', '')
            if ci:
                self.stats_text.insert('end', f"vs raise: {ci}\n", 'DRAW')
            reason = pr.get('reasoning', '')
            if reason:
                self.stats_text.insert('end', f"{reason}\n", 'MEMDATA')
        elif action:
            # Postflop: show decision
            act = action.upper()
            if bet_size and act in ('BET', 'RAISE'):
                self.stats_text.insert('end', f"=> {act} {bet_size:.2f}\n", 'ACTION')
            else:
                self.stats_text.insert('end', f"=> {act}\n", 'ACTION')
            if reasoning:
                self.stats_text.insert('end', f"{reasoning}\n", 'DRAW')

        # Hand strength
        hand = result.get('hand_analysis', {})
        if hand and hand.get('valid'):
            self.stats_text.insert('end', self._hand_strength_str(hand) + '\n', 'HAND')
            # Draws
            draws = []
            if hand.get('has_flush_draw'):
                draws.append("NFD" if hand.get('is_nut_flush_draw') else "Flush draw")
            if hand.get('has_straight_draw'):
                draws.append("Straight draw")
            if draws:
                self.stats_text.insert('end', ' + '.join(draws) + '\n', 'DRAW')
            # Board dangers
            dangers = []
            if hand.get('board_flush_suit'): dangers.append("Flush possible")
            if hand.get('board_straight_combos'): dangers.append("Straight possible")
            if hand.get('has_board_pair'): dangers.append("Board paired")
            if dangers:
                self.stats_text.insert('end', ' | '.join(dangers) + '\n', 'DANGER')

        # Opponents
        if VISION_V2_MODE and result.get('opponent_stats'):
            self.stats_text.insert('end', '---\n', 'MEMDATA')
            unknown_count = 0
            for opp in result['opponent_stats']:
                if opp.get('hands', 0) > 0:
                    self.stats_text.insert('end',
                        f"{opp['name']} {opp['archetype'].upper()} - {opp['advice']}\n", 'OPPONENT')
                else:
                    unknown_count += 1
            if unknown_count:
                self.stats_text.insert('end', f"UNKNOWN: {unknown_count}\n", 'DANGER')

        # Memory actions at bottom
        mem_actions = result.get('memory_actions', [])
        if mem_actions:
            self.stats_text.insert('end', '---\n', 'MEMDATA')
            deal_count = 0
            for name, act, amt in mem_actions:
                if act in ('POST_SB', 'POST_BB'):
                    continue
                if act == 'DEAL' or name is None:
                    deal_count += 1
                    street = {1: 'FLOP', 2: 'TURN', 3: 'RIVER'}.get(deal_count, 'DEAL')
                    self.stats_text.insert('end', f"--- {street} ---\n", 'DRAW')
                    continue
                line = f"{name or '?'}: {act}"
                if amt > 0:
                    line += f" {amt/100:.2f}"
                tag = 'MEM' if name == 'idealistslp' else 'MEMDATA'
                self.stats_text.insert('end', line + '\n', tag)

    def on_f10(self):
        """Toggle bot mode — auto-plays hands using strategy + clicks buttons"""
        if self.bot_running:
            self.bot_running = False
            self.log("Bot stopped", "INFO")
        else:
            self.bot_running = True
            self._bot_hand_id = None  # Track current hand to detect new hands
            self.log("BOT STARTED (F11 to stop)", "INFO")
            thread = threading.Thread(target=self._bot_loop, daemon=True)
            thread.start()

    def _bot_get_window(self):
        """Find the PokerStars window and return (window, rect) or (None, None)."""
        try:
            for w in gw.getAllWindows():
                if w.title and 'PokerStars' in w.title and 'Logged In' in w.title:
                    return w, (w.left, w.top, w.width, w.height)
        except Exception:
            pass
        return None, None

    def _bot_take_screenshot(self, win):
        """Take screenshot of poker window, return PIL Image."""
        region = (win.left, win.top, win.width, win.height)
        return pyautogui.screenshot(region=region)

    def _bot_loop(self):
        """Main bot loop: detect turn via screenshot, analyze, click."""
        from bot_clicker import detect_layout, execute_action

        while self.bot_running:
            try:
                # Find poker window
                win, win_rect = self._bot_get_window()
                if not win:
                    time.sleep(1)
                    continue

                # Take screenshot to check if it's our turn
                img = self._bot_take_screenshot(win)
                layout = detect_layout(img)

                if layout is None:
                    # Not our turn — poll quickly
                    time.sleep(0.3)
                    continue

                # It's our turn — run full analysis (same as F9)
                self.log(f"[BOT] Our turn ({layout})", "INFO")
                self.on_f9()

                # Wait for analysis to complete
                while self._analyzing and self.bot_running:
                    time.sleep(0.1)

                if not self.bot_running:
                    break

                # Get the decision from last result
                result = self._last_result
                if not result:
                    time.sleep(0.5)
                    continue

                action = result.get('action', 'fold')
                bet_size = result.get('bet_size') or 0
                board = result.get('community_cards', [])
                pos = result.get('position', 'BTN')

                # Preflop: pick action for correct position
                all_pos = result.get('all_positions')
                if all_pos and not board:
                    pos_result = all_pos.get(pos, all_pos.get('BTN', {}))
                    action = pos_result.get('action', 'fold')
                    bet_size = pos_result.get('bet_size') or 0
                    self.log(f"[BOT] Preflop {pos}: {action}", "DEBUG")

                # Fresh screenshot right before clicking (layout may have changed)
                img2 = self._bot_take_screenshot(win)
                layout2 = detect_layout(img2)
                if layout2 is None:
                    self.log("[BOT] Buttons disappeared before click", "DEBUG")
                    time.sleep(0.3)
                    continue

                # Execute the click
                logger = lambda msg, lvl="DEBUG": self.root.after(0, lambda: self.log(msg, lvl))
                executed = execute_action(action, bet_size, img2, win_rect, logger)

                # Log bot execution to session JSONL
                bot_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'bot_action',
                    'hand_id': result.get('hand_id'),
                    'hero_cards': result.get('hero_cards'),
                    'board': board,
                    'position': pos,
                    'layout_before': layout,
                    'layout_at_click': layout2,
                    'strategy_action': action,
                    'bet_size': bet_size,
                    'executed': executed,
                    'memory_status': result.get('memory_status'),
                    'memory_position': result.get('position'),
                    'reasoning': result.get('reasoning', ''),
                }
                with open(SESSION_LOG, 'a') as f:
                    f.write(json.dumps(bot_entry) + '\n')

                if executed:
                    self.log(f"[BOT] Executed: {action.upper()} {f'{bet_size:.2f}' if bet_size else ''}", "DECISION")
                else:
                    self.log(f"[BOT] Could not execute {action}", "DEBUG")
                time.sleep(1.0)

            except Exception as e:
                self.log(f"[BOT] Error: {e}", "ERROR")
                time.sleep(2)

    def on_f11(self):
        """Emergency stop — immediately halts bot"""
        self.bot_running = False
        self._analyzing = False
        self._mem_polling = False
        self.log("F11: EMERGENCY STOP!", "ERROR")

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

    def _check_resize_edge(self, event):
        """Check if mouse is near edge for resize"""
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x, y = event.x, event.y
        edge = 8
        
        on_left = x < edge
        on_right = x > w - edge
        on_top = y < edge
        on_bottom = y > h - edge
        
        if on_top and on_left: return 'nw'
        if on_top and on_right: return 'ne'
        if on_bottom and on_left: return 'sw'
        if on_bottom and on_right: return 'se'
        if on_top: return 'n'
        if on_bottom: return 's'
        if on_left: return 'w'
        if on_right: return 'e'
        return None

    def _start_resize(self, event):
        """Start resize if on edge"""
        self._resize_edge = self._check_resize_edge(event)
        if self._resize_edge:
            self._resize_start_x = event.x_root
            self._resize_start_y = event.y_root
            self._resize_start_w = self.root.winfo_width()
            self._resize_start_h = self.root.winfo_height()
            self._resize_start_geo_x = self.root.winfo_x()
            self._resize_start_geo_y = self.root.winfo_y()

    def _do_resize(self, event):
        """Resize window"""
        if not self._resize_edge:
            return
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        
        x, y = self._resize_start_geo_x, self._resize_start_geo_y
        w, h = self._resize_start_w, self._resize_start_h
        
        if 'e' in self._resize_edge: w += dx
        if 's' in self._resize_edge: h += dy
        if 'w' in self._resize_edge: w -= dx; x += dx
        if 'n' in self._resize_edge: h -= dy; y += dy
        
        w, h = max(400, w), max(200, h)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _end_resize(self, event):
        """End resize"""
        self._resize_edge = None

    def _update_cursor(self, event):
        """Update cursor based on edge"""
        edge = self._check_resize_edge(event)
        cursors = {'n': 'top_side', 's': 'bottom_side', 'e': 'right_side', 'w': 'left_side',
                   'nw': 'top_left_corner', 'ne': 'top_right_corner', 
                   'sw': 'bottom_left_corner', 'se': 'bottom_right_corner'}
        self.root.config(cursor=cursors.get(edge, ''))

    def run(self):
        """Start the application"""
        # Bind resize to root window
        self.root.bind('<Motion>', self._update_cursor)
        self.root.bind('<Button-1>', self._start_resize)
        self.root.bind('<B1-Motion>', self._do_resize)
        self.root.bind('<ButtonRelease-1>', self._end_resize)
        self.root.mainloop()


def main():
    if CALIBRATE_MODE:
        print("=== MEMORY CALIBRATION MODE ===")
        print("Press F9 on each hand - dumps memory + GPT reads cards.")
        print("Run 'python memory_calibrator.py analyze' offline to verify.")
        print("Dumps saved to memory_dumps/")
        print("")
    if BOT_MODE:
        print("=== BOT MODE ===")
        print("Bot will auto-play using strategy + click buttons.")
        print("F11 = Emergency stop. F10 = Toggle bot on/off.")
        print("")
    app = HelperBar()
    if BOT_MODE:
        # Auto-start bot after UI is ready
        app.root.after(1000, app.on_f10)
    app.run()


if __name__ == '__main__':
    main()
