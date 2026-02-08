"""
Send session logs + memory dumps to server for analysis
Usage: python send_logs.py [--dumps]
"""
import sys
import os
import requests

SERVER_URL = os.getenv('KIRO_SERVER', 'http://54.80.204.92:5001')
DUMP_DIR = os.path.join(os.path.dirname(__file__), 'memory_dumps')
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')


def send_log(path):
    print(f"Sending {path}...")
    with open(path, 'r') as f:
        content = f.read()
    resp = requests.post(f'{SERVER_URL}/logs', json={
        'filename': os.path.basename(path), 'content': content
    }, timeout=10)
    print(resp.json())


def send_dump(path):
    """Compress (if needed) and upload binary dump file to server."""
    import gzip
    name = os.path.basename(path)
    size_mb = os.path.getsize(path) / 1024 / 1024

    # Compress if not already gzipped
    if not path.endswith('.gz'):
        gz_path = path + '.gz'
        if not os.path.exists(gz_path):
            print(f"Compressing {name} ({size_mb:.1f} MB)...")
            with open(path, 'rb') as f_in, gzip.open(gz_path, 'wb', compresslevel=1) as f_out:
                while True:
                    chunk = f_in.read(4 * 1024 * 1024)
                    if not chunk:
                        break
                    f_out.write(chunk)
        path = gz_path
        name = os.path.basename(gz_path)
        size_mb = os.path.getsize(path) / 1024 / 1024

    print(f"Uploading {name} ({size_mb:.1f} MB)...")
    with open(path, 'rb') as f:
        resp = requests.post(f'{SERVER_URL}/upload-dump',
                             data=f,
                             headers={'X-Filename': name,
                                      'Content-Type': 'application/octet-stream'},
                             timeout=600)
    print(resp.json())


if __name__ == '__main__':
    send_dumps = '--dumps' in sys.argv

    # Send memory_scan.log if exists
    mem_log = os.path.join(LOG_DIR, 'memory_scan.log')
    if os.path.exists(mem_log):
        print("Sending memory_scan.log...")
        send_log(mem_log)

    # Send latest session log
    if os.path.isdir(LOG_DIR):
        logs = [f for f in os.listdir(LOG_DIR) if f.endswith('.jsonl')]
        if logs:
            latest = max(logs, key=lambda f: os.path.getmtime(os.path.join(LOG_DIR, f)))
            print(f"Sending latest: {latest}")
            send_log(os.path.join(LOG_DIR, latest))

    # Send memory dumps (.json metadata + .bin data)
    if send_dumps and os.path.isdir(DUMP_DIR):
        dumps = sorted(f for f in os.listdir(DUMP_DIR) if f.endswith('.json'))
        if not dumps:
            print("No memory dumps found")
        for jf in dumps:
            bf = jf.replace('.json', '.bin.gz')
            json_path = os.path.join(DUMP_DIR, jf)
            bin_path = os.path.join(DUMP_DIR, bf)
            # Fall back to uncompressed
            if not os.path.exists(bin_path):
                bf = jf.replace('.json', '.bin')
                bin_path = os.path.join(DUMP_DIR, bf)
            # Send metadata json as a log
            send_log(json_path)
            # Send binary dump
            if os.path.exists(bin_path):
                send_dump(bin_path)
            else:
                print(f"  Missing binary for {jf}, skipping")
    elif send_dumps:
        print("No memory_dumps/ folder found")
    else:
        # Show hint if dumps exist
        if os.path.isdir(DUMP_DIR) and any(f.endswith('.bin') for f in os.listdir(DUMP_DIR)):
            n = sum(1 for f in os.listdir(DUMP_DIR) if f.endswith('.bin'))
            print(f"\n{n} memory dump(s) found. Use --dumps to upload them too.")
