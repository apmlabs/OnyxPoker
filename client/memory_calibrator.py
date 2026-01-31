"""
Memory Reader - Read PokerStars data using known offsets from poker-supernova.

Offsets are relative to base pointers. We find the base pointer once per session
by searching for the known offset pattern, then read data instantly.

Usage:
    Integrated into helper_bar.py --calibrate
    python memory_calibrator.py --test       # Test if offsets work
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

# Known offsets from poker-supernova (PokerStars 7 Build 46014)
# These are RELATIVE offsets from base pointers
OFFSETS = {
    'table': {
        'card_values': 0x64,   # 5 bytes, one per community card
        'card_suits': 0x68,    # 5 bytes
        'pot': 0x18,
        'hand_id': 0x40,
        'num_cards': 0x58,
    },
    'seat': {
        'name': 0x00,          # String
        'stack': 0x58,         # Float/int
        'bet': 0x68,
        'card_values': 0x9C,   # 2 bytes for hole cards
        'card_suits': 0xA0,    # 2 bytes
    }
}

# Card decoding
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['c', 'd', 'h', 's']

CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), 'memory_offsets.json')


class MemoryReader:
    def __init__(self):
        self.pid = None
        self.handle = None
        self.table_base = None  # Found during calibration
        self.seat_base = None   # Hero's seat base
        
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
    
    def read_int(self, address):
        """Read 4-byte int."""
        data = self.read_bytes(address, 4)
        return int.from_bytes(data, 'little') if data else None
    
    def read_float(self, address):
        """Read 4-byte float."""
        import struct
        data = self.read_bytes(address, 4)
        return struct.unpack('<f', data)[0] if data else None
    
    def read_string(self, address, max_len=32):
        """Read null-terminated string."""
        data = self.read_bytes(address, max_len)
        if data:
            null = data.find(b'\x00')
            return data[:null].decode('utf-8', errors='ignore') if null > 0 else None
        return None
    
    def decode_card(self, rank_byte, suit_byte):
        """Decode card from rank/suit bytes."""
        if rank_byte is None or suit_byte is None:
            return None
        if 0 <= rank_byte <= 12 and 0 <= suit_byte <= 3:
            return RANKS[rank_byte] + SUITS[suit_byte]
        return None
    
    def enumerate_regions(self):
        """Get all readable memory regions."""
        if not IS_WINDOWS:
            return []
        regions = []
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        while ctypes.windll.kernel32.VirtualQueryEx(
            self.handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)
        ):
            if mbi.State == MEM_COMMIT and (mbi.Protect & PAGE_READABLE):
                regions.append((mbi.BaseAddress, mbi.RegionSize))
            addr = mbi.BaseAddress + mbi.RegionSize
            if addr <= mbi.BaseAddress:
                break
        return regions
    
    def find_base_pointers(self, hero_cards):
        """
        Find base pointers by searching for hero's cards at known offset.
        hero_cards: list like ['Ah', 'Kd']
        """
        if not hero_cards or len(hero_cards) < 2:
            return False
        
        # Parse expected card values
        c1, c2 = hero_cards[0], hero_cards[1]
        r1 = RANKS.index(c1[0].upper()) if c1[0].upper() in RANKS else None
        s1 = SUITS.index(c1[1].lower()) if c1[1].lower() in SUITS else None
        r2 = RANKS.index(c2[0].upper()) if c2[0].upper() in RANKS else None
        s2 = SUITS.index(c2[1].lower()) if c2[1].lower() in SUITS else None
        
        if None in [r1, s1, r2, s2]:
            return False
        
        # Search memory for this pattern at seat offset
        card_offset = OFFSETS['seat']['card_values']  # 0x9C
        suit_offset = OFFSETS['seat']['card_suits']   # 0xA0
        
        regions = self.enumerate_regions()
        for base, size in regions:
            if size > 10 * 1024 * 1024:  # Skip >10MB regions
                continue
            
            # Read region in chunks
            chunk = 65536
            for off in range(0, size - 0xA4, chunk):
                data = self.read_bytes(base + off, min(chunk + 0xA4, size - off))
                if not data:
                    continue
                
                # Search for card pattern
                for i in range(len(data) - 0xA4):
                    # Check if cards match at expected offsets
                    if (data[i + card_offset] == r1 and 
                        data[i + card_offset + 1] == r2 and
                        data[i + suit_offset] == s1 and 
                        data[i + suit_offset + 1] == s2):
                        
                        self.seat_base = base + off + i
                        print(f"Found seat base: {hex(self.seat_base)}")
                        return True
        
        return False
    
    def read_hero_cards(self):
        """Read hero's hole cards using calibrated offset."""
        if not self.seat_base:
            return None
        
        r1 = self.read_bytes(self.seat_base + OFFSETS['seat']['card_values'], 1)
        r2 = self.read_bytes(self.seat_base + OFFSETS['seat']['card_values'] + 1, 1)
        s1 = self.read_bytes(self.seat_base + OFFSETS['seat']['card_suits'], 1)
        s2 = self.read_bytes(self.seat_base + OFFSETS['seat']['card_suits'] + 1, 1)
        
        if all([r1, r2, s1, s2]):
            c1 = self.decode_card(r1[0], s1[0])
            c2 = self.decode_card(r2[0], s2[0])
            if c1 and c2:
                return [c1, c2]
        return None
    
    def read_hero_stack(self):
        """Read hero's stack."""
        if not self.seat_base:
            return None
        return self.read_float(self.seat_base + OFFSETS['seat']['stack'])
    
    def read_hero_name(self):
        """Read hero's name."""
        if not self.seat_base:
            return None
        return self.read_string(self.seat_base + OFFSETS['seat']['name'])


