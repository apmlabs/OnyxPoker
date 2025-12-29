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
        self.window.title("OnyxPoker Mini")
        
        # Window properties
        self.window.geometry("320x240")
        self.window.attributes('-topmost', True)  # Always on top
        self.window.attributes('-alpha', 0.95)  # Slightly transparent
        self.window.overrideredirect(False)  # Keep title bar for dragging
        
        # Make draggable
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
        
        hints = tk.Label(hints_frame, text="[F9] Analyze  [F10] Start/Stop  [F12] Main", 
                        font=('Arial', 8), 
                        bg='#2b2b2b', fg='#888888')
        hints.pack()
        
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
    
    def show(self):
        self.window.deiconify()
        self.window.lift()
    
    def hide(self):
        self.window.withdraw()
    
    def destroy(self):
        self.window.destroy()
