import sys, numpy as np
from netCDF4 import Dataset
for f in sys.argv[1:]:
    d = Dataset(f); a = d['timer_strt'][:].astype(float); b = d['timer_stop'][:].astype(float); k = d['kind'][:]
    win = b[:, -1] - a[:, 0]
    get = ((b - a)[:, k == 2]).sum(1); put = ((b - a)[:, k == 1]).sum(1)
    # skip init: from first GET to last event
    # start after the first coupling exchange (its GET absorbs the other component's init)
    gi = np.where(k == 2)[0]; i0 = gi[0] + 1
    while i0 < len(k) and k[i0] == 2: i0 += 1
    t0 = b[:, i0 - 1]
    win2 = b[:, -1] - t0; get2 = ((b - a)[:, i0:][:, k[i0:] == 2]).sum(1)
    comp = win2 - get2 - ((b - a)[:, i0:][:, k[i0:] == 1]).sum(1)
    print(f"{f.split('/')[-1]:24s} ranks {a.shape[0]:5d}  window {win2.mean():7.1f}  GET wait mean {get2.mean():7.1f} (min {get2.min():6.1f} max {get2.max():6.1f})  compute mean {comp.mean():7.1f}")
