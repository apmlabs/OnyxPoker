"""
Sync session logs + memory dumps to server.
No flags needed - syncs everything automatically, skips what's already there.
"""
import sys
import os
import time
import requests

SERVER_URL = os.getenv('KIRO_SERVER', 'http://54.80.204.92:5001')
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
DUMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory_dumps')


def fmt_size(b):
    if b < 1024: return f"{b} B"
    if b < 1024**2: return f"{b/1024:.1f} KB"
    if b < 1024**3: return f"{b/1024**2:.1f} MB"
    return f"{b/1024**3:.2f} GB"


def progress_upload(url, path, headers, timeout=600):
    """Upload file with progress bar."""
    total = os.path.getsize(path)
    sent = 0
    start = time.time()
    bar_width = 30

    def gen():
        nonlocal sent
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(256 * 1024)
                if not chunk:
                    break
                sent += len(chunk)
                elapsed = time.time() - start
                speed = sent / elapsed if elapsed > 0 else 0
                pct = sent / total if total > 0 else 1
                filled = int(bar_width * pct)
                bar = '#' * filled + '-' * (bar_width - filled)
                eta = (total - sent) / speed if speed > 0 else 0
                print(f"\r  [{bar}] {pct*100:5.1f}% | {fmt_size(sent)}/{fmt_size(total)} | {fmt_size(speed)}/s | ETA {eta:.0f}s", end='', flush=True)
                yield chunk

    resp = requests.post(url, data=gen(), headers=headers, timeout=timeout)
    elapsed = time.time() - start
    speed = total / elapsed if elapsed > 0 else 0
    print(f"\r  [{'#'*bar_width}] 100.0% | {fmt_size(total)} | {fmt_size(speed)}/s | {elapsed:.1f}s          ")
    return resp


def get_server_inventory():
    """Ask server what files it already has."""
    try:
        resp = requests.get(f'{SERVER_URL}/list-files', timeout=10)
        return resp.json()
    except Exception as e:
        print(f"  WARNING: Could not get server inventory ({e}), uploading everything")
        return {'logs': {}, 'dumps': {}}


def sync_logs(server_files):
    """Sync session logs (.jsonl) and memory_scan.log."""
    if not os.path.isdir(LOG_DIR):
        print(f"  Log dir not found: {LOG_DIR}")
        return 0, 0

    local_files = []
    # memory_scan.log
    mem_log = os.path.join(LOG_DIR, 'memory_scan.log')
    if os.path.exists(mem_log):
        local_files.append(('memory_scan.log', mem_log))
    # session logs
    for f in sorted(os.listdir(LOG_DIR)):
        if f.endswith('.jsonl'):
            local_files.append((f, os.path.join(LOG_DIR, f)))

    if not local_files:
        print("  No log files found")
        return 0, 0

    to_upload = []
    for name, path in local_files:
        local_size = os.path.getsize(path)
        server_size = server_files.get(name, -1)
        if server_size == local_size:
            continue  # already synced
        to_upload.append((name, path, local_size))

    skipped = len(local_files) - len(to_upload)
    if skipped:
        print(f"  {skipped} log(s) already on server, skipping")

    uploaded = 0
    for name, path, size in to_upload:
        print(f"  Uploading {name} ({fmt_size(size)})...", end=' ', flush=True)
        with open(path, 'r') as f:
            content = f.read()
        resp = requests.post(f'{SERVER_URL}/logs', json={
            'filename': name, 'content': content
        }, timeout=30)
        r = resp.json()
        print(f"OK ({r.get('lines', '?')} lines)")
        uploaded += 1

    return uploaded, skipped


