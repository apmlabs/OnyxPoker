#!/usr/bin/env python3
"""
OnyxPoker AI Analysis Server
Flask API server that integrates with Kiro CLI for intelligent screenshot analysis
"""

import os
import base64
import tempfile
import subprocess
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app)

# Configuration
API_KEY = os.getenv('API_KEY', 'dev-key-change-in-production')
TEMP_DIR = os.getenv('TEMP_SCREENSHOT_DIR', '/tmp/onyxpoker_screenshots')
KIRO_CLI_PATH = os.getenv('KIRO_CLI_PATH', 'kiro-cli')

# Ensure temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def authenticate_request():
    """Simple API key authentication"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return False
    token = auth_header.split(' ')[1]
    return token == API_KEY

def analyze_with_kiro(image_path, context=""):
    """
    Analyze screenshot using Kiro CLI
    Returns AI decision as JSON
    """
    try:
        # Prepare the analysis prompt
        prompt = f"Analyze this screenshot and provide the next action. Context: {context}"
        
        # For now, return a mock response since we need to integrate with actual Kiro CLI
        # TODO: Implement actual Kiro CLI subprocess call
        mock_response = {
            "action": "click",
            "coordinates": [450, 300],
            "confidence": 0.85,
            "reasoning": "Detected login button at center of screen",
            "next_steps": ["Enter username", "Enter password", "Click login"]
        }
        
        logger.info(f"Analyzed screenshot: {image_path}, Context: {context}")
        return mock_response
        
    except Exception as e:
        logger.error(f"Error analyzing screenshot: {str(e)}")
        return {"error": f"Analysis failed: {str(e)}"}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })

@app.route('/analyze', methods=['POST'])
def analyze_screenshot():
    """
    Main endpoint for screenshot analysis
    Expects: {"image": "base64_data", "context": "optional_context"}
    Returns: {"action": "click", "coordinates": [x, y], "confidence": 0.85}
    """
    # Authentication
    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"error": "Missing image data"}), 400
        
        # Decode base64 image
        image_data = base64.b64decode(data['image'])
        context = data.get('context', '')
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(
            suffix='.png', 
            dir=TEMP_DIR, 
            delete=False
        ) as temp_file:
            temp_file.write(image_data)
            temp_path = temp_file.name
        
        try:
            # Analyze with Kiro CLI
            result = analyze_with_kiro(temp_path, context)
            
            # Clean up temp file
            os.unlink(temp_path)
            
            return jsonify(result)
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Get server status and statistics"""
    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    
    return jsonify({
        "server": "OnyxPoker AI Analysis Server",
        "status": "running",
        "temp_dir": TEMP_DIR,
        "kiro_cli_path": KIRO_CLI_PATH,
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/analyze-poker', methods=['POST'])
def analyze_poker():
    """Poker-specific analysis endpoint"""
    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        state = data.get('state', {})
        screenshot_data = data.get('image')
        screenshot_path = None
        
        if screenshot_data:
            image_data = base64.b64decode(screenshot_data)
            with tempfile.NamedTemporaryFile(suffix='.png', dir=TEMP_DIR, delete=False) as f:
                f.write(image_data)
                screenshot_path = f.name
        
        # Import poker strategy
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from poker_strategy import analyze_poker_state
        
        decision = analyze_poker_state(state, screenshot_path)
        
        if screenshot_path and os.path.exists(screenshot_path):
            os.unlink(screenshot_path)
        
        return jsonify(decision)
        
    except Exception as e:
        logger.error(f"Poker analysis error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/validate-state', methods=['POST'])
def validate_state():
    """Validate poker state with Kiro CLI"""
    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        state = data.get('state', {})
        
        # Build validation prompt
        prompt = f"""Analyze this poker game state and determine if it's valid and makes sense:

Cards: {state.get('hero_cards', [])}
Board: {state.get('community_cards', [])}
Pot: ${state.get('pot', 0)}
Stacks: {state.get('stacks', [])}
Actions: {state.get('actions', {})}

Is this a valid poker state? Are the values reasonable?
Respond with: VALID or INVALID, followed by your reasoning."""
        
        # Call Kiro CLI
        result = subprocess.run(
            ['kiro-cli', 'chat', prompt],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        response = result.stdout.strip()
        
        # Parse response
        understood = 'VALID' in response.upper() and 'INVALID' not in response.upper()
        confidence = 0.8 if understood else 0.3
        concerns = [] if understood else ['State appears invalid or unreasonable']
        
        return jsonify({
            'understood': understood,
            'confidence': confidence,
            'interpretation': response,
            'concerns': concerns
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'understood': False,
            'confidence': 0.0,
            'interpretation': 'Kiro CLI timeout',
            'concerns': ['Validation timed out after 180 seconds']
        }), 500
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({
            'understood': False,
            'confidence': 0.0,
            'interpretation': str(e),
            'concerns': [str(e)]
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting OnyxPoker AI Analysis Server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
