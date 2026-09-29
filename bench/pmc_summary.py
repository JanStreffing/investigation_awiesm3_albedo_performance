"""Summarise bin/pmcmon.sh counter windows (pmc_<host>.txt in a run's work dir).

    python3 pmc_summary.py WORKDIR [WORKDIR ...]

Per component (fesom, OpenIFS): ranks seen, threads per rank, CPU busy (task time per
rank / window), clock while running (cycles / task time), IPC, demand DRAM fills per
rank, prefetch fills from DRAM per rank (newer 9-column files), and all of it per node
(64 B per line; write-backs are not counted).
"""
import glob
import os
import sys
from collections import defaultdict

WINDOW = 30.0

for work in sys.argv[1:]:
    rows = defaultdict(list)
    node_bytes = defaultdict(lambda: defaultdict(float))
    steps = []
    for f in sorted(glob.glob(os.path.join(work, "pmc_*.txt"))):
        host = os.path.basename(f)[4:-4]
        for line in open(f):
            if line.startswith("# host"):
                steps.append(int(line.split()[4]))
            if line.startswith("#") or not line.strip():
                continue
            p = line.split()
            if len(p) not in (7, 9) or p[1] not in ("fesom", "OpenIFS"):
                continue
            comm = p[1]
            nthr, task, cyc, ins, dram = int(p[2]), float(p[3]), float(p[4]), float(p[5]), float(p[6])
            # 9 columns: + L1D prefetch fills from DRAM, L2 prefetches missing L2 and L3
            pf = float(p[7]) + float(p[8]) if len(p) == 9 else float("nan")
            rows[comm].append((nthr, task, cyc, ins, dram, pf))
            node_bytes[comm][host] += (dram + (0 if pf != pf else pf)) * 64
    name = work.rstrip("/").split("/")[-3]
    print(f"== {name}  ({len(steps)} nodes, window after OIFS step {min(steps) if steps else '?'}-{max(steps) if steps else '?'})")
    for comm, r in rows.items():
        n = len(r)
        task = sum(x[1] for x in r)
        cyc = sum(x[2] for x in r)
        ins = sum(x[3] for x in r)
        dram = sum(x[4] for x in r)
        pf = sum(x[5] for x in r)
        nb = node_bytes[comm]
        print(
            f"  {comm:8s} ranks {n:4d}  threads/rank {sum(x[0] for x in r)/n:5.1f}  "
            f"busy cores/rank {task/n/WINDOW:4.2f}  GHz {cyc/task/1e9 if task else 0:4.2f}  "
            f"IPC {ins/cyc if cyc else 0:4.2f}  demand DRAM/rank {dram*64/n/WINDOW/1e9:5.2f} GB/s  "
            f"prefetch DRAM/rank {pf*64/n/WINDOW/1e9:5.2f} GB/s  "
            f"total DRAM/node {sum(nb.values())/len(nb)/WINDOW/1e9:6.1f} GB/s on {len(nb)} nodes"
        )
