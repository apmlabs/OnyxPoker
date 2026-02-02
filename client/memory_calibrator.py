"""
Memory Reader - Find PokerStars card data by scanning for known card values.

Since offsets change between PS versions, we scan memory for the actual card
values that GPT detected, then remember those addresses.

Usage:
    Integrated into helper_bar.py --calibrate
    python memory_calibrator.py --test       # Test memory access
"""

import sys
import os
import json
import time
from datetime import datetime

IS_WINDOWS = sys.platform == 'win32'

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    MEM_COMMIT = 0x1000
    MEM_PRIVATE = 0x20000  # Heap allocations - where game objects live
    MEM_IMAGE = 0x1000000  # DLLs - skip
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

# Card decoding - PokerStars stores rank and suit SEPARATELY
# card_values at offset X, card_suits at offset X+4
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['c', 'd', 'h', 's']  # clubs=0, diamonds=1, hearts=2, spades=3

CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), 'memory_offsets.json')


def card_to_rank_suit(card_str):
    """Convert card like 'Ah' to (rank_byte, suit_byte) for PokerStars encoding."""
    if not card_str or len(card_str) < 2:
        return None, None
    
    rank_char = card_str[0].upper()
    suit_char = card_str[1].lower()
    
    if rank_char not in RANKS or suit_char not in SUITS:
        return None, None
    
    r = RANKS.index(rank_char)  # 0-12 (2=0, A=12)
    s = SUITS.index(suit_char)  # 0-3
    
    return r, s


class MemoryReader:
    def __init__(self):
        self.pid = None
        self.handle = None
        self.card1_addr = None  # Address of first hero card
        self.card1_encoding = None
        self.card1_gap = 1  # Gap between card1 and card2
        
    def find_pokerstars(self):
        """Find PokerStars.exe PID."""
        if not IS_WINDOWS:
            return None
        import subprocess
        try:
            out = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq PokerStars.exe" /FO CSV',
                shell=True, stderr=subprocess.DEVNULL
            )
            lines = out.decode().strip().split('\n')
            if len(lines) > 1:
                return int(lines[1].split(',')[1].strip('"'))
        except:
            pass
        return None
    
    def open_process(self, pid):
        """Open process for reading."""
        if not IS_WINDOWS:
            return None
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid
        )
        return handle if handle else None
    
    def close(self):
        """Close process handle."""
        if IS_WINDOWS and self.handle:
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None
    
    def read_bytes(self, address, size):
        """Read bytes from memory."""
        if not IS_WINDOWS or not self.handle:
            return None
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t()
        if ctypes.windll.kernel32.ReadProcessMemory(
            self.handle, ctypes.c_void_p(address), buf, size, ctypes.byref(read)
        ):
            return buf.raw[:read.value]
        return None
    
    def enumerate_regions(self, private_only=False):
        """Get all readable memory regions. If private_only, skip DLLs/mapped files."""
        if not IS_WINDOWS or not self.handle:
            return []
        regions = []
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        while ctypes.windll.kernel32.VirtualQueryEx(
            self.handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)
        ):
            base = mbi.BaseAddress
            size = mbi.RegionSize
            if size is None or size <= 0:
                break
            if mbi.State == MEM_COMMIT and (mbi.Protect & PAGE_READABLE):
                # Filter by type if requested
                if private_only and mbi.Type != MEM_PRIVATE:
                    pass  # Skip non-private (DLLs, mapped files)
                else:
                    regions.append((base, size, mbi.Type))
            if base is None:
                base = 0
            addr = base + size
            if addr <= base:
                break
        return regions
    


# Global instance
_reader = None
_last_snapshot = None  # Memory snapshot taken at screenshot time

def get_reader():
    global _reader
    if _reader is None:
        _reader = MemoryReader()
    return _reader


