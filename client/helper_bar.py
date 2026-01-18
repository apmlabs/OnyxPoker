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
parser.add_argument('--visionv2', action='store_true', help='Use V2 vision with player detection')
parser.add_argument('--strategy', type=str, default='value_lord', help='Strategy to use (default: value_lord)')
args = parser.parse_args()

# Default: gpt-5.2 vision + strategy_engine (hardcoded strategy)
# --ai-only: gpt-5.2 does both vision + decision (old behavior)
# --visionv2: V2 vision with player names + opponent stats
AI_ONLY_MODE = args.ai_only
VISION_V2_MODE = args.visionv2
STRATEGY = args.strategy

if AI_ONLY_MODE:
    from vision_detector import VisionDetector, MODEL
elif VISION_V2_MODE:
    from vision_detector_v2 import VisionDetectorV2, DEFAULT_MODEL
    from strategy_engine import StrategyEngine
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

        self.log("OnyxPoker ready | F9=Advice F10=Bot F11=Stop F12=Hide", "INFO")

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
        self.log_text = scrolledtext.ScrolledText(center, font=('Courier', 10),
                                                  bg='#0d0d0d', fg='#ccc',
                                                  wrap='word', height=10)
        self.log_text.pack(fill='both', expand=True, pady=2)

        # Color tags
        self.log_text.tag_configure('INFO', foreground='#00ff00', font=('Courier', 10))
        self.log_text.tag_configure('DEBUG', foreground='#00ffff', font=('Courier', 10))
        self.log_text.tag_configure('ERROR', foreground='#ff4444', font=('Courier', 10, 'bold'))
        self.log_text.tag_configure('DECISION', foreground='#ffff00', font=('Courier', 11, 'bold'))

        # === RIGHT: Decision Stats (800px) ===
        right = tk.Frame(bottom, bg='#2d2d2d', width=800)
        right.pack(side='right', fill='y', padx=2, pady=2)
        right.pack_propagate(False)

        # Stats display (scrollable) - font reduced 40% (20pt -> 12pt)
        stats_scroll = scrolledtext.ScrolledText(right, font=('Courier', 12),
                                                bg='#1a1a1a', fg='#ccc',
                                                wrap='word', height=8)
        stats_scroll.pack(fill='both', expand=True, padx=5, pady=2)
        self.stats_text = stats_scroll

        # Color tags for stats - font reduced 40%
        self.stats_text.tag_configure('HAND', foreground='#00ff00', font=('Courier', 12, 'bold'))
        self.stats_text.tag_configure('DRAW', foreground='#00ffff', font=('Courier', 12))
        self.stats_text.tag_configure('DANGER', foreground='#ff8800', font=('Courier', 10))
        self.stats_text.tag_configure('OPPONENT', foreground='#ff66ff', font=('Courier', 12, 'bold'))
        self.stats_text.tag_configure('ADVICE', foreground='#ffcc00', font=('Courier', 11))

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

    def _load_player_stats(self):
        """Load player stats from JSON file"""
        stats_path = os.path.join(os.path.dirname(__file__), 'player_stats.json')
        if os.path.exists(stats_path):
            with open(stats_path) as f:
                return json.load(f)
        return {}

    def _classify_archetype(self, vpip, pfr, hands):
        """Classify player archetype from stats"""
        if hands < 10:
            return 'unknown'
        
        # Calculate aggression factor
        af = pfr / vpip if vpip > 0 else 0
        
        # Maniac: super loose super aggressive
        if vpip > 50 and pfr > 35:
            return 'maniac'
        # Fish: loose passive (high VPIP, low PFR relative to VPIP)
        if vpip > 40 or (vpip > 30 and af < 0.5):
            return 'fish'
        # Nit: ultra tight
        if vpip < 15:
            return 'nit'
        # LAG: loose aggressive (VPIP > 27 is key threshold)
        if vpip > 27 and af > 0.6:
            return 'lag'
        # TAG: tight aggressive (the default winning style)
        if vpip <= 27 and af > 0.5:
            return 'tag'
        # Loose passive (calls a lot, rarely raises)
        if vpip > 25 and af < 0.5:
            return 'fish'
        # Tight passive
        if vpip <= 25 and af < 0.5:
            return 'rock'
        
        return 'reg'  # Default: regular player

    def _get_archetype_advice(self, archetype, vpip, pfr):
        """Get actionable advice for archetype - when to deviate from value_lord"""
        if archetype == 'fish':
            return f"bet any pair big, never bluff"
        elif archetype == 'nit':
            return f"raise ATC in position, fold to their 3bet"
        elif archetype == 'lag':
            return f"only play top 15%, call any pair postflop"
        elif archetype == 'tag':
            return f"only play top 10% vs their opens"
        elif archetype == 'maniac':
            return f"only play pairs+AK, call down any pair"
        elif archetype == 'rock':
            return f"raise ATC in position, fold if they bet"
        elif archetype == 'reg':
            return f"play normal"
        return "no reads"

    def _lookup_opponent_stats(self, players):
        """Lookup stats for detected players"""
        stats_db = self._load_player_stats()
        opponent_stats = []
        for p in players:
            if p.get('is_hero'):
                continue
            name = p.get('name', '')
            if name in stats_db:
                s = stats_db[name]
                hands = s.get('hands', 0)
                vpip = s.get('vpip', 0)
                pfr = s.get('pfr', 0)
                archetype = self._classify_archetype(vpip, pfr, hands)
                advice = self._get_archetype_advice(archetype, vpip, pfr)
                opponent_stats.append({
                    'name': name,
                    'hands': hands,
                    'vpip': vpip,
                    'pfr': pfr,
                    'archetype': archetype,
                    'advice': advice
                })
            else:
                opponent_stats.append({
                    'name': name,
                    'hands': 0,
                    'archetype': 'unknown',
                    'advice': 'No data - play solid'
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
        """Format advice for all known opponents"""
        lines = []
        for o in opponent_stats:
            if o['hands'] > 0:
                lines.append(f"{o['name']}: {o['advice']}")
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

        self._analyzing = True
        #self.status_label.config(text="Analyzing...", fg='#ffff00')
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
                elif VISION_V2_MODE:
                    # V2 mode: vision with player detection + strategy engine
                    self.root.after(0, lambda: self.log(f"V2 API call ({DEFAULT_MODEL})...", "DEBUG"))
                    api_start = time.time()
                    vision = VisionDetectorV2(logger=lambda m, l="DEBUG": self.root.after(0, lambda: self.log(m, l)))
                    table_data = vision.detect_table(temp_path)
                    api_time = time.time() - api_start
                    
                    # Lookup opponent stats
                    opponent_stats = self._lookup_opponent_stats(table_data.get('players', []))
                    table_data['opponent_stats'] = opponent_stats
                    table_data['opponent_line'] = self._format_opponent_line(opponent_stats)
                    table_data['advice_line'] = self._format_advice_line(opponent_stats)
                    
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
                    result['api_time'] = api_time
                else:
                    # Default mode: gpt-5.2 for vision, strategy_engine for decision
                    self.root.after(0, lambda: self.log(f"API call ({DEFAULT_MODEL})...", "DEBUG"))
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
            self.root.after(0, lambda: None)  # status update removed

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
            'hero_cards': cards,
            'board': board,
            'pot': pot,
            'is_hero_turn': result.get('is_hero_turn', True),
            'action': action,
            'amount': bet_size,
            'to_call': to_call,
            'big_blind': result.get('big_blind', 0.02),
            'num_players': result.get('num_players', 2),
            'is_aggressor': result.get('is_aggressor'),
            'facing': result.get('facing'),
            'reasoning': reasoning,
            'confidence': confidence,
            'elapsed': round(elapsed, 2)
        }
        # Add postflop info if available
        if board:
            log_entry['equity'] = result.get('equity', 0)
            log_entry['hand_desc'] = result.get('hand_desc', '')
            log_entry['draws'] = result.get('draws', [])
            log_entry['outs'] = result.get('outs', 0)
            log_entry['pot_odds'] = result.get('pot_odds', 0)
        
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
        is_hero_turn = result.get('is_hero_turn', True)
        
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
        
        if True:  # Always show advice - removed unreliable is_hero_turn detection
            self._update_stats_display(result)
        
        self.time_label.config(text=f"{elapsed:.1f}s")

    def _update_stats_display(self, result):
        """Update the decision stats panel - clean, minimal display"""
        self.stats_text.delete('1.0', 'end')
        
        hand = result.get('hand_analysis', {})
        
        # Show opponent info first (V2 mode) - works on preflop too
        if VISION_V2_MODE and result.get('opponent_stats'):
            for opp in result['opponent_stats']:
                if opp.get('hands', 0) > 0:
                    short_name = opp['name'][:5]
                    line = f"{short_name} - {opp['advice']}\n"
                    self.stats_text.insert('end', line, 'HAND')
            self.stats_text.insert('end', '---\n', 'DANGER')
        
        if not hand or not hand.get('valid'):
            if not VISION_V2_MODE or not result.get('opponent_stats'):
                self.stats_text.insert('end', "No hand\n", 'HAND')
            return
        
        # 1. HAND STRENGTH (what you have)
        strength = hand.get('strength', 0)
        if strength >= 8:
            self.stats_text.insert('end', "STRAIGHT FLUSH\n", 'HAND')
        elif strength == 7:
            self.stats_text.insert('end', "QUADS\n", 'HAND')
        elif strength == 6:
            self.stats_text.insert('end', "FULL HOUSE\n", 'HAND')
        elif hand.get('has_flush'):
            nut = " (NUT)" if hand.get('is_nut_flush') else ""
            self.stats_text.insert('end', f"FLUSH{nut}\n", 'HAND')
        elif hand.get('has_straight'):
            self.stats_text.insert('end', "STRAIGHT\n", 'HAND')
        elif hand.get('has_set'):
            self.stats_text.insert('end', "SET\n", 'HAND')
        elif hand.get('has_trips'):
            self.stats_text.insert('end', "TRIPS\n", 'HAND')
        elif hand.get('has_two_pair'):
            tp = hand.get('two_pair_type', '')
            self.stats_text.insert('end', f"TWO PAIR ({tp})\n", 'HAND')
        elif hand.get('is_overpair'):
            self.stats_text.insert('end', "OVERPAIR\n", 'HAND')
        elif hand.get('has_top_pair'):
            k = "good K" if hand.get('has_good_kicker') else "weak K"
            self.stats_text.insert('end', f"TOP PAIR ({k})\n", 'HAND')
        elif hand.get('has_middle_pair'):
            self.stats_text.insert('end', "MIDDLE PAIR\n", 'HAND')
        elif hand.get('has_bottom_pair'):
            self.stats_text.insert('end', "BOTTOM PAIR\n", 'HAND')
        elif hand.get('is_pocket_pair'):
            self.stats_text.insert('end', "UNDERPAIR\n", 'HAND')
        else:
            self.stats_text.insert('end', "HIGH CARD\n", 'HAND')
        
        # 2. DRAWS (only if present)
        draws = []
        if hand.get('has_flush_draw'):
            nut = " NUT" if hand.get('is_nut_flush_draw') else ""
            draws.append(f"Flush draw{nut}")
        if hand.get('has_straight_draw'):
            draws.append("Straight draw")
        if draws:
            self.stats_text.insert('end', '\n'.join(draws) + '\n', 'DRAW')
        
        # 3. BOARD DANGERS (only if present)
        dangers = []
        if hand.get('board_flush_suit'):
            dangers.append("Flush possible")
        if hand.get('board_straight_combos'):
            dangers.append("Straight possible")
        if hand.get('has_board_pair'):
            dangers.append("Board paired")
        if dangers:
            self.stats_text.insert('end', '---\n' + '\n'.join(dangers) + '\n', 'DANGER')

    def on_f10(self):
        """Toggle bot mode"""
        if self.bot_running:
            self.bot_running = False
            #self.status_label.config(text="Stopped", fg='#ff8800')
            self.log("Bot stopped", "INFO")
        else:
            self.bot_running = True
            #self.status_label.config(text="Bot Running", fg='#00ffff')
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
        #self.status_label.config(text="STOPPED", fg='#ff4444')
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
    app = HelperBar()
    app.run()


if __name__ == '__main__':
    main()
