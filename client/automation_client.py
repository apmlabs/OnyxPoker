#!/usr/bin/env python3
"""
OnyxPoker Windows Automation Client
PyAutoGUI-based client that captures screenshots and executes AI-driven actions
"""

import os
import time
import base64
import json
import requests
import pyautogui
from PIL import Image
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
SERVER_URL = os.getenv('ONYXPOKER_SERVER_URL', 'http://localhost:5000')
API_KEY = os.getenv('ONYXPOKER_API_KEY', 'dev-key-change-in-production')
SCREENSHOT_DELAY = float(os.getenv('SCREENSHOT_DELAY', '1.0'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OnyxPokerClient:
    def __init__(self):
        self.server_url = SERVER_URL
        self.api_key = API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        
        # PyAutoGUI safety settings
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
        logger.info("OnyxPoker Client initialized")
    
    def capture_screenshot(self):
        """Capture screenshot and return as base64"""
        try:
            screenshot = pyautogui.screenshot()
            
            # Convert to base64
            import io
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            logger.info("Screenshot captured successfully")
            return image_data
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {str(e)}")
            return None
    
    def analyze_screenshot(self, image_data, context=""):
        """Send screenshot to AI server for analysis"""
        try:
            payload = {
                'image': image_data,
                'context': context
            }
            
            response = self.session.post(
                f"{self.server_url}/analyze",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Analysis result: {result}")
                return result
            else:
                logger.error(f"Server error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to analyze screenshot: {str(e)}")
            return None
    
    def execute_action(self, action_data):
        """Execute the action recommended by AI"""
        try:
            action = action_data.get('action')
            coordinates = action_data.get('coordinates', [])
            
            if action == 'click' and len(coordinates) >= 2:
                x, y = coordinates[0], coordinates[1]
                logger.info(f"Clicking at ({x}, {y})")
                pyautogui.click(x, y)
                return True
                
            elif action == 'type':
                text = action_data.get('text', '')
                logger.info(f"Typing: {text}")
                pyautogui.write(text)
                return True
                
            elif action == 'key':
                key = action_data.get('key', '')
                logger.info(f"Pressing key: {key}")
                pyautogui.press(key)
                return True
                
            elif action == 'wait':
                duration = action_data.get('duration', 1)
                logger.info(f"Waiting {duration} seconds")
                time.sleep(duration)
                return True
                
            else:
                logger.warning(f"Unknown action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute action: {str(e)}")
            return False
    
    def run_automation_loop(self, goal="", max_iterations=10):
        """Main automation loop"""
        logger.info(f"Starting automation loop with goal: {goal}")
        
        for iteration in range(max_iterations):
            logger.info(f"Iteration {iteration + 1}/{max_iterations}")
            
            # Capture screenshot
            image_data = self.capture_screenshot()
            if not image_data:
                logger.error("Failed to capture screenshot, stopping")
                break
            
            # Analyze with AI
            context = f"Goal: {goal}. Iteration: {iteration + 1}"
            analysis = self.analyze_screenshot(image_data, context)
            if not analysis:
                logger.error("Failed to get AI analysis, stopping")
                break
            
            # Check if goal is achieved
            if analysis.get('goal_achieved', False):
                logger.info("Goal achieved! Stopping automation.")
                break
            
            # Execute recommended action
            if 'action' in analysis:
                success = self.execute_action(analysis)
                if not success:
                    logger.warning("Action execution failed, continuing...")
            
            # Wait before next iteration
            time.sleep(SCREENSHOT_DELAY)
        
        logger.info("Automation loop completed")
    
    def test_connection(self):
        """Test connection to AI server"""
        try:
            response = self.session.get(f"{self.server_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info("Successfully connected to AI server")
                return True
            else:
                logger.error(f"Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

def main():
    """Main entry point"""
    client = OnyxPokerClient()
    
    # Test connection
    if not client.test_connection():
        logger.error("Cannot connect to AI server. Please check configuration.")
        return
    
    # Example usage
    goal = input("Enter automation goal (or press Enter for test): ").strip()
    if not goal:
        goal = "Test screenshot capture and analysis"
    
    client.run_automation_loop(goal=goal, max_iterations=5)

if __name__ == '__main__':
    main()
