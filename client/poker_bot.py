"""
Unified OnyxPoker Bot
Combines poker OCR with Kiro CLI decision-making
"""

import time
import pyautogui
import argparse
from typing import Dict, Any, Optional
from poker_reader import PokerScreenReader
from automation_client import OnyxPokerClient
import config

class OnyxPokerBot:
    def __init__(self, execution='analysis'):
        """
        Initialize poker bot
        
        Args:
            execution: 'auto' (click actions) or 'analysis' (display only)
        """
        self.execution = execution
        self.reader = PokerScreenReader()
        
        print(f"POKER OnyxPoker Bot initialized")
        print(f"   Execution: {execution}")
    
    def run(self, max_hands: Optional[int] = None):
        """Main bot loop"""
        hands_played = 0
        
        print("\nWAIT Waiting for your turn...")
        
        try:
            while max_hands is None or hands_played < max_hands:
                # Get game state with decision from GPT-5-mini
                state = self.reader.parse_game_state(include_decision=True)
                
                # Check if our turn
                if not self.is_hero_turn(state):
                    time.sleep(0.5)
                    continue
                
                # Display state
                print(f"\n{'='*50}")
                print(f"CARDS Hand {hands_played + 1}")
                print(f"{'='*50}")
                print(f"Cards: {state.get('hero_cards', ['??', '??'])}")
                print(f"Board: {state.get('community_cards', [])}")
                print(f"Pot: ${state.get('pot', 0)}")
                print(f"Stack: ${state.get('hero_stack', 0)}")
                print(f"To Call: ${state.get('to_call', 0)}")
                
                # Display decision
                action = state.get('recommended_action', 'fold')
                amount = state.get('recommended_amount', 0)
                reasoning = state.get('reasoning', 'No reasoning provided')
                
                print(f"\nBULB Recommended: {action.upper()}", end='')
                if amount:
                    print(f" ${amount}", end='')
                print(f"\nNOTE Reasoning: {reasoning}")
                
                # Execute or display
                if self.execution == 'auto':
                    self.execute_action(state)
                    print("SUCCESS Action executed")
                else:
                    print("INFO  [ADVICE MODE - No action taken]")
                
                hands_played += 1
                time.sleep(2)  # Wait before next check
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Bot stopped. Hands played: {hands_played}")
    
    def is_hero_turn(self, state: Dict[str, Any]) -> bool:
        """Check if it's hero's turn"""
        actions = state.get('actions', [])
        # If we have available actions, it's our turn
        return len(actions) > 0
    
    def execute_action(self, state: Dict[str, Any]):
        """Execute poker action using GPT-5-mini detected button positions"""
        action = state.get('recommended_action', 'fold')
        amount = state.get('recommended_amount', 0)
        button_positions = state.get('button_positions', {})
        
        if action == 'fold' and 'fold' in button_positions:
            x, y = button_positions['fold']
            pyautogui.click(x, y)
            
        elif action == 'call' and 'call' in button_positions:
            x, y = button_positions['call']
            pyautogui.click(x, y)
            
        elif action == 'raise' and 'raise' in button_positions:
            x, y = button_positions['raise']
            pyautogui.click(x, y)
            time.sleep(0.5)
            
            # Type amount if needed
            if amount:
                # Clear existing amount
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.2)
                # Type new amount
                pyautogui.typewrite(str(int(amount)))
                time.sleep(0.2)
                # Confirm
                pyautogui.press('enter')
        else:
            # Fallback: fold
            if 'fold' in button_positions:
                x, y = button_positions['fold']
                pyautogui.click(x, y)

def main():
    parser = argparse.ArgumentParser(description='OnyxPoker Bot')
    parser.add_argument('--execution', choices=['auto', 'analysis'], default='analysis',
                       help='Execution mode: auto (click) or analysis (display only)')
    parser.add_argument('--hands', type=int, help='Max hands to play')
    args = parser.parse_args()
    
    bot = OnyxPokerBot(execution=args.execution)
    bot.run(max_hands=args.hands)

if __name__ == '__main__':
    main()
