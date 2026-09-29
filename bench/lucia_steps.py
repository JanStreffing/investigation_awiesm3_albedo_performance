"""Per-exchange balance from LUCIA timelines (2026-09-29).

    python3 lucia_steps.py timeline_OpenIFS.nc timeline_fesom.nc

Splits each rank's event list into coupling intervals (a block of consecutive GETs
starts an interval). Per interval and component: compute = time from the end of the
GET block to the start of the next GET block (rank mean; PUTs counted as compute),
wait = duration of the next GET block (rank mean). Skips the first interval (init).
Groups intervals by position within the OIFS step pattern (interval index mod 24).
"""
import sys
import numpy as np
from netCDF4 import Dataset


def intervals(f):
    d = Dataset(f)
    a = d['timer_strt'][:].astype(float); b = d['timer_stop'][:].astype(float); k = d['kind'][:]
    g = np.where(k == 2)[0]
    starts = [g[0]] + [g[i] for i in range(1, len(g)) if g[i] != g[i - 1] + 1]
    ends = []
    for s in starts:
        e = s
        while e + 1 < len(k) and k[e + 1] == 2:
            e += 1
        ends.append(e)
    comp, wait = [], []
    for j in range(len(starts) - 1):
        c = a[:, starts[j + 1]] - b[:, ends[j]]
        w = b[:, ends[j + 1]] - a[:, starts[j + 1]]
        comp.append(c.mean()); wait.append(w.mean())
    return np.array(comp[1:]), np.array(wait[1:])


oc, ow = intervals(sys.argv[1])
fc, fw = intervals(sys.argv[2])
n = min(len(oc), len(fc))
oc, ow, fc, fw = oc[:n], ow[:n], fc[:n], fw[:n]
print(f"intervals {n}: OIFS compute {oc.sum():.1f} wait {ow.sum():.1f} | FESOM compute {fc.sum():.1f} wait {fw.sum():.1f}")
print("pos  OIFS_comp  OIFS_wait  FESOM_comp  FESOM_wait   (mean s per interval, by interval index mod 24)")
for p in range(24):
    s = slice(p, n, 24)
    print(f"{p:3d}  {oc[s].mean():9.3f}  {ow[s].mean():9.3f}  {fc[s].mean():10.3f}  {fw[s].mean():10.3f}")
