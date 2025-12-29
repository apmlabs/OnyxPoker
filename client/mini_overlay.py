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
        self.window.geometry("320x260")
        self.window.attributes('-topmost', True)  # Always on top
        self.window.attributes('-alpha', 0.85)  # More transparent
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
                         font=('Arial', 12, 'bold'), 
                         bg='#2b2b2b', fg='#00ff00')
        header.pack(pady=(0, 5))
        
        tk.Frame(main_frame, height=2, bg='#555555').pack(fill='x', pady=5)
        
        # Table info
        info_frame = tk.Frame(main_frame, bg='#2b2b2b')
        info_frame.pack(fill='x', pady=5)
        
        self.table_label = tk.Label(info_frame, text="Table: --", 
                                    font=('Courier', 9), 
                                    bg='#2b2b2b', fg='#ffffff', anchor='w')
        self.table_label.pack(fill='x')
        
        self.cards_label = tk.Label(info_frame, text="Cards: --", 
                                    font=('Courier', 10, 'bold'), 
                                    bg='#2b2b2b', fg='#ffff00', anchor='w')
        self.cards_label.pack(fill='x')
        
        self.stack_label = tk.Label(info_frame, text="Stack: --", 
                                    font=('Courier', 9), 
                                    bg='#2b2b2b', fg='#ffffff', anchor='w')
        self.stack_label.pack(fill='x')
        
        tk.Frame(main_frame, height=2, bg='#555555').pack(fill='x', pady=5)
        
        # Decision
        decision_frame = tk.Frame(main_frame, bg='#2b2b2b')
        decision_frame.pack(fill='x', pady=5)
        
        self.decision_label = tk.Label(decision_frame, text="💡 --", 
                                       font=('Arial', 14, 'bold'), 
                                       bg='#2b2b2b', fg='#00ffff', anchor='w')
        self.decision_label.pack(fill='x')
        
        self.reasoning_label = tk.Label(decision_frame, text="Waiting for action...", 
                                       font=('Arial', 8), 
                                       bg='#2b2b2b', fg='#cccccc', 
                                       anchor='w', wraplength=280, justify='left')
        self.reasoning_label.pack(fill='x')
        
        tk.Frame(main_frame, height=2, bg='#555555').pack(fill='x', pady=5)
        
        # Hotkey hints
        hints_frame = tk.Frame(main_frame, bg='#2b2b2b')
        hints_frame.pack(fill='x')
        
        self.hints1 = tk.Label(hints_frame, text="F9:Analyze  F12:Main  Ctrl+C:Calibrate", 
                        font=('Arial', 7), 
                        bg='#2b2b2b', fg='#888888')
        self.hints1.pack()
        
        self.hints2 = tk.Label(hints_frame, text="Ctrl+T:Test OCR  Ctrl+H:Toggle", 
                        font=('Arial', 7), 
                        bg='#2b2b2b', fg='#888888')
        self.hints2.pack()
        
    def update_info(self, state, decision=None):
        """Update overlay with current game state"""
        # Table info
        pot = state.get('pot', 0)
        self.table_label.config(text=f"Table: ${pot} pot")
        
        # Cards
        cards = state.get('hero_cards', ['??', '??'])
        cards_str = ' '.join(cards)
        self.cards_label.config(text=f"Cards: {cards_str}")
        
        # Stack
        stacks = state.get('stacks', [])
        stack = stacks[2] if len(stacks) > 2 else 0
        self.stack_label.config(text=f"Stack: ${stack}")
        
        # Decision
        if decision:
            action = decision.get('action', '--').upper()
            amount = decision.get('amount', 0)
            
            if amount > 0:
                action_text = f"💡 {action} ${amount}"
            else:
                action_text = f"💡 {action}"
            
            self.decision_label.config(text=action_text)
            
            # Reasoning (first 100 chars)
            reasoning = decision.get('reasoning', 'No reasoning')
            if len(reasoning) > 100:
                reasoning = reasoning[:97] + "..."
            self.reasoning_label.config(text=reasoning)
        else:
            self.decision_label.config(text="💡 --")
            self.reasoning_label.config(text="Waiting for action...")
    
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
            self.reasoning_label.config(text="Press Ctrl+C to calibrate\nOr F12 to open main window")
            self.table_label.config(text="Step 1: Scan Windows")
            self.cards_label.config(text="Step 2: Select poker window")
            self.stack_label.config(text="Step 3: Press F12, then Ctrl+T")
        elif step == "scan_done":
            self.decision_label.config(text="📸 Capture Table", fg='#00aaff')
            self.reasoning_label.config(text="Press F12 to hide this window\nThen press Ctrl+T to capture")
            self.table_label.config(text="✓ Window selected")
            self.cards_label.config(text="Next: F12 (hide)")
            self.stack_label.config(text="Then: Ctrl+T (capture)")
        elif step == "test":
            self.decision_label.config(text="📸 Test OCR", fg='#00aaff')
            self.reasoning_label.config(text="Press Ctrl+T to test OCR\nOr F9 to capture & analyze")
            self.table_label.config(text="Calibration saved!")
            self.cards_label.config(text="Test: Ctrl+T")
            self.stack_label.config(text="Or: F9 to analyze")
        elif step == "ready":
            self.decision_label.config(text="✅ Ready!", fg='#00ff00')
            self.reasoning_label.config(text="Press F9 to get AI advice\nBot is ready to help!")
            self.table_label.config(text="All set!")
            self.cards_label.config(text="F9: Get advice")
            self.stack_label.config(text="F10: Start bot")
        elif step == "playing":
            self.decision_label.config(text="🎮 Playing", fg='#00ffff')
            self.reasoning_label.config(text="Waiting for your turn...\nPress F9 for advice anytime")
            self.table_label.config(text="Bot active")
            self.cards_label.config(text="F9: Analyze")
            self.stack_label.config(text="F11: Emergency stop")
    
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
