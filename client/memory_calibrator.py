"""
Memory Calibrator - Auto-find PokerStars memory offsets using GPT vision as oracle.

Workflow:
1. Screenshot + scan memory for card-like values (same instant)
2. Save candidate addresses with their values
3. Send screenshot to GPT-5.2 for card detection
4. Correlate: filter addresses that had the correct card values
5. Repeat across hands until stable offsets found

Usage:
    python memory_calibrator.py --test       # Test memory reading
    python memory_calibrator.py --status     # Show calibration progress
"""

import sys
import os
import json
import time
from datetime import datetime

# Check for Windows
IS_WINDOWS = sys.platform == 'win32'

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    
    # Windows API constants
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    MEM_COMMIT = 0x1000
    PAGE_READABLE = (0x02 | 0x04 | 0x20 | 0x40 | 0x80)  # PAGE_READONLY | PAGE_READWRITE | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY
    
    # MEMORY_BASIC_INFORMATION structure
    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]

# Logging setup
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Calibration data file
CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), 'memory_calibration.json')

# Card encodings
SUIT_MAP = {'c': 0, 'd': 1, 'h': 2, 's': 3}
RANK_MAP = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}


class MemoryCalibrator:
    def __init__(self):
        self.log_file = os.path.join(LOG_DIR, f"memory_cal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
        self.pid = None
        self.handle = None
        
    def log(self, event, data=None):
        """Log event to JSONL file."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'event': event,
            'data': data or {}
        }
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        print(f"[{event}] {data if data else ''}")
    
    def get_pokerstars_pid(self):
        """Find PokerStars.exe process ID."""
        if not IS_WINDOWS:
            self.log('error', {'msg': 'Memory reading only works on Windows'})
            return None
            
        import subprocess
        try:
            t0 = time.time()
            output = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq PokerStars.exe" /FO CSV',
                shell=True, stderr=subprocess.DEVNULL
            )
            lines = output.decode().strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split(',')
                pid = int(parts[1].strip('"'))
                self.log('pid_found', {'pid': pid, 'duration_ms': int((time.time()-t0)*1000)})
                return pid
            self.log('error', {'msg': 'PokerStars.exe not found in process list'})
        except Exception as e:
            self.log('error', {'msg': f'Failed to find PokerStars.exe: {e}'})
        return None
    
    def open_process(self, pid):
        """Open process handle for memory reading."""
        if not IS_WINDOWS:
            return None
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if not handle:
            error = kernel32.GetLastError()
            self.log('error', {'msg': f'Failed to open process {pid}', 'error_code': error})
            return None
        self.log('process_opened', {'pid': pid, 'handle': handle})
        return handle
    
    def close_process(self, handle):
        """Close process handle."""
        if IS_WINDOWS and handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            self.log('process_closed', {'handle': handle})
    
    def enumerate_memory_regions(self, handle):
        """Use VirtualQueryEx to find all readable memory regions."""
        if not IS_WINDOWS:
            return []
        
        kernel32 = ctypes.windll.kernel32
        regions = []
        address = 0
        mbi = MEMORY_BASIC_INFORMATION()
        mbi_size = ctypes.sizeof(mbi)
        
        t0 = time.time()
        total_size = 0
        
        while True:
            result = kernel32.VirtualQueryEx(
                handle,
                ctypes.c_void_p(address),
                ctypes.byref(mbi),
                mbi_size
            )
            if not result:
                break
                
            # Only include committed, readable memory
            if mbi.State == MEM_COMMIT and (mbi.Protect & PAGE_READABLE):
                regions.append({
                    'base': mbi.BaseAddress,
                    'size': mbi.RegionSize,
                    'protect': mbi.Protect
                })
                total_size += mbi.RegionSize
            
            # Move to next region
            address = mbi.BaseAddress + mbi.RegionSize
            if address <= mbi.BaseAddress:  # Overflow check
                break
        
        duration = time.time() - t0
        self.log('regions_enumerated', {
            'count': len(regions),
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'duration_ms': int(duration * 1000)
        })
        return regions
    
    def read_memory(self, handle, address, size):
        """Read memory from process."""
        if not IS_WINDOWS:
            return None
        kernel32 = ctypes.windll.kernel32
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t()
        
        result = kernel32.ReadProcessMemory(
            handle,
            ctypes.c_void_p(address),
            buffer,
            size,
            ctypes.byref(bytes_read)
        )
        
        if result and bytes_read.value > 0:
            return buffer.raw[:bytes_read.value]
        return None
    
    def scan_region_for_cards(self, handle, base, size):
        """Scan a memory region for card-like values."""
        candidates = {}
        
        # Read in chunks to avoid huge allocations
        chunk_size = min(size, 65536)  # 64KB chunks
        
        for offset in range(0, size, chunk_size):
            read_size = min(chunk_size, size - offset)
            data = self.read_memory(handle, base + offset, read_size)
            if not data:
                continue
            
            for i, byte in enumerate(data):
                addr = base + offset + i
                # Card-like values: 0-51 (combined), 0-13 (rank), 0-3 (suit), 2-14 (rank alt)
                if byte <= 51:
                    candidates[addr] = byte
        
        return candidates
    
    def scan_all_regions(self, handle, regions):
        """Scan all memory regions for card-like values."""
        t0 = time.time()
        all_candidates = {}
        regions_scanned = 0
        bytes_scanned = 0
        
        for region in regions:
            base = region['base']
            size = region['size']
            
            # Skip very large regions (>10MB) - unlikely to contain card data
            if size > 10 * 1024 * 1024:
                continue
                
            candidates = self.scan_region_for_cards(handle, base, size)
            all_candidates.update(candidates)
            regions_scanned += 1
            bytes_scanned += size
        
        duration = time.time() - t0
        self.log('scan_complete', {
            'regions_scanned': regions_scanned,
            'bytes_scanned_mb': round(bytes_scanned / 1024 / 1024, 2),
            'candidates_found': len(all_candidates),
            'duration_ms': int(duration * 1000)
        })
        return all_candidates
    
    def parse_card(self, card_str):
        """Parse card string like 'Ah' into multiple encodings."""
        if not card_str or len(card_str) < 2:
            return None
        
        rank_char = card_str[0].upper()
        suit_char = card_str[1].lower()
        
        if rank_char not in RANK_MAP or suit_char not in SUIT_MAP:
            return None
        
        rank = RANK_MAP[rank_char]
        suit = SUIT_MAP[suit_char]
        
        return {
            'rank_2_14': rank,           # 2-14
            'rank_0_12': rank - 2,       # 0-12
            'suit_0_3': suit,            # 0-3
            'combined_r4s': (rank - 2) * 4 + suit,  # 0-51 (rank*4+suit)
            'combined_s13r': suit * 13 + (rank - 2), # 0-51 (suit*13+rank)
        }
    
    def correlate(self, candidates, gpt_cards):
        """Find addresses that match GPT-detected cards."""
        matches = []
        
        for card_str in gpt_cards:
            encodings = self.parse_card(card_str)
            if not encodings:
                continue
            
            for addr, value in candidates.items():
                for enc_name, enc_value in encodings.items():
                    if value == enc_value:
                        matches.append({
                            'address': hex(addr),
                            'address_int': addr,
                            'value': value,
                            'card': card_str,
                            'encoding': enc_name
                        })
        
        self.log('correlation_complete', {
            'gpt_cards': gpt_cards,
            'matches_found': len(matches)
        })
        return matches
    
    def snapshot(self):
        """Take a memory snapshot. Returns candidates dict."""
        t0 = time.time()
        
        self.pid = self.get_pokerstars_pid()
        if not self.pid:
            return None
        
        self.handle = self.open_process(self.pid)
        if not self.handle:
            return None
        
        try:
            regions = self.enumerate_memory_regions(self.handle)
            if not regions:
                self.log('error', {'msg': 'No readable memory regions found'})
                return None
            
            candidates = self.scan_all_regions(self.handle, regions)
            
            total_duration = time.time() - t0
            self.log('snapshot_complete', {
                'total_duration_ms': int(total_duration * 1000),
                'candidates': len(candidates)
            })
            return candidates
            
        finally:
            self.close_process(self.handle)
            self.handle = None


# Global instance for use by helper_bar.py
_calibrator = None

def get_calibrator():
    global _calibrator
    if _calibrator is None:
        _calibrator = MemoryCalibrator()
    return _calibrator


def memory_snapshot():
    """Take a memory snapshot. Called by helper_bar.py."""
    return get_calibrator().snapshot()


def calibration_step(screenshot_path, gpt_cards, candidates):
    """Correlate memory snapshot with GPT cards. Called by helper_bar.py."""
    cal = get_calibrator()
    matches = cal.correlate(candidates, gpt_cards)
    
    # Save to calibration file
    data = load_calibration()
    data['hands'].append({
        'timestamp': datetime.now().isoformat(),
        'screenshot': screenshot_path,
        'gpt_cards': gpt_cards,
        'num_candidates': len(candidates),
        'matches': matches
    })
    
    # Check for stable offsets
    stable = analyze_calibration_data(data)
    if stable:
        data['stable_offsets'] = stable
        cal.log('stable_offsets_found', {'offsets': stable})
    
    save_calibration(data)
    return matches, stable


def load_calibration():
    """Load calibration data."""
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE, 'r') as f:
            return json.load(f)
    return {'hands': [], 'stable_offsets': None}


def save_calibration(data):
    """Save calibration data."""
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def analyze_calibration_data(data):
    """Find addresses that appear in >80% of hands."""
    if len(data['hands']) < 5:
        return None
    
    address_counts = {}
    for hand in data['hands']:
        for match in hand.get('matches', []):
            key = (match['address'], match['encoding'])
            address_counts[key] = address_counts.get(key, 0) + 1
    
    threshold = len(data['hands']) * 0.8
    stable = []
    for (addr, encoding), count in address_counts.items():
        if count >= threshold:
            stable.append({
                'address': addr,
                'encoding': encoding,
                'hit_rate': round(count / len(data['hands']), 2)
            })
    
    return stable if stable else None


def show_status():
    """Show calibration status."""
    data = load_calibration()
    print(f"\n=== Memory Calibration Status ===")
    print(f"Hands collected: {len(data['hands'])}")
    print(f"Log file: {get_calibrator().log_file}")
    
    if data['stable_offsets']:
        print(f"\nStable offsets found:")
        for off in data['stable_offsets']:
            print(f"  {off['address']} ({off['encoding']}) - {off['hit_rate']*100:.0f}%")
    elif data['hands']:
        # Show top candidates
        address_counts = {}
        for hand in data['hands']:
            for match in hand.get('matches', []):
                key = (match['address'], match['encoding'])
                address_counts[key] = address_counts.get(key, 0) + 1
        
        if address_counts:
            print(f"\nTop candidates:")
            sorted_addrs = sorted(address_counts.items(), key=lambda x: -x[1])[:10]
            for (addr, enc), count in sorted_addrs:
                print(f"  {addr} ({enc}) - {count}/{len(data['hands'])} hands")
    else:
        print("\nNo data yet. Run: python helper_bar.py --calibrate")


if __name__ == '__main__':
    if '--status' in sys.argv:
        show_status()
    elif '--test' in sys.argv:
        print("Testing memory reading...")
        cal = MemoryCalibrator()
        candidates = cal.snapshot()
        if candidates:
            print(f"\nSUCCESS: Found {len(candidates)} card-like values")
            print(f"Log file: {cal.log_file}")
        else:
            print("\nFAILED: Could not read memory")
            print(f"Check log: {cal.log_file}")
    else:
        print("Memory Calibrator")
        print("")
        print("Usage:")
        print("  python memory_calibrator.py --test    # Test memory reading")
        print("  python memory_calibrator.py --status  # Show calibration progress")
        print("")
        print("Or run: python helper_bar.py --calibrate")