def sync_dumps(server_files):
    """Sync memory dumps (.json metadata + .bin/.bin.gz binaries)."""
    if not os.path.isdir(DUMP_DIR):
        print("  No memory_dumps/ folder found")
        return 0, 0

    # Collect all dump files (json + bin + bin.gz)
    local_files = []
    for f in sorted(os.listdir(DUMP_DIR)):
        if f.endswith(('.json', '.bin', '.bin.gz')):
            local_files.append((f, os.path.join(DUMP_DIR, f)))

    if not local_files:
        print("  No dump files found")
        return 0, 0

    to_upload = []
    for name, path in local_files:
        local_size = os.path.getsize(path)
        server_size = server_files.get(name, -1)
        if server_size == local_size:
            continue
        to_upload.append((name, path, local_size))

    skipped = len(local_files) - len(to_upload)
    if skipped:
        print(f"  {skipped} dump file(s) already on server, skipping")

    # Compress uncompressed .bin files before upload
    import gzip
    final_uploads = []
    for name, path, size in to_upload:
        if name.endswith('.bin') and not name.endswith('.bin.gz'):
            gz_path = path + '.gz'
            gz_name = name + '.gz'
            # Check if gz already exists on server
            if server_files.get(gz_name, -1) >= 0:
                print(f"  {gz_name} already on server, skipping {name}")
                continue
            if not os.path.exists(gz_path):
                print(f"  Compressing {name} ({fmt_size(size)})...", end=' ', flush=True)
                start = time.time()
                with open(path, 'rb') as f_in, gzip.open(gz_path, 'wb', compresslevel=1) as f_out:
                    while True:
                        chunk = f_in.read(4 * 1024 * 1024)
                        if not chunk:
                            break
                        f_out.write(chunk)
                gz_size = os.path.getsize(gz_path)
                ratio = gz_size / size * 100 if size > 0 else 0
                print(f"{fmt_size(gz_size)} ({ratio:.0f}%) in {time.time()-start:.1f}s")
            else:
                gz_size = os.path.getsize(gz_path)
            final_uploads.append((gz_name, gz_path, gz_size))
        else:
            final_uploads.append((name, path, size))

    uploaded = 0
    for name, path, size in final_uploads:
        print(f"  Uploading {name} ({fmt_size(size)})...")
        headers = {'X-Filename': name, 'Content-Type': 'application/octet-stream'}
        if size > 1024 * 1024:  # progress bar for >1MB
            resp = progress_upload(f'{SERVER_URL}/upload-dump', path, headers)
        else:
            with open(path, 'rb') as f:
                resp = requests.post(f'{SERVER_URL}/upload-dump', data=f, headers=headers, timeout=30)
            print(f"  OK")
        r = resp.json()
        if r.get('status') != 'ok':
            print(f"  ERROR: {r}")
        uploaded += 1

    return uploaded, skipped


if __name__ == '__main__':
    print(f"=== OnyxPoker Sync ===")
    print(f"Server: {SERVER_URL}")
    print()

    # Check server
    print("[1/3] Checking server...", end=' ', flush=True)
    try:
        resp = requests.get(f'{SERVER_URL}/health', timeout=5)
        print(f"OK")
    except Exception as e:
        print(f"FAILED: {e}")
        print("Cannot reach server. Aborting.")
        sys.exit(1)

    # Get server inventory
    print("[2/3] Getting server inventory...", end=' ', flush=True)
    inv = get_server_inventory()
    server_logs = inv.get('logs', {})
    server_dumps = inv.get('dumps', {})
    print(f"{len(server_logs)} logs, {len(server_dumps)} dumps on server")
    print()

    # Sync logs
    print("--- Session Logs ---")
    log_up, log_skip = sync_logs(server_logs)
    print()

    # Sync dumps
    print("--- Memory Dumps ---")
    dump_up, dump_skip = sync_dumps(server_dumps)
    print()

    # Summary
    total_up = log_up + dump_up
    total_skip = log_skip + dump_skip
    if total_up == 0:
        print(f"Everything in sync! ({total_skip} files already on server)")
    else:
        print(f"Done! Uploaded {total_up} file(s), {total_skip} already synced.")
