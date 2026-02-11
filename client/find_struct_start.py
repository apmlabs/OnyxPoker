#!/usr/bin/env python3
"""
Find where the container structure actually starts.
Strategy: Take ONE dump, search for pointers to (container - N) for N in range.
"""

import os
import sys
import struct

DUMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server', 'uploads', 'memory_dumps'))

# Import from memory_calibrator
sys.path.insert(0, os.path.dirname(__file__))
from memory_calibrator import find_buffer_in_dump, _make_read_fns
import json

def find_pointers_to(data, target_addr):
    """Find all 4-byte aligned pointers to target_addr."""
    target_bytes = struct.pack('<I', target_addr)
    hits = []
    for i in range(0, len(data) - 4, 4):
        if data[i:i+4] == target_bytes:
            hits.append(i)
    return hits

def analyze_one_dump(dump_path, meta_path):
    """Deep analysis of one dump to find structure start.
    
    Key insight: C++ has no GC - pointer MUST exist somewhere:
    1. Stack memory (function local variables)
    2. Module .data/.bss sections (global/static variables)
    3. Another heap object (member variable)
    """
    
    with open(meta_path) as f:
        meta = json.load(f)
    
    regions = meta['regions']
    module_base = meta.get('module_base', 0)
    
    # Find container
    buf_addr, entries = find_buffer_in_dump(dump_path, regions)
    if not buf_addr or not hasattr(find_buffer_in_dump, '_last_container_addr'):
        print("Container not found")
        return
    
    container_addr = find_buffer_in_dump._last_container_addr
    print(f"Container found at: 0x{container_addr:08X}")
    print(f"Module base: 0x{module_base:08X}")
    
    # Categorize memory regions
    stack_regions = []
    module_regions = []
    heap_regions = []
    
    for r in regions:
        base = r['base']
        size = r['size']
        if base >= 0x00C00000 and base < 0x08000000:
            module_regions.append(r)
        elif base >= 0x08000000 and base < 0x30000000:
            heap_regions.append(r)
        else:
            stack_regions.append(r)  # Stack is typically high addresses
    
    print(f"\nMemory layout:")
    print(f"  Module regions: {len(module_regions)} ({sum(r['size'] for r in module_regions)//1024//1024}MB)")
    print(f"  Heap regions: {len(heap_regions)} ({sum(r['size'] for r in heap_regions)//1024//1024}MB)")
    print(f"  Stack/other regions: {len(stack_regions)} ({sum(r['size'] for r in stack_regions)//1024//1024}MB)")
    
    # Load full dump
    print(f"\nLoading dump ({os.path.getsize(dump_path)//1024//1024}MB)...")
    with open(dump_path, 'rb') as f:
        data = f.read()
    
    print(f"Loaded {len(data)//1024//1024}MB")
    
    # Search ALL memory (module, heap, stack) for pointers to container-N
    print("\n=== SEARCHING ALL MEMORY for pointers ===")
    print("Range: container-8KB to container (structure must start BEFORE)")
    all_results = []
    
    checked = 0
    total = 2048  # 8KB / 4 bytes
    
    for offset in range(-8192, 4, 4):  # ONLY negative offsets
        checked += 1
        if checked % 400 == 0:
            print(f"  Progress: {checked}/{total} offsets...")
        
        target = container_addr + offset
        if target < 0:
            continue
        
        target_bytes = struct.pack('<I', target)
        
        # Search in ALL regions (don't categorize yet)
        for r in regions:
            region_data = data[r['file_offset']:r['file_offset']+r['size']]
            idx = 0
            while True:
                idx = region_data.find(target_bytes, idx)
                if idx == -1:
                    break
                if idx % 4 == 0:
                    abs_addr = r['base'] + idx
                    
                    # Categorize
                    if abs_addr < 0x08000000:
                        region_type = 'MODULE'
                    elif 0x08000000 <= abs_addr < 0x30000000:
                        region_type = 'HEAP'
                    else:
                        region_type = 'STACK'
                    
                    all_results.append((offset, abs_addr, region_type))
                    print(f"  container{offset:+5d}: FOUND at 0x{abs_addr:08X} [{region_type}]")
                idx += 4
    
    print(f"  Progress: {total}/{total} offsets checked.")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY:")
    print(f"  Total pointers found: {len(all_results)}")
    
    module_ptrs = [r for r in all_results if r[2] == 'MODULE']
    heap_ptrs = [r for r in all_results if r[2] == 'HEAP']
    stack_ptrs = [r for r in all_results if r[2] == 'STACK']
    
    print(f"  Module: {len(module_ptrs)}")
    print(f"  Heap: {len(heap_ptrs)}")
    print(f"  Stack: {len(stack_ptrs)}")
    
    if module_ptrs:
        print("\n✅ FOUND MODULE POINTERS (most stable):")
        for offset, addr, _ in module_ptrs[:10]:
            print(f"    container{offset:+d} at 0x{addr:08X} (module+0x{addr-module_base:X})")
        return {'type': 'module', 'results': module_ptrs}
    
    if heap_ptrs:
        print("\n✅ FOUND HEAP POINTERS:")
        for offset, addr, _ in heap_ptrs[:10]:
            print(f"    container{offset:+d} at 0x{addr:08X}")
        return {'type': 'heap', 'results': heap_ptrs}
    
    if stack_ptrs:
        print("\n✅ FOUND STACK POINTERS (transient):")
        for offset, addr, _ in stack_ptrs[:10]:
            print(f"    container{offset:+d} at 0x{addr:08X}")
        return {'type': 'stack', 'results': stack_ptrs}
    
    print("\n❌ NO POINTERS FOUND")
    return None

if __name__ == '__main__':
    # Pick first dump
    dumps = []
    for fname in sorted(os.listdir(DUMP_DIR)):
        if fname.endswith('.json'):
            json_path = os.path.join(DUMP_DIR, fname)
            bin_path = json_path.replace('.json', '.bin')
            if os.path.exists(bin_path):
                with open(json_path) as f:
                    meta = json.load(f)
                if meta.get('hero_cards'):
                    dumps.append((bin_path, json_path))
    
    if not dumps:
        print("No dumps found")
        sys.exit(1)
    
    print(f"Analyzing first dump: {os.path.basename(dumps[0][0])}\n")
    result = analyze_one_dump(dumps[0][0], dumps[0][1])
    
    if result and len(dumps) > 1:
        print(f"\n{'='*60}")
        print("VERIFICATION: Checking offset on other dumps...")
        offset = result['offset']
        
        for bin_path, json_path in dumps[1:4]:  # Check next 3 dumps
            dump_name = os.path.basename(bin_path).replace('.bin', '')
            with open(json_path) as f:
                meta = json.load(f)
            
            buf_addr, entries = find_buffer_in_dump(bin_path, meta['regions'])
            if not buf_addr or not hasattr(find_buffer_in_dump, '_last_container_addr'):
                continue
            
            container_addr = find_buffer_in_dump._last_container_addr
            target = container_addr + offset
            
            with open(bin_path, 'rb') as f:
                data = f.read()
            
            hits = find_pointers_to(data, target)
            module_hits = [h for h in hits if h < 0x08000000]
            
            print(f"  {dump_name}: container{offset:+d} = {len(hits)} pointers (module={len(module_hits)})")
