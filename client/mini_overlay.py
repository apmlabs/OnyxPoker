"""
OnyxPoker Mini Overlay - Always-on-top panel with essential info
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

class MiniOverlay:
    def __init__(self, parent_gui):
        self.parent = parent_gui
        self.window = tk.Toplevel()
        self.visible = True
        
        # Window properties
        self.window.geometry("400x380")
        self.window.attributes('-topmost', True)  # Always on top
        self.window.attributes('-alpha', 0.90)  # Slightly more opaque
        self.window.overrideredirect(True)  # No title bar or buttons
        
        # Prevent closing via window manager
        self.window.protocol("WM_DELETE_WINDOW", self.toggle_visibility)
        
        # Make draggable (entire window)
        self.window.bind('<Button-1>', self.start_drag)
        self.window.bind('<B1-Motion>', self.on_drag)
        
        self.create_ui()
        
    def create_ui(self):
        # Main frame with dark background
        main_frame = tk.Frame(self.window, bg='#2b2b2b', padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)
        
        # Header
        header = tk.Label(main_frame, text="🎰 OnyxPoker", 
                         font=('Arial', 14, 'bold'), 
                         bg='#2b2b2b', fg='#00ff00')
        header.pack(pady=(0, 5))
        
        tk.Frame(main_frame, height=2, bg='#555555').pack(fill='x', pady=5)
        
        # Table info
        info_frame = tk.Frame(main_frame, bg='#2b2b2b')
        info_frame.pack(fill='x', pady=5)
        
        self.pot_label = tk.Label(info_frame, text="Pot: $--", 
                                 font=('Courier', 11, 'bold'), 
                                 bg='#2b2b2b', fg='#ffff00', anchor='w')
        self.pot_label.pack(fill='x')
        
        self.cards_label = tk.Label(info_frame, text="Cards: --", 
                                    font=('Courier', 12, 'bold'), 
                                    bg='#2b2b2b', fg='#00ffff', anchor='w')
        self.cards_label.pack(fill='x')
        
        self.board_label = tk.Label(info_frame, text="Board: --", 
                                    font=('Courier', 10), 
                                    bg='#2b2b2b', fg='#ffffff', anchor='w')
        self.board_label.pack(fill='x')
        
        self.stack_label = tk.Label(info_frame, text="Stack: $--", 
                                    font=('Courier', 10), 
                                    bg='#2b2b2b', fg='#ffffff', anchor='w')
        self.stack_label.pack(fill='x')
        
        tk.Frame(main_frame, height=2, bg='#555555').pack(fill='x', pady=5)
        
        # Decision
        decision_frame = tk.Frame(main_frame, bg='#2b2b2b')
        decision_frame.pack(fill='x', pady=5)
        
        self.decision_label = tk.Label(decision_frame, text="💡 --", 
                                       font=('Arial', 16, 'bold'), 
                                       bg='#2b2b2b', fg='#00ffff', anchor='w')
        self.decision_label.pack(fill='x')
        
        self.reasoning_label = tk.Label(decision_frame, text="Waiting for action...", 
                                       font=('Arial', 9), 
                                       bg='#2b2b2b', fg='#cccccc', 
                                       anchor='w', wraplength=360, justify='left')
        self.reasoning_label.pack(fill='x')
        
        # Confidence and timestamp
        meta_frame = tk.Frame(main_frame, bg='#2b2b2b')
        meta_frame.pack(fill='x', pady=2)
        
        self.confidence_label = tk.Label(meta_frame, text="", 
                                        font=('Arial', 8), 
                                        bg='#2b2b2b', fg='#888888', anchor='w')
        self.confidence_label.pack(side='left')
        
        self.timestamp_label = tk.Label(meta_frame, text="", 
                                       font=('Arial', 8), 
                                       bg='#2b2b2b', fg='#888888', anchor='e')
        self.timestamp_label.pack(side='right')
        
        tk.Frame(main_frame, height=2, bg='#555555').pack(fill='x', pady=5)
        
        # Hotkey hints
        hints_frame = tk.Frame(main_frame, bg='#2b2b2b')
        hints_frame.pack(fill='x')
        
        self.hints1 = tk.Label(hints_frame, text="F8:Calibrate  F9:Advice  F10:Bot", 
                        font=('Arial', 8), 
                        bg='#2b2b2b', fg='#888888')
        self.hints1.pack()
        
        self.hints2 = tk.Label(hints_frame, text="F11:Stop  F12:Window", 
                        font=('Arial', 8), 
                        bg='#2b2b2b', fg='#888888')
        self.hints2.pack()
        
    def update_game_state(self, state=None, decision=None, cards=None, pot=None, stack=None, reasoning=None):
        """Update overlay with game state - unified method"""
        from datetime import datetime
        
        # If state dict provided, extract values
        if state:
            cards = state.get('hero_cards', ['??', '??'])
            pot = state.get('pot', 0)
            board = state.get('community_cards', [])
            stack = state.get('hero_stack', 0)
            if stack == 0:
                stacks = state.get('stacks', [])
                stack = stacks[2] if len(stacks) > 2 else 0
            confidence = state.get('confidence', 0.0)
        
        # Update pot
        if pot is not None:
            self.pot_label.config(text=f"Pot: ${pot}")
        
        # Update cards
        if cards:
            cards_str = ' '.join(cards) if isinstance(cards, list) else str(cards)
            self.cards_label.config(text=f"Cards: {cards_str}")
        
        # Update board
        if state and 'community_cards' in state:
            board = state['community_cards']
            if board:
                board_str = ' '.join(board)
                self.board_label.config(text=f"Board: {board_str}")
            else:
                self.board_label.config(text="Board: --")
        
        # Update stack
        if stack is not None:
            self.stack_label.config(text=f"Stack: ${stack}")
        
        # Update decision
        if decision:
            if isinstance(decision, dict):
                action = decision.get('action', '--').upper()
                amount = decision.get('amount', 0)
                if amount > 0:
                    decision_text = f"💡 {action} ${amount}"
                else:
                    decision_text = f"💡 {action}"
                self.decision_label.config(text=decision_text, fg='#00ffff')
                
                reasoning = decision.get('reasoning', 'No reasoning')
            else:
                # decision is a string like "RAISE $60"
                self.decision_label.config(text=f"💡 {decision}", fg='#00ffff')
        
        # Update reasoning
        if reasoning:
            if len(reasoning) > 150:
                reasoning = reasoning[:147] + "..."
            self.reasoning_label.config(text=reasoning)
        
        # Update confidence
        if state and 'confidence' in state:
            conf = state['confidence']
            conf_color = '#00ff00' if conf > 0.9 else '#ffff00' if conf > 0.7 else '#ff8800'
            self.confidence_label.config(text=f"Confidence: {conf:.0%}", fg=conf_color)
        
        # Update timestamp
        now = datetime.now().strftime("%H:%M:%S")
        self.timestamp_label.config(text=now)
    
    def update_status(self, status):
        """Update status message"""
        self.reasoning_label.config(text=status)
    
    def start_drag(self, event):
        self.x = event.x
        self.y = event.y
    
    def on_drag(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.window.winfo_x() + deltax
        y = self.window.winfo_y() + deltay
        self.window.geometry(f"+{x}+{y}")
    
    def set_next_step(self, step):
        """Update overlay with next step guidance"""
        if step == "calibrate":
            self.decision_label.config(text="📋 Setup Needed", fg='#ffaa00')
            self.reasoning_label.config(text="Press F8 to calibrate\n(Focus poker window first)")
            self.pot_label.config(text="Step 1: Focus poker window")
            self.cards_label.config(text="Step 2: Press F8")
            self.board_label.config(text="Step 3: Save config")
        elif step == "test":
            self.decision_label.config(text="✅ Calibrated!", fg='#00ff00')
            self.reasoning_label.config(text="Press F5 to test OCR\nOr F9 to get advice")
            self.pot_label.config(text="Calibration saved!")
            self.cards_label.config(text="Test: F5")
            self.board_label.config(text="Advice: F9")
        elif step == "ready":
            self.decision_label.config(text="✅ Ready!", fg='#00ff00')
            self.reasoning_label.config(text="F9: Get advice (one-time)\nF10: Start bot (auto mode)")
            self.pot_label.config(text="All set!")
            self.cards_label.config(text="F9: Advice")
            self.board_label.config(text="F10: Auto bot")
        elif step == "playing":
            self.decision_label.config(text="🎮 Playing", fg='#00ffff')
            self.reasoning_label.config(text="Bot is running...\nF11: Emergency stop")
            self.pot_label.config(text="Bot active")
            self.cards_label.config(text="F9: Quick advice")
            self.board_label.config(text="F11: Stop")
    
    def show(self):
        """Show the overlay"""
        self.window.deiconify()
        self.window.lift()
        self.visible = True
    
    def hide(self):
        """Hide the overlay"""
        self.window.withdraw()
        self.visible = False
    
    def toggle_visibility(self):
        """Toggle overlay visibility"""
        if self.visible:
            self.hide()
        else:
            self.show()
    
    def destroy(self):
        self.window.destroy()
