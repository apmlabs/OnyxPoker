"""
Memory Calibrator v5 - Container + message buffer approach

Reads hero cards + actions from PokerStars message buffer in memory.

The message buffer is an array of 0x40-byte entries on the heap:
  +0x00: hand_id (8B LE)
  +0x08: sequence (4B)
  +0x14: msg_type (1B) — 0x0A=new_hand, 0x01=action, 0x02=seated, 0x07=action_start
  +0x16: seat_index (1B, 0-based)
  +0x17: action_code (1B) — 0x43=CALL, 0x45=RAISE, 0x46=FOLD, 0x50=POST_BB, 0x70=POST_SB
  +0x18: amount (2B uint16, cents)
  +0x1C: name_ptr (4B) -> player name
  +0x20: name_len (4B)
  +0x24: name_capacity (4B)
  +0x28: extra_ptr (4B) -> hero's type 0x02: 4-byte ASCII cards (e.g. "8h5d")
  +0x2C: extra_len (4B)

Buffer discovery (two methods, container tried first):

1. Container scan (primary, ~2.9x faster than anchor):
   Search heap (0x08M-0x22M) for magic number 0x0B0207EA at container+0x54.
   Validate with 24-byte anchor at +0x6C:
     05000000 05000000 02000000 00000000 00000000 00030300
   Validate: +0x38 has B4 07 8C 01, +0x44==0x3C, +0xE0==1, +0xE4=valid pointer.
   Read buf-8 from +0xE4, entry count from (+0xE8 - +0xE4) / 0x40.
   Magic number is 100% stable across all dumps (verified 7/7).
   Container address cached for instant rescan.

2. 0x88 signature scan (fallback):
   Search for `00 88 00 00 00 00 00 00 00 00` before first entry.
   Validate first entry (hand_id in range + seq=1), pick highest hand_id.

Verified: 40/40 dumps across 2 PIDs (16496, 20236), 0 mismatches.
Performance: Magic scan 150ms vs anchor 480ms (2.9x faster, verified on 7 dumps).
"""

import sys
import os
import json
import struct
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

DUMP_DIR = os.path.join(os.path.dirname(__file__), '..', 'server', 'uploads', 'memory_dumps')
CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), 'memory_offsets.json')

