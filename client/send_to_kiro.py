"""
Send screenshot to Kiro server for analysis
Usage: python send_to_kiro.py <screenshot.png>
"""
import sys
import os
import base64
import requests

SERVER_URL = os.getenv('KIRO_SERVER', 'http://54.80.204.92:5001')

def send_screenshot(path):
    filename = os.path.basename(path)
    print(f"Uploading {filename}...", end=" ", flush=True)
    with open(path, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode()
    
    resp = requests.post(f'{SERVER_URL}/analyze', json={'image': img_b64, 'filename': filename}, timeout=30)
    result = resp.json()
    print(f"✓ {result}")
    return result

if __name__ == '__main__':
    if len(sys.argv) < 2:
        folder = 'screenshots'
        if os.path.isdir(folder):
            files = [f for f in sorted(os.listdir(folder)) if f.endswith('.png')]
            total = len(files)
            for i, f in enumerate(files, 1):
                print(f"\n[{i}/{total}] {f}")
                send_screenshot(os.path.join(folder, f))
            print(f"\nDone! Sent {total} screenshots.")
        else:
            print("Usage: python send_to_kiro.py <screenshot.png>")
    else:
        send_screenshot(sys.argv[1])
