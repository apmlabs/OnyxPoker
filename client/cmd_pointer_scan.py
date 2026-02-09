"""
Pointer Scanner v2 — CE-style cross-validated reverse pointer scan.

Finds a static pointer chain: module+X → *(heap) + Y → ... → buffer

Algorithm:
  Pick 2 dumps (A, B) from same PID where buffer is at different addresses.
  Load BOTH into memory for fast random access.
  Level 1: Scan B for any 4-byte value V where buf_B - V in [0, MAX_OFFSET].
           For each hit at address P with offset O:
             Cross-validate: read same address P in dump A, check if value == buf_A - O.
             If validated AND P is in module → FOUND static pointer.
             If validated AND P is on heap → save for level 2.
  Level 2+: Repeat with heap hits as new targets.
"""

import sys, os, json, struct, time, bisect
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import memory_calibrator as mc

mc.DUMP_DIR = os.environ.get(
    'DUMP_DIR',
    os.path.join(os.path.dirname(os.path.dirname(__file__)),
                 'server', 'uploads', 'memory_dumps'))

MAX_OFFSET = 0x1000   # 4KB
ALIGN = 4
MIN_PTR = 0x00100000
MAX_PTR = 0x7FFFFFFF


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


class DumpSnapshot:
    """Entire dump loaded into memory for fast access."""

    def __init__(self, meta, buf_addr):
        self.dump_id = meta['dump_id']
        self.buf_addr = buf_addr
        self.module_base = meta['module_base']
        self.regions = sorted(meta['regions'], key=lambda r: r['base'])
        self._bases = [r['base'] for r in self.regions]

        # Load ALL regions into a dict: base_addr -> bytes
        log(f"  Loading {self.dump_id} into memory...")
        t0 = time.time()
        self._data = {}
        total = 0
        with open(meta['_bin_path'], 'rb') as f:
            for r in self.regions:
                f.seek(r['file_offset'])
                self._data[r['base']] = f.read(r['size'])
                total += r['size']
        log(f"  Loaded {len(self.regions)} regions, {total/1024/1024:.0f} MB "
            f"({time.time()-t0:.1f}s)")

    def read_u32(self, addr):
        idx = bisect.bisect_right(self._bases, addr) - 1
        if idx < 0:
            return None
        r = self.regions[idx]
        off = addr - r['base']
        if off < 0 or off + 4 > r['size']:
            return None
        d = self._data[r['base']]
        return struct.unpack('<I', d[off:off+4])[0]

    def is_module(self, addr):
        return 0 <= (addr - self.module_base) < 0x2000000

    def mod_off(self, addr):
        return addr - self.module_base


def gather_buffers():
    dumps = mc._load_tagged_dumps()
    by_pid = defaultdict(list)
    for d in dumps:
        expected = ''.join(d.get('hero_cards', []))
        buf, ent = mc.find_buffer_in_dump(d['_bin_path'], d['regions'], expected)
        if buf and ent:
            hd = mc.extract_hand_data(ent)
            d['_buf'] = buf
            d['_cards'] = hd['hero_cards']
            by_pid[d['pid']].append(d)
    return by_pid


def pick_pair(ds):
    """Pick 2 dumps with different buffer addresses, preferring 1-candidate dumps."""
    # Group by buffer address
    by_buf = defaultdict(list)
    for d in ds:
        by_buf[d['_buf']].append(d)
    if len(by_buf) < 2:
        return None, None
    # Pick two different buffer groups, take first dump from each
    bufs = sorted(by_buf.keys())
    return by_buf[bufs[0]][0], by_buf[bufs[-1]][0]


