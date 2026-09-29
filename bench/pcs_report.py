#!/usr/bin/env python3
"""Turn pcsampler output (<base>.samples, <base>.maps) into a per-library and per-routine profile.

usage: pcs_report.py <base> [top_n]
"""
import bisect
import collections
import os
import subprocess
import sys

base = sys.argv[1]
top = int(sys.argv[2]) if len(sys.argv) > 2 else 30
# optional wall-clock window (epoch seconds) to restrict samples to, e.g. the time-stepping phase
win = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else None

maps = []
for line in open(base + ".maps"):
    f = line.split()
    lo, hi = (int(x, 16) for x in f[0].split("-"))
    path = f[5] if len(f) > 5 else "[anon]"
    maps.append((lo, hi, int(f[2], 16), path))
maps.sort()
starts = [m[0] for m in maps]
load_base = {}
for lo, hi, off, path in maps:
    if path.startswith("/") and path not in load_base:
        load_base[path] = lo - off

samples = []
total = 0
t0, binsec = 0.0, 1
for line in open(base + ".samples"):
    if line.startswith("#"):
        f = line.split()
        if "t0" in f:
            t0 = float(f[f.index("t0") + 1]); binsec = int(f[f.index("binsec") + 1])
        continue
    f = line.split()
    a, c = f[0], f[1]
    if win and len(f) > 2:
        tb = t0 + int(f[2]) * binsec
        if tb < win[0] or tb + binsec > win[1]:
            continue
    samples.append((int(a, 16), int(c)))
    total += int(c)

_fv = {}


def first_vaddr(path):
    """Link-time vaddr of the first LOAD segment minus its file offset (0 for shared libs, 0x400000 for non-PIE)."""
    if path not in _fv:
        v = 0
        out = subprocess.run(["readelf", "-lW", path], capture_output=True, text=True).stdout
        for l in out.splitlines():
            f = l.split()
            if f and f[0] == "LOAD":
                v = int(f[2], 16) - int(f[1], 16)
                break
        _fv[path] = v
    return _fv[path]


by_lib = collections.Counter()
per_lib_addr = collections.defaultdict(list)
for pc, c in samples:
    i = bisect.bisect_right(starts, pc) - 1
    if i >= 0 and maps[i][0] <= pc < maps[i][1]:
        path = maps[i][3]
    else:
        path = "[unknown]"
    by_lib[path] += c
    if path in load_base:
        per_lib_addr[path].append((pc - load_base[path] + first_vaddr(path), c))

print(f"total samples: {total}" + (f" in window {win[1]-win[0]:.0f} s" if win else ""))
print("\n== by library")
for path, c in by_lib.most_common(15):
    print(f"{100.0 * c / total:6.1f} %  {c:8d}  {os.path.basename(path)}")


def symbols(path):
    out = subprocess.run(["nm", "-C", "--defined-only", path], capture_output=True, text=True).stdout
    if not out.strip():
        out = subprocess.run(["nm", "-C", "-D", "--defined-only", path], capture_output=True, text=True).stdout
    syms = []
    for l in out.splitlines():
        p = l.split(None, 2)
        if len(p) == 3 and p[1] in "tTwW":
            syms.append((int(p[0], 16), p[2]))
    syms.sort()
    return syms


by_sym = collections.Counter()
for path, lst in per_lib_addr.items():
    if by_lib[path] < 0.005 * total:
        continue
    syms = symbols(path)
    addrs = [s[0] for s in syms]
    lib = os.path.basename(path)
    for rel, c in lst:
        j = bisect.bisect_right(addrs, rel) - 1
        name = syms[j][1] if j >= 0 else "?"
        by_sym[(lib, name)] += c

print(f"\n== top {top} routines")
for (lib, name), c in by_sym.most_common(top):
    print(f"{100.0 * c / total:6.1f} %  {c:8d}  {lib:24s} {name[:90]}")
