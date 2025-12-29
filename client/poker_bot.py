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
                if not self.reader.is_hero_turn():
                    time.sleep(config.POLL_INTERVAL)
                    continue
                
                # Parse state
                state = self.reader.parse_game_state()
                print(f"\n{'='*50}")
                print(f"🃏 Hand {hands_played + 1}")
                print(f"{'='*50}")
                print(f"Cards: {state['hero_cards']}")
                print(f"Board: {state['community_cards']}")
                print(f"Pot: ${state['pot']}")
                print(f"Stack: ${state['stacks'][2] if len(state['stacks']) > 2 else 0}")
                print(f"Actions: {state['actions']}")
                
                # Get decision
                decision = self.get_decision(state)
                print(f"\n💡 Decision: {decision['action'].upper()}", end='')
                if decision.get('amount'):
                    print(f" ${decision['amount']}", end='')
                print(f"\n📝 Reasoning: {decision.get('reasoning', 'N/A')[:100]}...")
                
                # Execute or display
                if self.execution == 'auto':
                    self.execute_action(decision)
                    print("✅ Action executed")
                else:
                    print("ℹ️  [ANALYSIS MODE - No action taken]")
                
                hands_played += 1
                time.sleep(config.ACTION_DELAY)
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Bot stopped. Hands played: {hands_played}")
    
    def get_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get decision from Kiro CLI"""
        if self.mode == 'local':
            # Local subprocess (TODO: implement)
            import subprocess
            from poker_strategy import analyze_poker_state
            return analyze_poker_state(state)
        else:
            # Remote HTTP call
            screenshot = self.reader.capture_screenshot()
            response = self.client.session.post(
                f"{self.client.server_url}/analyze-poker",
                json={'state': state, 'image': screenshot},
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {'action': 'fold', 'amount': 0, 'reasoning': 'Server error'}
    
    def execute_action(self, decision: Dict[str, Any]):
        """Execute poker action"""
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