def scan_level(snap_a, snap_b, targets_a, targets_b, level):
    """Scan all memory in B for pointers to targets_b, cross-validate with A."""
    log(f"\n{'='*60}")
    log(f"LEVEL {level}: {len(targets_a)} target pair(s)")
    for i in range(min(3, len(targets_a))):
        log(f"  target[{i}]: A=0x{targets_a[i]:08X}  B=0x{targets_b[i]:08X}")
    log(f"{'='*60}")

    module_hits = []
    heap_pairs = []  # (addr, addr) — same address is target in both A and B for next level

    total_bytes = sum(r['size'] for r in snap_b.regions)
    scanned = 0
    cand_count = 0
    valid_count = 0
    t0 = time.time()

    for ri, region in enumerate(snap_b.regions):
        rbase = region['base']
        rsize = region['size']
        data = snap_b._data[rbase]

        # Progress every ~50MB
        if ri % 30 == 0 or scanned + rsize >= total_bytes:
            elapsed = time.time() - t0
            mb = scanned / 1048576
            log(f"  [{ri:4d}/{len(snap_b.regions)}] "
                f"0x{rbase:08X} ({mb:.0f}/{total_bytes/1048576:.0f} MB, "
                f"{elapsed:.0f}s) cand={cand_count} valid={valid_count}")

        scanned += rsize

        for j in range(0, len(data) - 3, ALIGN):
            val = struct.unpack('<I', data[j:j+4])[0]
            if val < MIN_PTR or val > MAX_PTR:
                continue

            for ti in range(len(targets_b)):
                diff = targets_b[ti] - val
                if diff < 0 or diff > MAX_OFFSET:
                    continue

                cand_count += 1
                ptr_addr = rbase + j
                offset = diff

                # Cross-validate: same address in A must hold (targets_a[ti] - offset)
                expected_a = targets_a[ti] - offset
                if expected_a < MIN_PTR:
                    continue
                actual_a = snap_a.read_u32(ptr_addr)
                if actual_a is None or actual_a != expected_a:
                    continue

                valid_count += 1
                is_mod = snap_b.is_module(ptr_addr)

                if is_mod:
                    mo = snap_b.mod_off(ptr_addr)
                    log(f"  ** MODULE module+0x{mo:07X} +0x{offset:X} "
                        f"(B: 0x{val:08X}, A: 0x{expected_a:08X})")
                    module_hits.append((mo, offset))
                else:
                    if len(heap_pairs) < 500:  # cap
                        heap_pairs.append(ptr_addr)
                break

    elapsed = time.time() - t0
    log(f"\n  Level {level} done: {elapsed:.0f}s, "
        f"candidates={cand_count}, validated={valid_count}, "
        f"module={len(module_hits)}, heap={len(heap_pairs)}")

    return module_hits, heap_pairs


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--pid', type=int)
    p.add_argument('--max-depth', type=int, default=4)
    args = p.parse_args()

    log("=== Pointer Scanner v2 ===")
    log(f"MAX_OFFSET=0x{MAX_OFFSET:X}, max_depth={args.max_depth}")

    log("\nFinding buffers in all dumps...")
    by_pid = gather_buffers()
    for pid, ds in by_pid.items():
        bufs = set(d['_buf'] for d in ds)
        log(f"  PID {pid}: {len(ds)} dumps, {len(bufs)} unique bufs, "
            f"module=0x{ds[0]['module_base']:X}")

    if args.pid:
        ds = by_pid.get(args.pid, [])
    else:
        best = max(by_pid, key=lambda p: len(set(d['_buf'] for d in by_pid[p])))
        ds = by_pid[best]
        log(f"\nAuto-selected PID {best}")

    a, b = pick_pair(ds)
    if not a or not b:
        log("Need 2 dumps with different buffer addresses"); return

    log(f"\nDump A: {a['dump_id']} buf=0x{a['_buf']:08X} cards={a['_cards']}")
    log(f"Dump B: {b['dump_id']} buf=0x{b['_buf']:08X} cards={b['_cards']}")
    log(f"Distance: 0x{abs(b['_buf']-a['_buf']):X}")

    log("\nLoading snapshots...")
    snap_a = DumpSnapshot(a, a['_buf'])
    snap_b = DumpSnapshot(b, b['_buf'])

    targets_a = [snap_a.buf_addr]
    targets_b = [snap_b.buf_addr]

    for level in range(1, args.max_depth + 1):
        if not targets_a:
            log("No targets remain."); break

        mod_hits, heap_addrs = scan_level(
            snap_a, snap_b, targets_a, targets_b, level)

        if mod_hits:
            log(f"\n*** FOUND {len(mod_hits)} STATIC POINTER(S)! ***")
            for mo, off in mod_hits:
                log(f"  module + 0x{mo:07X} + 0x{off:X} = target")
            break

        if not heap_addrs:
            log("No heap hits to follow. Chain not found at this depth.")
            break

        log(f"\n  {len(heap_addrs)} heap addresses become targets for level {level+1}")
        # Next level: find what points to these heap addresses
        # The heap address is the same in both dumps (stable allocation)
        targets_a = heap_addrs
        targets_b = heap_addrs

    log("\nDone.")


if __name__ == '__main__':
    main()
