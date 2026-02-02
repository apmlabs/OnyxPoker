"""
Memory Calibrator - Find PokerStars card addresses using GPT as oracle.

PokerStars stores cards as:
  - ranks (0-12) at offset 0x9C from seat base
  - suits (0-3) at offset 0xA0 (4 bytes after ranks)

Flow:
  1. GPT detects cards from screenshot
  2. We scan memory for those exact card values
  3. Track addresses across hands - real address has correct values each time
"""

import sys
import os
import json
from datetime import datetime

IS_WINDOWS = sys.platform == 'win32'

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    MEM_COMMIT = 0x1000
    MEM_PRIVATE = 0x20000
    PAGE_READABLE = 0x02 | 0x04 | 0x20 | 0x40 | 0x80

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

RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['c', 'd', 'h', 's']

CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), 'memory_offsets.json')
SAMPLES_FILE = os.path.join(os.path.dirname(__file__), 'memory_samples.json')
LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'memory_scan.log')


def log(msg):
    """Log to file and console."""
    line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
    print(f"[MEM] {msg}")
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass


def card_to_bytes(card_str):
    """Convert 'Ah' to (rank=12, suit=2)."""
    if not card_str or len(card_str) < 2:
        return None, None
    rank_char = card_str[0].upper()
    suit_char = card_str[1].lower()
    if rank_char not in RANKS or suit_char not in SUITS:
        return None, None
    return RANKS.index(rank_char), SUITS.index(suit_char)


class MemoryReader:
    def __init__(self):
        self.pid = None
        self.handle = None
    
    def find_pokerstars(self):
        if not IS_WINDOWS:
            return None
        import subprocess
        try:
            out = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq PokerStars.exe" /FO CSV',
                shell=True, stderr=subprocess.DEVNULL
            )
            for line in out.decode().strip().split('\n')[1:]:
                return int(line.split(',')[1].strip('"'))
        except:
            pass
        return None
    
    def open_process(self, pid):
        if not IS_WINDOWS:
            return None
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid
        )
        return handle if handle else None
    
    def read_bytes(self, address, size):
        if not IS_WINDOWS or not self.handle:
            return None
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t()
        if ctypes.windll.kernel32.ReadProcessMemory(
            self.handle, ctypes.c_void_p(address), buf, size, ctypes.byref(read)
        ):
            return buf.raw[:read.value]
        return None
    
    def get_regions(self):
        """Get private memory regions (heap)."""
        if not IS_WINDOWS or not self.handle:
            return []
        regions = []
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        while ctypes.windll.kernel32.VirtualQueryEx(
            self.handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)
        ):
            if mbi.RegionSize is None or mbi.RegionSize <= 0:
                break
            if mbi.State == MEM_COMMIT and mbi.Type == MEM_PRIVATE and (mbi.Protect & PAGE_READABLE):
                regions.append((mbi.BaseAddress or 0, mbi.RegionSize))
            addr = (mbi.BaseAddress or 0) + mbi.RegionSize
            if addr <= (mbi.BaseAddress or 0):
                break
        return regions
    
    def scan_for_cards(self, r1, s1, r2, s2):
        """
        Scan memory for specific card values.
        PokerStars format: [r1, r2, ?, ?, s1, s2] at card address.
        Returns list of matching addresses.
        """
        regions = self.get_regions()
        total_mb = sum(r[1] for r in regions) / 1024 / 1024
        log(f"Scanning {len(regions)} regions ({total_mb:.0f}MB) for r1={r1} r2={r2} s1={s1} s2={s2}")
        
        matches = []
        scanned = 0
        
        for i, (base, size) in enumerate(regions):
            if i % 100 == 0 and i > 0:
                log(f"Progress: {i}/{len(regions)} regions, {len(matches)} matches")
            
            if size > 10 * 1024 * 1024:  # Skip >10MB regions
                continue
            
            data = self.read_bytes(base, size)
            if not data or len(data) < 6:
                continue
            
            scanned += len(data)
            
            # Search for pattern: [r1, r2, ?, ?, s1, s2]
            for j in range(len(data) - 5):
                if data[j] == r1 and data[j+1] == r2 and data[j+4] == s1 and data[j+5] == s2:
                    matches.append(base + j)
        
        log(f"Done: {len(matches)} matches in {scanned // 1024}KB")
        return matches