# Global instance
_reader = None

def get_reader():
    global _reader
    if _reader is None:
        _reader = MemoryReader()
    return _reader


def calibrate_with_gpt(gpt_cards):
    """
    Calibrate memory reader using GPT-detected cards.
    Called by helper_bar.py after GPT returns cards.
    Returns True if calibration successful.
    """
    reader = get_reader()
    
    # Open process if needed
    if not reader.handle:
        reader.pid = reader.find_pokerstars()
        if not reader.pid:
            print("PokerStars not found")
            return False
        reader.handle = reader.open_process(reader.pid)
        if not reader.handle:
            print("Could not open PokerStars process")
            return False
    
    # Find base pointer using GPT cards
    if reader.find_base_pointers(gpt_cards):
        # Save calibration
        save_calibration({'seat_base': reader.seat_base})
        return True
    
    return False


def read_cards_fast():
    """
    Read hero cards instantly using calibrated offsets.
    Returns cards list or None if not calibrated.
    """
    reader = get_reader()
    
    # Load calibration if needed
    if not reader.seat_base:
        cal = load_calibration()
        if cal and cal.get('seat_base'):
            reader.seat_base = cal['seat_base']
            # Reopen process
            reader.pid = reader.find_pokerstars()
            if reader.pid:
                reader.handle = reader.open_process(reader.pid)
    
    if not reader.seat_base or not reader.handle:
        return None
    
    return reader.read_hero_cards()


def load_calibration():
    """Load saved calibration."""
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE) as f:
            return json.load(f)
    return None


def save_calibration(data):
    """Save calibration."""
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f)


def is_calibrated():
    """Check if memory reader is calibrated."""
    cal = load_calibration()
    return cal and cal.get('seat_base') is not None


if __name__ == '__main__':
    if '--test' in sys.argv:
        print("Testing memory reader...")
        reader = MemoryReader()
        reader.pid = reader.find_pokerstars()
        
        if not reader.pid:
            print("PokerStars not running")
            sys.exit(1)
        
        print(f"Found PokerStars PID: {reader.pid}")
        reader.handle = reader.open_process(reader.pid)
        
        if not reader.handle:
            print("Could not open process")
            sys.exit(1)
        
        regions = reader.enumerate_regions()
        total_mb = sum(r[1] for r in regions) / 1024 / 1024
        print(f"Found {len(regions)} memory regions ({total_mb:.1f} MB)")
        
        # Check if already calibrated
        cal = load_calibration()
        if cal and cal.get('seat_base'):
            reader.seat_base = cal['seat_base']
            print(f"Using saved seat base: {hex(reader.seat_base)}")
            cards = reader.read_hero_cards()
            if cards:
                print(f"Hero cards: {cards[0]} {cards[1]}")
            else:
                print("Could not read cards (offsets may have changed)")
        else:
            print("Not calibrated. Run helper_bar.py --calibrate")
        
        reader.close()
    else:
        print("Memory Reader - Uses known PokerStars offsets")
        print("")
        print("Usage:")
        print("  python memory_calibrator.py --test  # Test reading")
        print("")
        print("Calibration: python helper_bar.py --calibrate")
        print("Then press F9 once - GPT detects cards, we find the base pointer.")
        print("After that, cards are read in <1ms instead of ~5s.")