HERO_NAME = 'idealistslp'
ENTRY_SIZE = 0x40
# 10-byte signature immediately before first buffer entry (fallback scan)
BUFFER_SIGNATURE = bytes([0x00, 0x88, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
# 24-byte build-independent anchor at container +0x6C (6-max: seats=5, blinds=2, flags)
# Verified across PIDs 16496 (sig 0x01C351F4) and 20236 (sig 0x018E51F4) — 40/40 dumps
CONTAINER_ANCHOR = (
    struct.pack('<I', 5) +         # +0x6C: num_seats - 1
    struct.pack('<I', 5) +         # +0x70: num_seats - 1
    struct.pack('<I', 2) +         # +0x74: num_blinds
    struct.pack('<I', 0) +         # +0x78: zero
    struct.pack('<I', 0) +         # +0x7C: zero
    struct.pack('<I', 0x00030300)  # +0x80: flags
)
CONTAINER_ANCHOR_OFFSET = 0x6C  # offset of anchor within container struct
# Heap address range for container scan (covers all observed container addresses)
HEAP_RANGE = (0x08000000, 0x22000000)
ACTION_NAMES = {0x42: 'BET', 0x43: 'CALL', 0x45: 'RAISE', 0x46: 'FOLD', 0x50: 'POST_BB', 0x63: 'CHECK', 0x70: 'POST_SB', 0x77: 'WIN'}
MSG_TYPES = {0x0A: 'NEW_HAND', 0x01: 'ACTION', 0x02: 'SEATED', 0x05: 'DEAL', 0x06: 'WIN', 0x07: 'ACTION_START'}


def log(msg):
    print(f"[MEM] {msg}")


# ── Entry Decoder ────────────────────────────────────────────────────

def decode_entry(data_40bytes, read_str_fn=None):
    """Decode a single 0x40-byte message buffer entry."""
    e = data_40bytes
    hand_id = struct.unpack('<Q', e[0:8])[0]
    seq = struct.unpack('<I', e[8:12])[0]
    msg_type = e[0x14]
    seat = e[0x16]
    action_code = e[0x17]
    amount = struct.unpack('<H', e[0x18:0x1A])[0]
    name_ptr = struct.unpack('<I', e[0x1C:0x20])[0]
    name_len = struct.unpack('<I', e[0x20:0x24])[0]
    extra_ptr = struct.unpack('<I', e[0x28:0x2C])[0]
    extra_len = struct.unpack('<I', e[0x2C:0x30])[0]

    name = None
    extra = None
    if read_str_fn and 0x01000000 < name_ptr < 0x7FFFFFFF:
        name = read_str_fn(name_ptr, 64)
    if read_str_fn and 0x01000000 < extra_ptr < 0x7FFFFFFF:
        extra = read_str_fn(extra_ptr, 16)

    return {
        'hand_id': hand_id, 'seq': seq, 'msg_type': msg_type,
        'seat': seat, 'action_code': action_code, 'amount': amount,
        'name_ptr': name_ptr, 'name': name,
        'extra_ptr': extra_ptr, 'extra': extra,
    }


def decode_buffer(buf_addr, read_bytes_fn, read_str_fn, max_entries=30):
    """Decode all entries from a message buffer. Returns list of entry dicts."""
    entries = []
    first_hid = None
    for i in range(max_entries):
        data = read_bytes_fn(buf_addr + i * ENTRY_SIZE, ENTRY_SIZE)
        if not data or len(data) < ENTRY_SIZE:
            break
        e = decode_entry(data, read_str_fn)
        if i == 0:
            first_hid = e['hand_id']
        elif e['hand_id'] != first_hid:
            break
        entries.append(e)
    return entries


def format_entry(e):
    """Human-readable string for one entry."""
    if e['msg_type'] == 0x0A:
        return f"[{e['seq']:2d}] NEW_HAND"
    elif e['msg_type'] == 0x02:
        cards = f" [{e['extra']}]" if e['extra'] else ""
        seat = f"seat={e['seat']}" if e['seat'] != 255 else "BOARD"
        return f"[{e['seq']:2d}] SEATED {seat} {e['name'] or ''}{cards}"
    elif e['msg_type'] == 0x05:
        return f"[{e['seq']:2d}] DEAL"
    elif e['msg_type'] == 0x06:
        return f"[{e['seq']:2d}] WIN {e['name'] or ''}"
    elif e['msg_type'] == 0x01:
        act = ACTION_NAMES.get(e['action_code'], f"0x{e['action_code']:02X}")
        return f"[{e['seq']:2d}] {act} {e['name'] or '?'} {e['amount']}c"
    elif e['msg_type'] == 0x07:
        return f"[{e['seq']:2d}] ACTION_START {e['name'] or ''}"
    mt = MSG_TYPES.get(e['msg_type'], f"0x{e['msg_type']:02X}")
    return f"[{e['seq']:2d}] type={mt} seat={e['seat']} {e['name'] or ''}"


def extract_hand_data(entries):
    """Extract poker-relevant data from decoded entries.
    
    Uses card cache: if hero_cards not found in entries (string pointers freed),
    falls back to last known cards for this hand_id.
    """
    global _card_cache
    
    if not entries:
        return None
    hand_id = entries[0]['hand_id']
    hero_cards = None
    community_cards = []
    players = {}
    actions = []
    hero_seat = None
    bb_seat = None

    for e in entries:
        if e['msg_type'] == 0x05:
            # DEAL marker — street boundary for action tracking
            actions.append((None, 'DEAL', 0))
        elif e['msg_type'] == 0x02:
            if e['seat'] == 255 and e['extra']:
                # Community cards: seat=255, extra = card string
                cc = e['extra']
                for i in range(0, len(cc) - 1, 2):
                    community_cards.append(cc[i:i+2])
            else:
                players[e['seat']] = e['name']
                if e['extra'] and e['name'] == HERO_NAME:
                    hero_cards = e['extra']
                    hero_seat = e['seat']
        elif e['msg_type'] == 0x01:
            act = ACTION_NAMES.get(e['action_code'], f"0x{e['action_code']:02X}")
            # Use players dict to get name (e['name'] might be None if string freed)
            name = players.get(e['seat'], e['name'])
            actions.append((name, act, e['amount']))
            if e['action_code'] == 0x50 and bb_seat is None:  # POST_BB
                bb_seat = e['seat']

    # Card caching: save when found, restore ONLY for same hand_id
    if hero_cards:
        _card_cache[hand_id] = hero_cards
    elif hand_id in _card_cache:
        # Only use cache for SAME hand (string pointers freed but hand ongoing)
        hero_cards = _card_cache[hand_id]
    # If cards not found and not in cache, return None
    # This happens briefly at start of new hand until SEATED entries written

    # Derive position from hero_seat relative to BB in 6-max
    position = None
    if hero_seat is not None and bb_seat is not None and len(players) > 0:
        n = len(players)  # number of seats (typically 6)
        # Seats after BB in clockwise order: UTG, MP, CO, BTN, SB, BB
        # Distance from BB+1 (UTG) determines position
        positions_6max = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
        dist = (hero_seat - bb_seat - 1) % n
        if dist < len(positions_6max):
            position = positions_6max[dist]

    return {'hand_id': hand_id, 'hero_cards': hero_cards, 'players': players,
            'actions': actions, 'community_cards': community_cards,
            'hero_seat': hero_seat, 'bb_seat': bb_seat, 'position': position}


# ── Process Reader (Windows only) ───────────────────────────────────

class ProcessReader:
    def __init__(self):
        self.handle = None
        self.pid = None
        self.module_base = None

    def attach(self):
        if not IS_WINDOWS:
            return False
        self.pid = self._find_pid()
        if not self.pid:
            log("PokerStars.exe not found"); return False
        self.handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, self.pid)
        if not self.handle:
            log("OpenProcess failed"); return False
        self.module_base = self._get_module_base()
        log(f"Attached: PID={self.pid} module=0x{self.module_base or 0:X}")
        return True

    def _find_pid(self):
        import subprocess
        try:
            out = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq PokerStars.exe" /FO CSV',
                shell=True, stderr=subprocess.DEVNULL)
            for line in out.decode().strip().split('\n')[1:]:
                parts = line.split(',')
                if len(parts) >= 2:
                    return int(parts[1].strip('"'))
        except Exception:
            pass
        return None

    def _get_module_base(self):
        try:
            hMods = (ctypes.c_void_p * 1024)()
            needed = ctypes.c_ulong()
            ctypes.windll.psapi.EnumProcessModulesEx(
                self.handle, hMods, ctypes.sizeof(hMods),
                ctypes.byref(needed), 0x03)
            return hMods[0] if needed.value > 0 else None
        except Exception:
            return None

    def read(self, addr, size):
        if not self.handle:
            return None
        buf = ctypes.create_string_buffer(size)
        nread = ctypes.c_size_t()
        ok = ctypes.windll.kernel32.ReadProcessMemory(
            self.handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(nread))
        return buf.raw[:nread.value] if ok and nread.value > 0 else None

    def read_str(self, addr, maxlen=64):
        data = self.read(addr, maxlen)
        if not data:
            return None
        end = data.find(b'\x00')
        if end <= 0:
            return None
        try:
            return data[:end].decode('ascii')
        except Exception:
            return None

    def iter_regions(self):
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        while ctypes.windll.kernel32.VirtualQueryEx(
            self.handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            if mbi.RegionSize is None or mbi.RegionSize <= 0:
                break
            if mbi.State == MEM_COMMIT and (mbi.Protect & PAGE_READABLE):
                yield (mbi.BaseAddress or 0, mbi.RegionSize)
            addr = (mbi.BaseAddress or 0) + mbi.RegionSize
            if addr <= (mbi.BaseAddress or 0):
                break


# ── Dump on F9 (called from helper_bar) ─────────────────────────────

_reader = None

def save_dump(timestamp=None):
    """Called on F9. Dumps PS memory to disk. Returns dump_id or None."""
    global _reader
    if not IS_WINDOWS:
        return None
    if _reader is None:
        _reader = ProcessReader()
    if not _reader.handle and not _reader.attach():
        return None

    os.makedirs(DUMP_DIR, exist_ok=True)
    ts = timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')
    dump_id = f'dump_{ts}'
    bin_path = os.path.join(DUMP_DIR, f'{dump_id}.bin')
    meta_path = os.path.join(DUMP_DIR, f'{dump_id}.json')

    regions = []
    file_offset = 0
    with open(bin_path, 'wb') as f:
        for base, size in _reader.iter_regions():
            if size > 100 * 1024 * 1024:
                continue
            data = _reader.read(base, size)
            if data:
                f.write(data)
                regions.append({'base': base, 'size': len(data), 'file_offset': file_offset})
                file_offset += len(data)

    meta = {
        'dump_id': dump_id, 'timestamp': ts,
        'pid': _reader.pid, 'module_base': _reader.module_base,
        'regions': regions, 'bytes_total': file_offset,
    }
    with open(meta_path, 'w') as f:
        json.dump(meta, f)
    log(f"Dump: {len(regions)} regions, {file_offset/1024/1024:.0f} MB")
    return dump_id


def tag_dump(dump_id, gpt_result):
    """Called after GPT returns. Tags dump with vision data."""
    if not dump_id:
        return
    meta_path = os.path.join(DUMP_DIR, f'{dump_id}.json')
    if not os.path.exists(meta_path):
        return
    with open(meta_path) as f:
        meta = json.load(f)
    meta['hand_id'] = gpt_result.get('hand_id')
    meta['hero_cards'] = gpt_result.get('hero_cards', [])
    meta['community_cards'] = gpt_result.get('community_cards', [])
    meta['pot'] = gpt_result.get('pot')
    meta['opponents'] = [
        {'name': o.get('name', ''), 'has_cards': o.get('has_cards', False)}
        for o in gpt_result.get('opponents', [])
    ]
    with open(meta_path, 'w') as f:
        json.dump(meta, f)


# ── Dump File Helpers ────────────────────────────────────────────────

def _load_tagged_dumps():
    if not os.path.isdir(DUMP_DIR):
        return []
    dumps = []
    for fname in sorted(os.listdir(DUMP_DIR)):
        if not fname.endswith('.json'):
            continue
        meta_path = os.path.join(DUMP_DIR, fname)
        bin_path = meta_path.replace('.json', '.bin')
        if not os.path.exists(bin_path):
            # Try .bin.gz — decompress on first use
            gz_path = bin_path + '.gz'
            if os.path.exists(gz_path):
                import gzip
                log(f"Decompressing {os.path.basename(gz_path)}...")
                with gzip.open(gz_path, 'rb') as gz, open(bin_path, 'wb') as out:
                    while True:
                        chunk = gz.read(1 << 20)
                        if not chunk:
                            break
                        out.write(chunk)
            else:
                continue
        with open(meta_path) as f:
            meta = json.load(f)
        if not meta.get('hero_cards') or len(meta['hero_cards']) < 2:
            continue
        meta['_bin_path'] = bin_path
        dumps.append(meta)
    return dumps


def _make_read_fns(bin_path, regions):
    """Return (read_bytes, read_str) functions for a dump file."""
    def read_bytes(addr, size):
        for r in regions:
            if r['base'] <= addr < r['base'] + r['size']:
                off = addr - r['base']
                with open(bin_path, 'rb') as f:
                    f.seek(r['file_offset'] + off)
                    return f.read(min(size, r['size'] - off))
        return None

    def read_str(addr, maxlen=64):
        data = read_bytes(addr, maxlen)
        if not data:
            return None
        end = data.find(b'\x00')
        if end <= 0:
            return None
        try:
            return data[:end].decode('ascii')
        except Exception:
            return None

    return read_bytes, read_str


# ── Signature-Based Buffer Finder ────────────────────────────────────

def _find_buffer_via_container(data_iter, read_bytes_fn, debug=False):
    """Find buffer by scanning for magic number 0x0B0207EA at container+0x54.
    
    This is 2.9x faster than 24-byte anchor scan (verified across 7 dumps).
    Magic number is 100% stable and appears at container+0x54 in all cases.
    We validate with the 24-byte anchor to ensure correct container.

    data_iter yields (base_addr, data_bytes) for each memory region.
    Returns (buf_addr, entry_count, hand_id, container_addr) or (None, 0, 0, None).
    """
    best = None  # (buf_addr, entry_count, hand_id, container_addr)
    regions_scanned = 0
    magic_hits = 0
    validated = 0
    
    MAGIC_NUMBER = struct.pack('<I', 0x0B0207EA)
    MAGIC_OFFSET = 0x54  # Magic appears at container+0x54
    
    for base, data in data_iter:
        regions_scanned += 1
        idx = 0
        while True:
            # Scan for magic number (2.9x faster than anchor)
            idx = data.find(MAGIC_NUMBER, idx)
            if idx < 0:
                break
            magic_hits += 1
            
            # Container would be at: idx - MAGIC_OFFSET
            sb = idx - MAGIC_OFFSET  # struct_base offset within data
            if sb < 0 or sb + 0xF0 > len(data):
                idx += 1; continue
            
            # Validate with 24-byte anchor at +0x6C
            anchor_offset = sb + CONTAINER_ANCHOR_OFFSET
            if anchor_offset + 24 > len(data):
                idx += 1; continue
            if data[anchor_offset:anchor_offset+24] != CONTAINER_ANCHOR:
                idx += 1; continue
            
            # Confirm signature at +0x38
            if data[sb+0x38] != 0xB4 or data[sb+0x39] != 0x07 or data[sb+0x3A] != 0x8C or data[sb+0x3B] != 0x01:
                idx += 1; continue
            # Validate +0x44 == 0x3C
            if struct.unpack('<I', data[sb+0x44:sb+0x48])[0] != 0x3C:
                idx += 1; continue
            # Validate +0xE0 == 1
            if struct.unpack('<I', data[sb+0xE0:sb+0xE4])[0] != 1:
                idx += 1; continue
            # Read buf-8 pointer from +0xE4
            bp = struct.unpack('<I', data[sb+0xE4:sb+0xE8])[0]
            if bp < 0x100000:
                idx += 1; continue
            # Entry count from +0xE8
            ep = struct.unpack('<I', data[sb+0xE8:sb+0xEC])[0]
            n_entries = (ep - bp) // ENTRY_SIZE
            if n_entries < 3 or n_entries > 200:
                idx += 1; continue
            # Read hand_id from first buffer entry (bp + 8)
            hid_data = read_bytes_fn(bp + 8, 8)
            if not hid_data or len(hid_data) < 8:
                idx += 1; continue
            hid = struct.unpack('<Q', hid_data)[0]
            if not (200_000_000_000 < hid < 300_000_000_000):
                idx += 1; continue
            validated += 1
            container_addr = base + sb
            if not best or hid > best[2]:
                best = (bp + 8, n_entries, hid, container_addr)
            idx += 1
    
    if debug:
        log(f"[CONTAINER] Scanned {regions_scanned} regions, {magic_hits} magic hits, {validated} validated, best={best is not None}")
    
    return best or (None, 0, 0, None)


def find_buffer_in_dump(bin_path, regions, expected_cards_ascii=None):
    """Find the message buffer. Tries container anchor first (~2.3x faster),
    falls back to 0x88 signature scan.

    Returns (buf_addr, entries) or (None, None).
    
    Note: Expects uncompressed .bin files. If .bin.gz uploaded, decompress first.
    """
    read_bytes, read_str = _make_read_fns(bin_path, regions)

    # Try container scan first — only scan heap range for speed
    def _region_iter():
        with open(bin_path, 'rb') as f:
            for r in regions:
                if r['base'] < HEAP_RANGE[0] or r['base'] >= HEAP_RANGE[1]:
                    continue
                if r['size'] < 0x200:
                    continue
                f.seek(r['file_offset'])
                yield r['base'], f.read(r['size'])

    buf_addr, n_entries, hid, container_addr = _find_buffer_via_container(_region_iter(), read_bytes)
    if buf_addr:
        # Save container address for pointer scan
        find_buffer_in_dump._last_container_addr = container_addr
        entries = decode_buffer(buf_addr, read_bytes, read_str, n_entries)
        if len(entries) >= 3:
            return buf_addr, entries

    # Fallback: 0x88 signature scan
    candidates = []  # (buf_addr, hand_id)

    with open(bin_path, 'rb') as f:
        for r in regions:
            f.seek(r['file_offset'])
            data = f.read(r['size'])
            idx = 0
            while True:
                idx = data.find(BUFFER_SIGNATURE, idx)
                if idx < 0:
                    break
                entry_off = idx + 10  # signature is 10 bytes before first entry
                if entry_off + 16 <= len(data):
                    hid = struct.unpack('<Q', data[entry_off:entry_off+8])[0]
                    seq = struct.unpack('<I', data[entry_off+8:entry_off+12])[0]
                    if 200_000_000_000 < hid < 300_000_000_000 and seq == 1:
                        candidates.append((r['base'] + entry_off, hid))
                idx += 1

    if not candidates:
        return None, None

        # Pick highest hand_id
        max_hid = max(c[1] for c in candidates)
        best = [c for c in candidates if c[1] == max_hid]

        if len(best) == 1:
            buf_addr = best[0][0]
        else:
            # Tiebreak: find the one with readable hero name in SEATED entries
            buf_addr = best[0][0]
            for ba, hid in best:
                entries = decode_buffer(ba, read_bytes, read_str)
                for e in entries:
                    if e['msg_type'] == 0x02 and e['name'] == HERO_NAME:
                        buf_addr = ba
                        break

    entries = decode_buffer(buf_addr, read_bytes, read_str)
    return (buf_addr, entries) if len(entries) >= 3 else (None, None)


def _fuzzy_match(a, b):
    """Check if two names match allowing 1-char difference (GPT vision errors like O/0)."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(c1 != c2 for c1, c2 in zip(a, b)) <= 1
    # Length differs by 1: check if one is substring-ish
    short, long = (a, b) if len(a) < len(b) else (b, a)
    diffs = 0
    si = li = 0
    while si < len(short) and li < len(long):
        if short[si] != long[li]:
            diffs += 1
            li += 1
        else:
            si += 1
            li += 1
    return diffs <= 1


# ── Deep Pointer Analysis ────────────────────────────────────────────

def _find_pointers_to_address(data, target_addr, base_addr=0):
    """Find all 4-byte aligned locations containing target_addr as pointer.
    Returns list of absolute addresses where pointer was found.
    """
    target_bytes = struct.pack('<I', target_addr)
    pointers = []
    # Search every 4-byte aligned location
    for i in range(0, len(data) - 4, 4):
        if data[i:i+4] == target_bytes:
            pointers.append(base_addr + i)
    return pointers


def _analyze_container_structure(bin_path, regions, container_addr):
    """Deep analysis of memory before container to find structure boundaries.
    
    Compares bytes before container across multiple dumps to find:
    1. Where the actual structure starts (might be before our known container base)
    2. Stable patterns that indicate structure boundaries
    3. Pointers to the structure from elsewhere in memory
    """
    read_bytes, _ = _make_read_fns(bin_path, regions)
    
    # Read 1KB before container to analyze structure boundaries
    LOOKBACK = 1024
    pre_data = read_bytes(container_addr - LOOKBACK, LOOKBACK)
    if not pre_data:
        return None
    
    # Read container itself (known to be ~0x1E8 bytes)
    container_data = read_bytes(container_addr, 0x200)
    if not container_data:
        return None
    
    return {
        'container_addr': container_addr,
        'pre_data': pre_data,
        'container_data': container_data,
    }


def _deep_pointer_scan(dumps_data):
    """Cross-dump pointer analysis.
    
    For each dump:
    1. Find container address
    2. Search for pointers to container (and container-8, -16, -32, -64, -128, -256)
    3. Compare pointer locations across dumps to find stable patterns
    4. Categorize by memory region (module vs heap)
    
    Returns dict with analysis results.
    """
    from collections import defaultdict
    
    results = []
    pointer_map = defaultdict(list)  # offset -> [(dump_name, container_addr, target_offset)]
    
    # Offsets to check before container (structure might start earlier)
    SEARCH_OFFSETS = [0, -8, -16, -32, -64, -128, -256, -512]
    
    log(f"  Scanning {len(dumps_data)} dumps for pointers...")
    for i, dump in enumerate(dumps_data, 1):
        dump_name = os.path.basename(dump['_bin_path']).replace('.bin', '')
        bin_path = dump['_bin_path']
        regions = dump['regions']
        
        log(f"    [{i}/{len(dumps_data)}] {dump_name}...")
        
        # Find container
        buf_addr, entries = find_buffer_in_dump(bin_path, regions)
        if not buf_addr or not hasattr(find_buffer_in_dump, '_last_container_addr'):
            log(f"      SKIP (no container)")
            continue
        
        container_addr = find_buffer_in_dump._last_container_addr
        log(f"      Container: 0x{container_addr:08X}")
        
        # Analyze structure boundaries
        struct_info = _analyze_container_structure(bin_path, regions, container_addr)
        if not struct_info:
            log(f"      SKIP (can't read structure)")
            continue
        
        # Load full dump for pointer scanning
        log(f"      Loading dump ({os.path.getsize(bin_path)//1024//1024}MB)...")
        with open(bin_path, 'rb') as f:
            full_data = f.read()
        
        # Search for pointers to container and nearby addresses
        log(f"      Scanning for pointers to {len(SEARCH_OFFSETS)} target addresses...")
        for offset in SEARCH_OFFSETS:
            target_addr = container_addr + offset
            if target_addr < 0:
                continue
            
            # Find all pointers to this address
            pointers = []
            for r in regions:
                region_data = full_data[r['file_offset']:r['file_offset']+r['size']]
                ptrs = _find_pointers_to_address(region_data, target_addr, r['base'])
                pointers.extend(ptrs)
            
            if pointers:
                log(f"        container{offset:+4d}: {len(pointers)} pointers")
            
            # Store results
            for ptr_addr in pointers:
                pointer_map[ptr_addr].append((dump_name, container_addr, offset))
        
        results.append({
            'dump_name': dump_name,
            'container_addr': container_addr,
            'struct_info': struct_info,
        })
    
    return {
        'dumps': results,
        'pointer_map': pointer_map,
    }


def _compare_pre_container_bytes(dumps_data):
    """Compare bytes before container across all dumps to find structure start.
    
    Returns analysis of stable patterns before the known container base.
    """
    pre_data_list = []
    
    log(f"  Loading {len(dumps_data)} dumps to compare pre-container bytes...")
    for i, dump in enumerate(dumps_data, 1):
        bin_path = dump['_bin_path']
        regions = dump['regions']
        dump_name = os.path.basename(bin_path).replace('.bin', '')
        
        log(f"    [{i}/{len(dumps_data)}] {dump_name}...")
        buf_addr, entries = find_buffer_in_dump(bin_path, regions)
        if not buf_addr or not hasattr(find_buffer_in_dump, '_last_container_addr'):
            log(f"      SKIP (no container)")
            continue
        
        container_addr = find_buffer_in_dump._last_container_addr
        struct_info = _analyze_container_structure(bin_path, regions, container_addr)
        if struct_info:
            pre_data_list.append({
                'dump': dump_name,
                'container_addr': container_addr,
                'pre_data': struct_info['pre_data'],
            })
            log(f"      OK (container at 0x{container_addr:08X})")
    
    if len(pre_data_list) < 2:
        return None
    
    log(f"  Comparing bytes across {len(pre_data_list)} dumps...")
    # Find common patterns in pre-data
    # Compare byte-by-byte across all dumps
    LOOKBACK = 1024
    stable_ranges = []  # (offset_from_container, length, pattern)
    
    for offset in range(-LOOKBACK, 0, 4):  # Check every 4 bytes
        # Get byte at this offset from all dumps
        bytes_at_offset = []
        for pd in pre_data_list:
            idx = LOOKBACK + offset
            if 0 <= idx < len(pd['pre_data']):
                bytes_at_offset.append(pd['pre_data'][idx:idx+4])
        
        # Check if all dumps have same bytes
        if len(bytes_at_offset) == len(pre_data_list) and len(set(map(tuple, bytes_at_offset))) == 1:
            # All dumps have same 4 bytes at this offset
            stable_ranges.append((offset, 4, bytes_at_offset[0]))
    
    return {
        'dumps_compared': len(pre_data_list),
        'stable_ranges': stable_ranges,
        'pre_data_samples': pre_data_list[:3],  # First 3 for inspection
    }


# ── Offline Analysis ─────────────────────────────────────────────────



def cmd_scan_pointers():
    """Deep pointer analysis across all dumps."""
    dumps = _load_tagged_dumps()
    if not dumps:
        log("No tagged dumps. Run: python helper_bar.py --calibrate")
        return
    
    log(f"=== DEEP POINTER ANALYSIS ===")
    log(f"Analyzing {len(dumps)} dumps...\n")
    
    # Phase 1: Compare bytes before container to find structure start
    log("Phase 1: Analyzing memory before container...")
    pre_analysis = _compare_pre_container_bytes(dumps)
    if pre_analysis:
        log(f"  Compared {pre_analysis['dumps_compared']} dumps")
        log(f"  Found {len(pre_analysis['stable_ranges'])} stable 4-byte patterns before container")
        if pre_analysis['stable_ranges']:
            log("  Top 10 stable patterns:")
            for offset, length, pattern in pre_analysis['stable_ranges'][:10]:
                hex_pattern = ' '.join(f'{b:02X}' for b in pattern)
                log(f"    container{offset:+5d}: {hex_pattern}")
    
    # Phase 2: Deep pointer scan
    log("\nPhase 2: Scanning for pointers to container...")
    pointer_analysis = _deep_pointer_scan(dumps)
    
    log(f"  Analyzed {len(pointer_analysis['dumps'])} dumps")
    
    # Find stable pointer locations (appear in multiple dumps)
    from collections import Counter
    pointer_counts = Counter()
    for ptr_addr, occurrences in pointer_analysis['pointer_map'].items():
        pointer_counts[ptr_addr] = len(occurrences)
    
    stable_pointers = [(addr, count) for addr, count in pointer_counts.items() if count >= 2]
    stable_pointers.sort(key=lambda x: x[1], reverse=True)
    
    log(f"  Total unique pointer locations: {len(pointer_analysis['pointer_map'])}")
    log(f"  Stable locations (2+ dumps): {len(stable_pointers)}")
    
    # Categorize stable pointers
    module_stable = [(a, c) for a, c in stable_pointers if a < 0x08000000]
    heap_stable = [(a, c) for a, c in stable_pointers if 0x08000000 <= a < 0x30000000]
    
    log(f"\n  MODULE pointers (0x00-0x08M): {len(module_stable)}")
    log(f"  HEAP pointers (0x08M-0x30M): {len(heap_stable)}")
    
    if module_stable:
        log("\n  TOP 10 STABLE MODULE POINTERS:")
        for addr, count in module_stable[:10]:
            log(f"    0x{addr:08X} - appears in {count} dumps")
            # Show what it points to
            for dump_name, container_addr, offset in pointer_analysis['pointer_map'][addr][:3]:
                target = container_addr + offset
                log(f"      {dump_name}: -> 0x{target:08X} (container{offset:+d})")
    else:
        log("\n  NO STABLE MODULE POINTERS FOUND")
        log("  Container is likely only referenced from heap (dynamic allocation)")
    
    if heap_stable:
        log("\n  TOP 10 STABLE HEAP POINTERS:")
        for addr, count in heap_stable[:10]:
            log(f"    0x{addr:08X} - appears in {count} dumps")
            for dump_name, container_addr, offset in pointer_analysis['pointer_map'][addr][:3]:
                target = container_addr + offset
                log(f"      {dump_name}: -> 0x{target:08X} (container{offset:+d})")
    
    # Summary
    log("\n" + "="*60)
    log("SUMMARY:")
    if module_stable:
        log(f"  Found {len(module_stable)} stable MODULE pointers")
        log("  These are candidates for static pointer chain starting points")
    else:
        log("  NO stable module pointers found")
        log("  Container appears to be heap-only (no static pointer chain)")
    
    if heap_stable:
        log(f"  Found {len(heap_stable)} stable HEAP pointers")
        log("  These indicate dynamic allocation chains on the heap")


def cmd_analyze():
    """Verify message buffer structure across all tagged dumps."""
    dumps = _load_tagged_dumps()
    if not dumps:
        print("[ANALYZE] No tagged dumps. Run: python helper_bar.py --calibrate", flush=True)
        return

    print(f"[ANALYZE] === Memory Calibrator v5 ===", flush=True)
    print(f"[ANALYZE] Dumps: {len(dumps)}\n", flush=True)

    errors = 0
    for i, meta in enumerate(dumps, 1):
        dump_id = meta['dump_id']
        hero_cards = meta['hero_cards']
        bin_path = meta['_bin_path']
        regions = meta['regions']
        # Handle both formats: list of dicts or list of strings
        opps_raw = meta.get('opponents', [])
        if opps_raw and isinstance(opps_raw[0], dict):
            opps = [o['name'] for o in opps_raw if o.get('name')]
        else:
            opps = [o for o in opps_raw if o]
        expected = ''.join(hero_cards) if hero_cards else None

        print(f"[ANALYZE] {'='*60}", flush=True)
        print(f"[ANALYZE] [{i}/{len(dumps)}] {dump_id}: cards={hero_cards} opps={opps}", flush=True)

        t0 = time.time()
        buf_addr, entries = find_buffer_in_dump(bin_path, regions, expected)
        elapsed = time.time() - t0

        if not buf_addr:
            print(f"[ANALYZE]   FAIL: buffer not found ({elapsed:.1f}s)", flush=True)
            errors += 1
            continue

        hand_data = extract_hand_data(entries)
        found_cards = hand_data['hero_cards']
        found_community = hand_data['community_cards']

        # Verify cards (allow reversed order)
        cards_ok = False
        if found_cards and expected:
            cards_ok = found_cards == expected
            if not cards_ok and len(found_cards) == 4:
                cards_ok = found_cards[2:4] + found_cards[0:2] == expected

        # Verify community cards against GPT
        comm_expected = meta.get('community_cards', [])
        comm_ok = set(found_community) == set(comm_expected) if comm_expected and found_community else True

        # Verify opponent names (fuzzy: allow 1-char difference for GPT vision errors)
        real_players = {s: n for s, n in hand_data['players'].items() if s != 255 and n}
        found_names = set(real_players.values())
        opps_ok = True
        for opp in opps:
            if opp not in found_names:
                # Fuzzy: check if any name is close (1-char diff or O/0 swap)
                fuzzy = any(_fuzzy_match(opp, fn) for fn in found_names)
                if not fuzzy:
                    opps_ok = False

        if not cards_ok:
            errors += 1

        print(f"[ANALYZE]   Buffer: 0x{buf_addr:08X} ({len(entries)} entries, {elapsed:.1f}s)", flush=True)
        print(f"[ANALYZE]   Hand ID: {hand_data['hand_id']}", flush=True)
        print(f"[ANALYZE]   Cards: '{found_cards}' {'OK' if cards_ok else 'FAIL (expected '+str(expected)+')'}", flush=True)
        print(f"[ANALYZE]   Players: {dict(real_players)} {'OK' if opps_ok else 'MISMATCH (GPT: '+str(opps)+')'}", flush=True)
        if found_community:
            print(f"[ANALYZE]   Community: {found_community} {'OK' if comm_ok else 'MISMATCH (GPT: '+str(comm_expected)+')'}", flush=True)
        print(f"[ANALYZE]   Actions: {len(hand_data['actions'])}", flush=True)
        for e in entries:
            log(f"    {format_entry(e)}")
        
        # Scan for pointers to container (if found via container method)
        if hasattr(find_buffer_in_dump, '_last_container_addr'):
            container_addr = find_buffer_in_dump._last_container_addr
            log(f"  Scanning for pointers to container 0x{container_addr:08X}...")
            
            # Load full dump
            with open(bin_path, 'rb') as f:
                mem = f.read()
            
            # Search for container address as 4-byte LE pointer
            target_bytes = struct.pack('<I', container_addr)
            hits = []
            offset = 0
            while True:
                idx = mem.find(target_bytes, offset)
                if idx == -1:
                    break
                hits.append(idx)
                offset = idx + 4
                if len(hits) >= 20:  # Limit to first 20
                    break
            
            log(f"  Found {len(hits)} pointers to container:")
            for addr in hits[:10]:
                if 0x00C00000 <= addr < 0x02000000:
                    log(f"    0x{addr:08X} [MODULE]")
                elif 0x08000000 <= addr < 0x22000000:
                    log(f"    0x{addr:08X} [HEAP]")
                else:
                    log(f"    0x{addr:08X}")

    log(f"\n{'='*60}")
    log(f"TOTAL ERRORS: {errors}")
    if errors == 0:
        log(f"ALL {len(dumps)} DUMPS VERIFIED")


# ── Fast Card Read (Windows runtime) ────────────────────────────────

# Cached container address — stable within a table session, avoids full rescan
_cached_container_addr = None

# Card cache per hand_id — when string pointers become invalid, use last known cards
_card_cache = {}  # hand_id → hero_cards (4-byte ASCII string)


def _read_buffer_from_container(container_addr, reader):
    """Read buffer pointer from a known container. Returns (buf_addr, n_entries, hand_id) or None."""
    data = reader.read(container_addr + 0xE0, 0x10)  # +0xE0 through +0xEC (16 bytes)
    if not data or len(data) < 0x10:
        return None
    if struct.unpack('<I', data[0:4])[0] != 1:  # +0xE0 validation
        return None
    bp = struct.unpack('<I', data[4:8])[0]       # +0xE4: buf-8
    ep = struct.unpack('<I', data[8:12])[0]      # +0xE8: end ptr
    if bp < 0x100000:
        return None
    n = (ep - bp) // ENTRY_SIZE
    if n < 3 or n > 200:
        return None
    hid_data = reader.read(bp + 8, 8)
    if not hid_data or len(hid_data) < 8:
        return None
    hid = struct.unpack('<Q', hid_data)[0]
    if not (200_000_000_000 < hid < 300_000_000_000):
        return None
    return (bp + 8, n, hid)


def scan_live():
    """Scan live PS memory for current hand data.

    Uses cached container address if available (instant pointer read).
    Otherwise scans heap for 24-byte container anchor, falls back to 0x88.
    Returns dict with hand_id, hero_cards, players, actions, scan_time,
    buf_addr, container_addr, or None on failure.
    """
    global _reader, _cached_container_addr
    if _reader is None:
        _reader = ProcessReader()
    if not _reader.handle and not _reader.attach():
        return None

    t0 = time.time()

    # Fast path: try cached container address first (just a pointer read, <1ms)
    if _cached_container_addr:
        result = _read_buffer_from_container(_cached_container_addr, _reader)
        if result:
            buf_addr, n_entries, hid = result
            entries = decode_buffer(buf_addr, _reader.read, _reader.read_str, n_entries)
            hand_data = extract_hand_data(entries)
            if hand_data and hand_data['hero_cards']:
                hand_data['scan_time'] = round(time.time() - t0, 2)
                hand_data['buf_addr'] = buf_addr
                hand_data['container_addr'] = _cached_container_addr
                hand_data['entry_count'] = len(entries)
                return hand_data
        # Cache miss — container moved or invalidated
        _cached_container_addr = None

    # Container scan — only heap range (skips ~47% of memory)
    def _live_iter():
        for base, size in _reader.iter_regions():
            if base < HEAP_RANGE[0] or base >= HEAP_RANGE[1]:
                continue
            if size < 0x200 or size > 100 * 1024 * 1024:
                continue
            data = _reader.read(base, size)
            if data:
                yield base, data

    buf_addr, n_entries, hid, container_addr = _find_buffer_via_container(
        _live_iter(), _reader.read, debug=True)
    if buf_addr:
        _cached_container_addr = container_addr
        entries = decode_buffer(buf_addr, _reader.read, _reader.read_str, n_entries)
        hand_data = extract_hand_data(entries)
        if hand_data and hand_data['hero_cards']:
            hand_data['scan_time'] = round(time.time() - t0, 2)
            hand_data['buf_addr'] = buf_addr
            hand_data['container_addr'] = container_addr
            hand_data['entry_count'] = len(entries)
            return hand_data

    # Fallback: 0x88 signature scan (all memory)
    candidates = []
    for base, size in _reader.iter_regions():
        if size > 100 * 1024 * 1024:
            continue
        data = _reader.read(base, size)
        if not data:
            continue
        idx = 0
        while True:
            idx = data.find(BUFFER_SIGNATURE, idx)
            if idx < 0:
                break
            entry_off = idx + 10
            if entry_off + 16 <= len(data):
                hid = struct.unpack('<Q', data[entry_off:entry_off+8])[0]
                seq = struct.unpack('<I', data[entry_off+8:entry_off+12])[0]
                if 200_000_000_000 < hid < 300_000_000_000 and seq == 1:
                    candidates.append((base + entry_off, hid))
            idx += 1

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[1], reverse=True)

    for buf_addr, hid in candidates:
        entries = decode_buffer(buf_addr, _reader.read, _reader.read_str)
        hand_data = extract_hand_data(entries)
        if hand_data and hand_data['hero_cards']:
            hand_data['scan_time'] = round(time.time() - t0, 2)
            hand_data['buf_addr'] = buf_addr
            hand_data['entry_count'] = len(entries)
            return hand_data

    return None


def rescan_buffer(buf_addr, expected_hand_id=None):
    """Re-read a known buffer address. <1ms. Returns hand_data or None.
    If buffer moved (new hand), tries cached container for instant redirect."""
    global _reader, _cached_container_addr
    if _reader is None or not _reader.handle:
        return None
    
    # FIRST: Check if container moved to a new hand (even if buffer hasn't updated yet)
    if expected_hand_id and _cached_container_addr:
        result = _read_buffer_from_container(_cached_container_addr, _reader)
        if result:
            new_buf_addr, n_entries, new_hid = result[0], result[1], result[2]
            
            # If container points to a DIFFERENT hand than expected, follow it
            if new_hid != expected_hand_id:
                entries = decode_buffer(new_buf_addr, _reader.read, _reader.read_str, n_entries)
                hand_data = extract_hand_data(entries)
                if hand_data:
                    hand_data['buf_addr'] = new_buf_addr
                    hand_data['entry_count'] = len(entries)
                    hand_data['hand_id_changed'] = True
                return hand_data
    
    # Container says same hand - rescan buffer at known address
    entries = decode_buffer(buf_addr, _reader.read, _reader.read_str)
    hand_data = extract_hand_data(entries)
    if hand_data:
        # Validate: if we have actions but no player names, buffer is corrupted
        actions = hand_data.get('actions', [])
        if actions and len(actions) > 2:  # More than just blinds
            # Check if any non-blind action has a real name
            has_real_names = any(name and name != 'None' for name, act, amt in actions 
                                if act not in ('POST_SB', 'POST_BB', 'DEAL'))
            if not has_real_names:
                # Buffer corrupted - return None to trigger full rescan
                return None
        
        hand_data['buf_addr'] = buf_addr
        hand_data['entry_count'] = len(entries)
    return hand_data


def read_cards_fast():
    """API for helper_bar: returns ['Ah', 'Kd'] or None."""
    result = scan_live()
    if not result or not result.get('hero_cards'):
        return None
    cards = result['hero_cards']
    if len(cards) != 4:
        return None
    return [cards[0:2], cards[2:4]]


def is_calibrated():
    """Signature-based approach doesn't need pre-calibration."""
    return IS_WINDOWS


def calibrate_after_gpt(gpt_result):
    """Legacy API - no-op."""
    pass


def load_calibration():
    try:
        with open(CALIBRATION_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def save_calibration(data):
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# ── CLI ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else ''
    if cmd == 'analyze':
        cmd_analyze()
    elif cmd == 'scan_pointers':
        cmd_scan_pointers()
    elif cmd == 'read':
        if not IS_WINDOWS:
            log("Windows only")
        else:
            r = scan_live()
            if r:
                log(f"Cards: {r['hero_cards']}  hand_id: {r['hand_id']}  "
                    f"players: {r['players']}  ({r['scan_time']}s)")
            else:
                log("Could not find buffer")
    elif cmd == 'dump':
        did = save_dump()
        log(f"Saved: {did}" if did else "Failed (Windows only)")
    elif cmd == 'list':
        dumps = _load_tagged_dumps()
        log(f"{len(dumps)} tagged dumps:")
        for d in dumps:
            log(f"  {d['dump_id']}: hand={d.get('hand_id')} cards={d.get('hero_cards')} "
                f"opps={[o['name'] for o in d.get('opponents',[])]}")
    else:
        print("Usage:")
        print("  python memory_calibrator.py analyze        # Verify message buffer in all dumps")
        print("  python memory_calibrator.py scan_pointers  # Find pointers to container")
        print("  python memory_calibrator.py read           # Read cards live (Windows only)")
        print("  python memory_calibrator.py list           # Show tagged dumps")
        print("  python memory_calibrator.py dump           # Manual dump (Windows only)")