def scan_memory_snapshot():
    """
    Scan memory NOW and save snapshot. Called at screenshot time.
    PokerStars stores ranks at addr, suits at addr+4.
    Returns dict of {addr: (byte0, byte1, byte4, byte5)} for potential card locations.
    """
    global _last_snapshot
    reader = get_reader()
    
    if not reader.handle:
        reader.pid = reader.find_pokerstars()
        if not reader.pid:
            print("[MEM] PokerStars not found")
            return None
        reader.handle = reader.open_process(reader.pid)
        if not reader.handle:
            print("[MEM] Could not open process")
            return None
    
    # Only scan private memory (heap) - skip DLLs and mapped files
    regions = reader.enumerate_regions(private_only=True)
    total_size = sum(r[1] for r in regions)
    print(f"[MEM] {len(regions)} private regions, {total_size // 1024 // 1024}MB total")
    
    snapshot = {}
    scanned = 0
    region_count = 0
    
    for base, size, _ in regions:
        if size is None or size <= 0 or size < 6:
            continue
        if base is None:
            base = 0
        
        region_count += 1
        if region_count % 50 == 0:
            print(f"[MEM] Progress: {region_count}/{len(regions)} regions, {len(snapshot)} matches")
        
        data = reader.read_bytes(base, size)
        if not data or len(data) < 6:
            continue
        
        scanned += len(data)
        
        # Look for potential card structures: ranks 0-12 at i,i+1 and suits 0-3 at i+4,i+5
        for i in range(len(data) - 5):
            r1, r2 = data[i], data[i + 1]
            s1, s2 = data[i + 4], data[i + 5]
            
            # Both ranks must be 0-12, both suits must be 0-3
            if r1 <= 12 and r2 <= 12 and s1 <= 3 and s2 <= 3:
                snapshot[base + i] = (r1, r2, s1, s2)
    
    _last_snapshot = snapshot
    print(f"[MEM] Snapshot: {len(snapshot)} card-like structures from {scanned // 1024}KB")
    return snapshot


SAMPLES_FILE = os.path.join(os.path.dirname(__file__), 'memory_samples.json')

def calibrate_with_gpt(gpt_cards, snapshot=None):
    """
    Use snapshot to find card addresses.
    PokerStars format: ranks at addr, addr+1; suits at addr+4, addr+5
    """
    global _last_snapshot
    
    if snapshot is None:
        snapshot = _last_snapshot
    
    if not snapshot:
        return "No memory snapshot - scan failed?"
    
    if not gpt_cards or len(gpt_cards) < 2:
        return "Need 2 cards"
    
    card1, card2 = gpt_cards[0], gpt_cards[1]
    r1, s1 = card_to_rank_suit(card1)
    r2, s2 = card_to_rank_suit(card2)
    
    if r1 is None or r2 is None:
        return f"Invalid cards: {card1} {card2}"
    
    print(f"[MEM] Looking for {card1}(r={r1},s={s1}) {card2}(r={r2},s={s2})")
    print(f"[MEM] Snapshot has {len(snapshot)} potential card structures")
    
    # Load existing tracking data
    tracking = {'addrs': [], 'hands': 0}
    if os.path.exists(SAMPLES_FILE):
        try:
            with open(SAMPLES_FILE) as f:
                tracking = json.load(f)
        except:
            pass
    
    if tracking['hands'] == 0:
        # First hand: find matching structures in snapshot
        candidates = []
        for addr, (sr1, sr2, ss1, ss2) in snapshot.items():
            if sr1 == r1 and sr2 == r2 and ss1 == s1 and ss2 == s2:
                candidates.append(addr)
        
        print(f"[MEM] Hand 1: {len(candidates)} exact matches")
        
        if not candidates:
            return f"No matches for {card1} {card2}"
        
        tracking['addrs'] = candidates
        tracking['hands'] = 1
        
        with open(SAMPLES_FILE, 'w') as f:
            json.dump(tracking, f)
        
        return None
    
    else:
        # Subsequent hands: filter to addresses that now have new cards
        surviving = []
        for addr in tracking['addrs']:
            if addr in snapshot:
                sr1, sr2, ss1, ss2 = snapshot[addr]
                if sr1 == r1 and sr2 == r2 and ss1 == s1 and ss2 == s2:
                    surviving.append(addr)
        
        print(f"[MEM] Hand {tracking['hands'] + 1}: {len(surviving)} survived (was {len(tracking['addrs'])})")
        
        tracking['addrs'] = surviving
        tracking['hands'] += 1
        
        if len(surviving) == 0:
            print("[MEM] No addresses survived - starting over")
            os.remove(SAMPLES_FILE)
            return None
        
        if len(surviving) <= 3 and tracking['hands'] >= 3:
            addr = surviving[0]
            print(f"[MEM] FOUND! Address {hex(addr)}")
            
            save_calibration({
                'card_addr': addr,
                'hands_to_calibrate': tracking['hands'],
                'timestamp': datetime.now().isoformat()
            })
            os.remove(SAMPLES_FILE)
            return None
        
        with open(SAMPLES_FILE, 'w') as f:
            json.dump(tracking, f)
        
        return None