_reader = None

def get_reader():
    global _reader
    if _reader is None:
        _reader = MemoryReader()
    return _reader


def calibrate_after_gpt(gpt_cards):
    """
    Called after GPT returns cards. Scan memory for those cards.
    Track addresses across hands until we find the stable one.
    """
    log(f"=== calibrate_after_gpt({gpt_cards}) ===")
    
    if not gpt_cards or len(gpt_cards) < 2:
        return "Need 2 cards"
    
    r1, s1 = card_to_bytes(gpt_cards[0])
    r2, s2 = card_to_bytes(gpt_cards[1])
    
    if r1 is None or r2 is None:
        return f"Invalid cards: {gpt_cards}"
    
    reader = get_reader()
    if not reader.handle:
        reader.pid = reader.find_pokerstars()
        if not reader.pid:
            return "PokerStars not found"
        reader.handle = reader.open_process(reader.pid)
        if not reader.handle:
            return "Could not open process"
    
    log(f"PID: {reader.pid}")
    
    # Load tracking data
    tracking = {'addrs': [], 'hands': 0}
    if os.path.exists(SAMPLES_FILE):
        try:
            with open(SAMPLES_FILE) as f:
                tracking = json.load(f)
        except:
            pass
    
    if tracking['hands'] == 0:
        # First hand: find all matches
        matches = reader.scan_for_cards(r1, s1, r2, s2)
        if not matches:
            return f"No matches for {gpt_cards[0]} {gpt_cards[1]}"
        
        tracking['addrs'] = matches
        tracking['hands'] = 1
        log(f"Hand 1: {len(matches)} candidates")
    else:
        # Subsequent hands: filter to addresses that still match
        matches = reader.scan_for_cards(r1, s1, r2, s2)
        match_set = set(matches)
        
        surviving = [a for a in tracking['addrs'] if a in match_set]
        log(f"Hand {tracking['hands']+1}: {len(surviving)} survived (was {len(tracking['addrs'])})")
        
        tracking['addrs'] = surviving
        tracking['hands'] += 1
        
        if len(surviving) == 0:
            log("No addresses survived - restarting")
            os.remove(SAMPLES_FILE)
            return None
        
        if len(surviving) <= 3 and tracking['hands'] >= 3:
            addr = surviving[0]
            log(f"CALIBRATED! Address: {hex(addr)}")
            save_calibration({'card_addr': addr, 'hands': tracking['hands']})
            os.remove(SAMPLES_FILE)
            return None
    
    with open(SAMPLES_FILE, 'w') as f:
        json.dump(tracking, f)
    
    return None


def read_cards_fast():
    """Read cards from calibrated address."""
    cal = load_calibration()
    if not cal or not cal.get('card_addr'):
        return None
    
    reader = get_reader()
    if not reader.handle:
        reader.pid = reader.find_pokerstars()
        if not reader.pid:
            return None
        reader.handle = reader.open_process(reader.pid)
        if not reader.handle:
            return None
    
    data = reader.read_bytes(cal['card_addr'], 6)
    if not data or len(data) < 6:
        return None
    
    r1, r2, s1, s2 = data[0], data[1], data[4], data[5]
    if r1 > 12 or r2 > 12 or s1 > 3 or s2 > 3:
        return None
    
    return [RANKS[r1] + SUITS[s1], RANKS[r2] + SUITS[s2]]


def load_calibration():
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE) as f:
                return json.load(f)
        except:
            pass
    return None


def save_calibration(data):
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def is_calibrated():
    cal = load_calibration()
    return cal is not None and cal.get('card_addr') is not None


if __name__ == '__main__':
    if '--test' in sys.argv:
        print("Testing memory access...")
        reader = MemoryReader()
        reader.pid = reader.find_pokerstars()
        if not reader.pid:
            print("PokerStars not running")
            sys.exit(1)
        print(f"PID: {reader.pid}")
        reader.handle = reader.open_process(reader.pid)
        if not reader.handle:
            print("Could not open process")
            sys.exit(1)
        regions = reader.get_regions()
        total_mb = sum(r[1] for r in regions) / 1024 / 1024
        print(f"Private regions: {len(regions)} ({total_mb:.0f}MB)")
        print("OK!")
    else:
        print("Usage: python memory_calibrator.py --test")
        print("Calibration: python helper_bar.py --calibrate")
