"""
Kiro Analysis Server - Receives screenshots, saves them for Kiro to analyze
"""
from flask import Flask, request, jsonify
import os
import base64
import subprocess
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Store pending analysis requests
pending = {}

@app.route('/analyze', methods=['POST'])
def analyze():
    """Receive screenshot, save it, return request ID"""
    data = request.json
    if not data or 'image' not in data:
        return jsonify({'error': 'No image provided'}), 400
    
    # Use original filename if provided, else generate timestamp
    original_name = data.get('filename', '')
    if original_name and original_name.endswith('.png'):
        req_id = original_name.replace('.png', '')
    else:
        req_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    img_path = os.path.join(UPLOAD_DIR, f'{req_id}.png')
    
    img_data = base64.b64decode(data['image'])
    with open(img_path, 'wb') as f:
        f.write(img_data)
    
    pending[req_id] = {'status': 'pending', 'image': img_path, 'result': None}
    
    return jsonify({'request_id': req_id, 'status': 'pending', 'message': f'Image saved: {img_path}'})

@app.route('/result/<req_id>', methods=['GET'])
def get_result(req_id):
    """Get analysis result"""
    if req_id not in pending:
        return jsonify({'error': 'Request not found'}), 404
    return jsonify(pending[req_id])

@app.route('/result/<req_id>', methods=['POST'])
def set_result(req_id):
    """Set analysis result (called after Kiro analyzes)"""
    if req_id not in pending:
        return jsonify({'error': 'Request not found'}), 404
    
    data = request.json
    pending[req_id]['status'] = 'complete'
    pending[req_id]['result'] = data
    return jsonify({'status': 'ok'})

@app.route('/pending', methods=['GET'])
def list_pending():
    """List all pending requests"""
    return jsonify({k: v for k, v in pending.items() if v['status'] == 'pending'})

@app.route('/logs', methods=['POST'])
def receive_logs():
    """Receive session logs for analysis"""
    data = request.json
    filename = data.get('filename', 'unknown.jsonl')
    content = data.get('content', '')
    
    log_path = os.path.join(UPLOAD_DIR, filename)
    with open(log_path, 'w') as f:
        f.write(content)
    
    return jsonify({'status': 'ok', 'path': log_path, 'lines': len(content.strip().split('\n'))})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'uploads_dir': UPLOAD_DIR})

@app.route('/analyze-screenshot', methods=['POST'])
def analyze_screenshot():
    """Analyze screenshot with Kiro CLI vision"""
    import time
    timings = {}
    start_total = time.time()
    
    logger.info("=== ANALYZE-SCREENSHOT REQUEST START ===")
    try:
        data = request.json
        if not data or 'image' not in data:
            return jsonify({'error': 'No image provided'}), 400
        
        # Save screenshot temporarily
        start = time.time()
        import tempfile
        img_data = base64.b64decode(data['image'])
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(img_data)
            temp_path = f.name
        timings['image_decode_save'] = time.time() - start
        
        logger.info(f"Saved screenshot to: {temp_path}")
        
        # Build analysis prompt with image path
        start = time.time()
        prompt = f"""Look at this poker screenshot: {temp_path}

Extract the game state and give me JSON with these fields:
- hero_cards: array of 2 cards (format: "Ah", "Kd", "Tc", etc.)
- community_cards: array of board cards
- pot: number (just the number, no currency symbol)
- position: string (UTG/MP/CO/BTN/SB/BB)
- is_hero_turn: boolean"""
        timings['prompt_build'] = time.time() - start
        
        logger.info(f"Calling kiro-cli with prompt including image path")
        
        # Use full path to kiro-cli
        kiro_cli_path = '/home/ubuntu/.local/bin/kiro-cli'
        
        # Call Kiro CLI with prompt (image path is in the prompt)
        # Use poker-vision agent (built-in tools only, no MCP servers = faster)
        start = time.time()
        result = subprocess.run(
            [kiro_cli_path, 'chat', '--agent', 'poker-vision', '--trust-all-tools', prompt],
            capture_output=True,
            text=True,
            timeout=180,
            input='',  # Empty input to let it complete
            env={**os.environ, 'KIRO_NO_TIPS': '1'}  # Disable tips to reduce output
        )
        timings['kiro_cli_execution'] = time.time() - start
        
        # Clean up temp file
        start = time.time()
        os.unlink(temp_path)
        timings['cleanup'] = time.time() - start
        
        logger.info(f"Kiro CLI exit code: {result.returncode}")
        logger.info(f"Stdout length: {len(result.stdout)} chars")
        
        if result.stderr:
            logger.warning(f"Stderr: {result.stderr[:200]}")
        
        start = time.time()
        response = result.stdout.strip()
        
        # Strip ANSI color codes
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        response = ansi_escape.sub('', response)
        timings['ansi_strip'] = time.time() - start
        
        logger.info(f"Response preview (cleaned): {response[:200]}...")
        
        # Try to parse JSON response
        start = time.time()
        import json
        import re
        try:
            # First try direct parse
            parsed = json.loads(response)
            logger.info(f"Successfully parsed JSON: {list(parsed.keys())}")
            timings['json_parse'] = time.time() - start
            timings['total'] = time.time() - start_total
            
            # Add performance metrics
            parsed['_performance'] = timings
            logger.info(f"⏱️  PERFORMANCE: Total={timings['total']:.3f}s | Kiro={timings['kiro_cli_execution']:.3f}s | Decode={timings['image_decode_save']:.3f}s | Parse={timings['json_parse']:.3f}s")
            logger.info("=== ANALYZE-SCREENSHOT SUCCESS ===")
            return jsonify(parsed)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown or conversational text
            logger.info("Direct parse failed, trying to extract JSON...")
            
            # Look for JSON object in the response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(0))
                    logger.info(f"Extracted JSON: {list(parsed.keys())}")
                    timings['json_parse'] = time.time() - start
                    timings['total'] = time.time() - start_total
                    
                    # Add performance metrics
                    parsed['_performance'] = timings
                    logger.info(f"⏱️  PERFORMANCE: Total={timings['total']:.3f}s | Kiro={timings['kiro_cli_execution']:.3f}s | Decode={timings['image_decode_save']:.3f}s | Parse={timings['json_parse']:.3f}s")
                    logger.info("=== ANALYZE-SCREENSHOT SUCCESS ===")
                    return jsonify(parsed)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted JSON: {e}")
            
            logger.error(f"No valid JSON found in response")
            logger.error(f"Raw response: {response[:500]}")
            return jsonify({
                'error': 'Failed to parse response',
                'raw_response': response[:500]
            }), 500
        
    except subprocess.TimeoutExpired:
        logger.error("=== ANALYZE-SCREENSHOT TIMEOUT ===")
        return jsonify({'error': 'Kiro CLI timeout'}), 500
    except Exception as e:
        logger.error(f"=== ANALYZE-SCREENSHOT ERROR: {str(e)} ===")
        logger.exception("Full traceback:")
        return jsonify({'error': str(e)}), 500

