"""
Test raw GPT poker strategy (no custom rules) on saved screenshots
Usage: python test_raw_gpt.py [screenshot_path]
"""

import os
import sys
import json
import time
import base64
from datetime import datetime
from openai import OpenAI

MODEL = "gpt-5.2"
LOG_FILE = None

PROMPT = """Analyze this PokerStars 6-max BLITZ table screenshot. Stakes: €0.02/€0.05 No Limit Texas Hold'em.

Return JSON:
{
  "hero_cards": ["As", "Kh"],
  "community_cards": ["Qd", "Jc", "Ts"],
  "pot": 0.15,
  "hero_stack": 5.00,
  "to_call": 0.02,
  "is_hero_turn": true,
  "action": "raise",
  "bet_size": 0.10,
  "reasoning": "explanation",
  "confidence": 0.95
}

READING THE TABLE:
- hero_cards: TWO face-up cards at BOTTOM. Format: As=Ace spades, Kh=King hearts. null if no cards.
- community_cards: Cards in CENTER. Empty [] if preflop.
- pot/hero_stack/to_call: Read EXACT amounts with decimals.
- to_call: Amount on CALL button, 0 if CHECK available, null if no buttons.
- is_hero_turn: TRUE if LARGE RED buttons visible, FALSE if only checkboxes.
- action: fold/check/call/bet/raise
- bet_size: Amount in euros when betting/raising.
- reasoning: Your poker strategy reasoning.

Use your best poker strategy knowledge for 6-max micro stakes. Return ONLY JSON."""


def analyze(path):
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    with open(path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    t = time.time()
    response = client.responses.create(
        model=MODEL,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": PROMPT},
                {"type": "input_image", "image_url": f"data:image/png;base64,{image_data}"}
            ]
        }],
        max_output_tokens=500,
        reasoning={"effort": "none"},
        text={"verbosity": "low"}
    )
    api_time = time.time() - t
    
    result_text = None
    for item in response.output:
        if hasattr(item, 'content'):
            for content in item.content:
                if hasattr(content, 'text'):
                    result_text = content.text
                    break
    
    if not result_text:
        raise ValueError("No text in response")
    
    result_text = result_text.strip()
    if result_text.startswith('```'):
        result_text = result_text.split('```')[1]
        if result_text.startswith('json'):
            result_text = result_text[4:]
        result_text = result_text.strip()
    
    result = json.loads(result_text)
    result['api_time'] = api_time
    result['model'] = MODEL
    return result


def test_screenshot(path, index=None, total=None):
    global LOG_FILE
    prefix = f"[{index}/{total}] " if index else ""
    fname = os.path.basename(path)
    print(f"{prefix}{fname}", end=" ", flush=True)
    
    try:
        result = analyze(path)
        
        cards = result.get('hero_cards') or []
        turn = result.get('is_hero_turn', False)
        action = result.get('action') or 'none'
        api_time = result.get('api_time', 0)
        
        print(f"| {' '.join(cards) if cards else '--':8} | turn={str(turn):5} | {action:6} | {api_time:.1f}s")
        
        if LOG_FILE:
            result['screenshot'] = fname
            result['timestamp'] = datetime.now().isoformat()
            LOG_FILE.write(json.dumps(result) + '\n')
            LOG_FILE.flush()
        
        return result
    except Exception as e:
        err = str(e).encode('ascii', 'replace').decode('ascii')
        print(f"| ERROR: {err[:50]}")
        return None


def main():
    global LOG_FILE
    
    if len(sys.argv) > 1:
        test_screenshot(sys.argv[1])
    else:
        screenshots_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
        if not os.path.exists(screenshots_dir):
            print("No screenshots folder found")
            return
        
        files = sorted([f for f in os.listdir(screenshots_dir) if f.endswith('.png')])
        if not files:
            print("No screenshots found")
            return
        
        logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, f"raw_gpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
        LOG_FILE = open(log_path, 'w')
        
        print(f"Testing {len(files)} screenshots with RAW GPT (no strategy rules)")
        print(f"Logging to {log_path}\n")
        
        for i, f in enumerate(files, 1):
            test_screenshot(os.path.join(screenshots_dir, f), i, len(files))
        
        LOG_FILE.close()
        print(f"\nDone! Results saved to: {log_path}")

if __name__ == '__main__':
    main()
