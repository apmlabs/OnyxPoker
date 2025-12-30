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
    def __init__(self, mode='remote', execution='analysis'):
        """
        Initialize poker bot
        
        Args:
            mode: 'local' (Kiro CLI subprocess) or 'remote' (HTTP to server)
            execution: 'auto' (click actions) or 'analysis' (display only)
        """
        self.mode = mode
        self.execution = execution
        self.reader = PokerScreenReader()
        
        if mode == 'remote':
            self.client = OnyxPokerClient()
            if not self.client.test_connection():
                raise ConnectionError("Cannot connect to server")
        
        print(f"🎰 OnyxPoker Bot initialized")
        print(f"   Mode: {mode}")
        print(f"   Execution: {execution}")
    
    def run(self, max_hands: Optional[int] = None):
        """Main bot loop"""
        hands_played = 0
        
        print("\n⏳ Waiting for your turn...")
        
        try:
            while max_hands is None or hands_played < max_hands:
                # Get game state with decision from GPT-4o
                state = self.reader.parse_game_state(include_decision=True)
                
                # Check if our turn
                if not self.is_hero_turn(state):
                    time.sleep(0.5)
                    continue
                
                # Display state
                print(f"\n{'='*50}")
                print(f"🃏 Hand {hands_played + 1}")
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
                
                print(f"\n💡 Recommended: {action.upper()}", end='')
                if amount:
                    print(f" ${amount}", end='')
                print(f"\n📝 Reasoning: {reasoning}")
                
                # Execute or display
                if self.execution == 'auto':
                    self.execute_action(state)
                    print("✅ Action executed")
                else:
                    print("ℹ️  [ADVICE MODE - No action taken]")
                
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
        """Execute poker action using GPT-4o detected button positions"""
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
        action = decision.get('action')
        amount = decision.get('amount', 0)
        
        if action == 'fold':
            self.click_button('fold')
        elif action == 'call':
            self.click_button('call')
        elif action == 'raise':
            self.click_button('raise')
            if amount > 0:
                time.sleep(0.3)
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.typewrite(str(amount), interval=0.05)
                pyautogui.press('enter')
    
    def click_button(self, button_name: str):
        """Click poker action button"""
        x, y, w, h = config.BUTTON_REGIONS[button_name]
        table_x, table_y, _, _ = config.TABLE_REGION
        pyautogui.click(table_x + x + w // 2, table_y + y + h // 2)

def main():
    parser = argparse.ArgumentParser(description='OnyxPoker Bot')
    parser.add_argument('--mode', choices=['local', 'remote'], default='remote',
                       help='Decision mode: local Kiro CLI or remote server')
    parser.add_argument('--execution', choices=['auto', 'analysis'], default='analysis',
                       help='Execution mode: auto (click) or analysis (display only)')
    parser.add_argument('--hands', type=int, help='Max hands to play')
    args = parser.parse_args()
    
    bot = OnyxPokerBot(mode=args.mode, execution=args.execution)
    bot.run(max_hands=args.hands)

if __name__ == '__main__':
    main()