def read_cards_fast():
    """
    Read hero cards using calibrated address.
    PokerStars: ranks at addr, addr+1; suits at addr+4, addr+5
    Returns [card1, card2] or None.
    """
    reader = get_reader()
    
    # Load calibration if needed
    cal = load_calibration()
    if not cal or not cal.get('card_addr'):
        return None
    
    addr = cal['card_addr']
    
    # Open process if needed
    if not reader.handle:
        reader.pid = reader.find_pokerstars()
        if not reader.pid:
            return None
        reader.handle = reader.open_process(reader.pid)
        if not reader.handle:
            return None
    
    # Read 6 bytes: ranks at 0,1 and suits at 4,5
    data = reader.read_bytes(addr, 6)
    if not data or len(data) < 6:
        return None
    
    r1, r2 = data[0], data[1]
    s1, s2 = data[4], data[5]
    
    if r1 > 12 or r2 > 12 or s1 > 3 or s2 > 3:
        return None
    
    card1 = RANKS[r1] + SUITS[s1]
    card2 = RANKS[r2] + SUITS[s2]
    
    return [card1, card2]


def load_calibration():
    """Load saved calibration."""
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE) as f:
                return json.load(f)
        except:
            pass
    return None


def save_calibration(data):
    """Save calibration."""
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def is_calibrated():
    """Check if memory reader is calibrated."""
    cal = load_calibration()
    if not cal:
        return False
    if cal.get('card_addr'):
        return True
    return False


if __name__ == '__main__':
    if '--test' in sys.argv:
        print("Testing memory access...")
        reader = MemoryReader()
        reader.pid = reader.find_pokerstars()
        
        if not reader.pid:
            print("PokerStars not running")
            sys.exit(1)
        
        print(f"Found PokerStars PID: {reader.pid}")
        reader.handle = reader.open_process(reader.pid)
        
        if not reader.handle:
            print("Could not open process (try running as admin?)")
            sys.exit(1)
        
        all_regions = reader.enumerate_regions(private_only=False)
        private_regions = reader.enumerate_regions(private_only=True)
        all_mb = sum(r[1] for r in all_regions) / 1024 / 1024
        private_mb = sum(r[1] for r in private_regions) / 1024 / 1024
        print(f"All regions: {len(all_regions)} ({all_mb:.1f} MB)")
        print(f"Private (heap): {len(private_regions)} ({private_mb:.1f} MB)")
        print("Memory access OK!")
        
        reader.close()
    else:
        print("Memory Calibrator")
        print("")
        print("Usage:")
        print("  python memory_calibrator.py --test  # Test memory access")
        print("")
        print("Calibration: python helper_bar.py --calibrate")
        print("Press F9 with cards visible - we find them in memory.")
        print("After calibration, cards read instantly (<1ms).")
