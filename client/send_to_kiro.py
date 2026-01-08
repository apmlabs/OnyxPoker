"""
Send screenshot to Kiro server for analysis
Usage: python send_to_kiro.py <screenshot.png>
"""
import sys
import os
import base64
import requests

SERVER_URL = os.getenv('KIRO_SERVER', 'http://57.181.105.180:5001')

def send_screenshot(path):
    with open(path, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode()
    
    resp = requests.post(f'{SERVER_URL}/analyze', json={'image': img_b64})
    print(resp.json())

if __name__ == '__main__':
    if len(sys.argv) < 2:
        # Send all screenshots in folder
        folder = 'screenshots'
        if os.path.isdir(folder):
            for f in sorted(os.listdir(folder)):
                if f.endswith('.png'):
                    print(f"\n=== {f} ===")
                    send_screenshot(os.path.join(folder, f))
        else:
            print("Usage: python send_to_kiro.py <screenshot.png>")
    else:
        send_screenshot(sys.argv[1])