@app.route('/validate-state', methods=['POST'])
def validate_state():
    """Validate poker state with Kiro CLI"""
    logger.info("=== VALIDATE-STATE REQUEST START ===")
    try:
        data = request.json
        state = data.get('state', {})
        
        logger.info(f"Received state: cards={state.get('hero_cards')}, board={state.get('community_cards')}, pot={state.get('pot')}, pos={state.get('position')}")
        
        # Build validation prompt
        prompt = f"""Analyze this poker game state and determine if it's valid and makes sense:

Cards: {state.get('hero_cards', [])}
Board: {state.get('community_cards', [])}
Pot: ${state.get('pot', 0)}
Position: {state.get('position', 'unknown')}

Is this a valid poker state? Are the values reasonable?
Respond with: VALID or INVALID, followed by your reasoning."""
        
        logger.info(f"Prompt length: {len(prompt)} chars")
        
        # Use full path to kiro-cli
        kiro_cli_path = '/home/ubuntu/.local/bin/kiro-cli'
        logger.info(f"Calling kiro-cli at: {kiro_cli_path}")
        
        # Call Kiro CLI
        result = subprocess.run(
            [kiro_cli_path, 'chat', prompt],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        logger.info(f"Kiro CLI exit code: {result.returncode}")
        logger.info(f"Stdout length: {len(result.stdout)} chars")
        logger.info(f"Stderr length: {len(result.stderr)} chars")
        
        if result.stderr:
            logger.warning(f"Stderr: {result.stderr[:200]}")
        
        response = result.stdout.strip()
        logger.info(f"Response preview: {response[:100]}...")
        
        # Parse response
        understood = 'VALID' in response.upper() and 'INVALID' not in response.upper()
        confidence = 0.8 if understood else 0.3
        concerns = [] if understood else ['State appears invalid or unreasonable']
        
        logger.info(f"Parsed: understood={understood}, confidence={confidence}")
        logger.info("=== VALIDATE-STATE REQUEST SUCCESS ===")
        
        return jsonify({
            'understood': understood,
            'confidence': confidence,
            'interpretation': response,
            'concerns': concerns
        })
        
    except subprocess.TimeoutExpired:
        logger.error("=== VALIDATE-STATE TIMEOUT ===")
        return jsonify({
            'understood': False,
            'confidence': 0.0,
            'interpretation': 'Kiro CLI timeout',
            'concerns': ['Validation timed out after 180 seconds']
        }), 500
    except Exception as e:
        logger.error(f"=== VALIDATE-STATE ERROR: {str(e)} ===")
        logger.exception("Full traceback:")
        return jsonify({
            'understood': False,
            'confidence': 0.0,
            'interpretation': str(e),
            'concerns': [f'Error: {str(e)}']
        }), 500

if __name__ == '__main__':
    print(f"Uploads dir: {UPLOAD_DIR}")
    app.run(host='0.0.0.0', port=5001, debug=True)
