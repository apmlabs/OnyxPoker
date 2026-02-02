"""
Memory Calibrator v2 - Auto-find cards using GPT-detected hand_id as anchor.

Flow:
1. GPT reads screenshot, returns hand_id + hero_cards
2. Scan memory for hand_id (unique 12-digit number)
3. Explore nearby memory for card values matching hero_cards
4. Track successful addresses across hands until stable
"""

import sys
import os
import json
import struct
from datetime import datetime

IS_WINDOWS = sys.platform == 'win32'

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    MEM_COMMIT = 0x1000
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

LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'memory_scan.log')
CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), 'memory_offsets.json')
TRACKING_FILE = os.path.join(os.path.dirname(__file__), 'memory_tracking.json')

RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['c', 'd', 'h', 's']


def log(msg):
    line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
    print(f"[MEM] {msg}")
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass


def card_to_values(card_str):
    """Convert 'Ah' to (rank=12, suit=2)."""
    if not card_str or len(card_str) < 2:
        return None, None
    r = card_str[0].upper()
    s = card_str[1].lower()
    if r not in RANKS or s not in SUITS:
        return None, None
    return RANKS.index(r), SUITS.index(s)


class MemoryScanner:
    def __init__(self):
        self.handle = None
        self.pid = None
    
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
    
    def open(self):
        if not IS_WINDOWS:
            return False
        self.pid = self.find_pokerstars()
        if not self.pid:
            return False
        self.handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, self.pid
        )
        return bool(self.handle)
    
    def read(self, addr, size):
        if not self.handle:
            return None
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t()
        if ctypes.windll.kernel32.ReadProcessMemory(
            self.handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(read)
        ):
            return buf.raw[:read.value]
        return None
    
    def scan_for_bytes(self, pattern):
        """Scan memory for byte pattern."""
        if not self.handle:
            return []
        matches = []
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        
        while ctypes.windll.kernel32.VirtualQueryEx(
            self.handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)
        ):
            if mbi.RegionSize is None or mbi.RegionSize <= 0:
                break
            if mbi.State == MEM_COMMIT and (mbi.Protect & PAGE_READABLE):
                base = mbi.BaseAddress or 0
                size = mbi.RegionSize
                if size <= 50 * 1024 * 1024:
                    data = self.read(base, size)
                    if data:
                        idx = 0
                        while True:
                            idx = data.find(pattern, idx)
                            if idx == -1:
                                break
                            matches.append(base + idx)
                            idx += 1
            addr = (mbi.BaseAddress or 0) + mbi.RegionSize
            if addr <= (mbi.BaseAddress or 0):
                break
        return matches


_scanner = None

def get_scanner():
    global _scanner
    if _scanner is None:
        _scanner = MemoryScanner()
    return _scanner


def calibrate_after_gpt(gpt_result):
    """
    Called automatically after GPT returns. Uses hand_id to find cards.
    
    gpt_result: dict with 'hand_id' and 'hero_cards'
    """
    hand_id = gpt_result.get('hand_id')
    hero_cards = gpt_result.get('hero_cards')
    
    if not hand_id or not hero_cards or len(hero_cards) < 2:
        return
    
    log(f"=== Auto-calibrate: hand_id={hand_id}, cards={hero_cards} ===")
    
    r1, s1 = card_to_values(hero_cards[0])
    r2, s2 = card_to_values(hero_cards[1])
    if r1 is None or r2 is None:
        return
    
    scanner = get_scanner()
    if not scanner.handle:
        if not scanner.open():
            log("Could not open PokerStars")
            return
        log(f"Attached to PID {scanner.pid}")
    
    # Search for hand_id in memory
    patterns = [
        ('ascii', hand_id.encode('ascii')),
        ('utf16', hand_id.encode('utf-16-le')),
    ]
    try:
        patterns.append(('int64', struct.pack('<Q', int(hand_id))))
    except:
        pass
    
    found_cards = []
    
    for enc_name, pattern in patterns:
        matches = scanner.scan_for_bytes(pattern)
        if not matches:
            continue
        log(f"hand_id as {enc_name}: {len(matches)} matches")
        
        # Check memory around each match for our cards
        for addr in matches[:20]:
            data = scanner.read(addr - 128, 512)
            if not data:
                continue
            
            # Look for [r1, r2, ?, ?, s1, s2] pattern
            for offset in range(len(data) - 6):
                if data[offset] == r1 and data[offset+1] == r2:
                    for gap in [4]:  # PokerStars uses gap of 4
                        if offset + gap + 2 > len(data):
                            continue
                        if data[offset+gap] == s1 and data[offset+gap+1] == s2:
                            real_addr = addr - 128 + offset
                            log(f"FOUND cards at {hex(real_addr)} (hand_id+{offset-128})")
                            found_cards.append({
                                'card_addr': real_addr,
                                'hand_id_addr': addr,
                                'offset_from_hand_id': offset - 128
                            })
    
    if not found_cards:
        log("No card matches found near hand_id")
        return
    
    # Track addresses across hands
    tracking = load_tracking()
    
    if tracking.get('hands', 0) == 0:
        # First hand - save all candidates
        tracking['candidates'] = [f['card_addr'] for f in found_cards]
        tracking['hands'] = 1
        log(f"Hand 1: {len(found_cards)} candidates")
    else:
        # Filter to addresses that matched again
        new_addrs = set(f['card_addr'] for f in found_cards)
        surviving = [a for a in tracking.get('candidates', []) if a in new_addrs]
        tracking['candidates'] = surviving
        tracking['hands'] += 1
        log(f"Hand {tracking['hands']}: {len(surviving)} survived")
        
        if len(surviving) == 1 and tracking['hands'] >= 2:
            # Found stable address!
            save_calibration({'card_addr': surviving[0]})
            log(f"CALIBRATED! Card address: {hex(surviving[0])}")
            tracking = {}  # Reset tracking
        elif len(surviving) == 0:
            log("No addresses survived - restarting")
            tracking = {}
    
    save_tracking(tracking)


def read_cards_fast():
    """Read cards from calibrated address. Returns ['Ah', 'Kd'] or None."""
    cal = load_calibration()
    if not cal or not cal.get('card_addr'):
        return None
    
    scanner = get_scanner()
    if not scanner.handle:
        if not scanner.open():
            return None
    
    data = scanner.read(cal['card_addr'], 6)
    if not data or len(data) < 6:
        return None
    
    r1, r2, s1, s2 = data[0], data[1], data[4], data[5]
    if r1 > 12 or r2 > 12 or s1 > 3 or s2 > 3:
        return None
    
    return [RANKS[r1] + SUITS[s1], RANKS[r2] + SUITS[s2]]


def is_calibrated():
    cal = load_calibration()
    return cal is not None and cal.get('card_addr') is not None


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


def load_tracking():
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_tracking(data):
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == '__main__':
    # Manual test
    if len(sys.argv) >= 3:
        hand_id = sys.argv[1]
        cards = sys.argv[2].split(',')
        calibrate_after_gpt({'hand_id': hand_id, 'hero_cards': cards})
    else:
        print("Usage: python memory_calibrator.py <hand_id> <card1,card2>")
        print("Example: python memory_calibrator.py 234567890123 Ah,Kd")
        print("\nOr run helper_bar.py - calibration happens automatically")
