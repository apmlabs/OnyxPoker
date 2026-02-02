"""
Send session logs to Kiro server for analysis
Usage: python send_logs.py [log_file]
"""
import sys
import os
import requests

SERVER_URL = os.getenv('KIRO_SERVER', 'http://54.80.204.92:5001')

def send_log(path):
    print(f"Sending {path}...")
    with open(path, 'r') as f:
        content = f.read()
    
    resp = requests.post(f'{SERVER_URL}/logs', json={'filename': os.path.basename(path), 'content': content}, timeout=10)
    print(resp.json())

if __name__ == '__main__':
    if len(sys.argv) > 1:
        send_log(sys.argv[1])
    else:
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        if not os.path.isdir(log_dir):
            print("No logs folder")
            sys.exit(1)
        
        # Always send memory_scan.log if it exists
        mem_log = os.path.join(log_dir, 'memory_scan.log')
        if os.path.exists(mem_log):
            print("Sending memory_scan.log...")
            send_log(mem_log)
        
        # Send latest session log
        logs = [f for f in os.listdir(log_dir) if f.endswith('.jsonl')]
        if logs:
            latest = max(logs, key=lambda f: os.path.getmtime(os.path.join(log_dir, f)))
            print(f"Sending latest: {latest}")
            send_log(os.path.join(log_dir, latest))
        else:
            print("No session logs found")
