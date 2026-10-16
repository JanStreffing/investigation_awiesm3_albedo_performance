"""Check that an OASIS set's feom order matches a FESOM partition: grids.nc feom.lon/lat vs nod2d.out in my_list order."""
import sys, glob
import numpy as np, netCDF4
I = "/albedo/work/projects/p_awiesm3_cmip7/jstreffi/input"
n, d = sys.argv[1], sys.argv[2]
nod = np.loadtxt(f"{I}/fesom2/core3/nod2d.out", skiprows=1, usecols=(1, 2))
order = []
for f in sorted(glob.glob(f"{I}/fesom2/core3/dist_{n}/my_list*.out")):
    t = open(f).read().split()
    my = int(t[1]); order += [int(x) for x in t[3:3 + my]]
order = np.array(order) - 1
assert order.size == nod.shape[0] and np.unique(order).size == order.size
g = netCDF4.Dataset(f"{d}/grids.nc")
lon = np.ravel(g["feom.lon"][:]); lat = np.ravel(g["feom.lat"][:])
dl = np.abs(((lon - nod[order, 0]) + 180) % 360 - 180); da = np.abs(lat - nod[order, 1])
print(f"dist_{n}: n>{0.01} deg lon {int((dl > 0.01).sum())} lat {int((da > 0.01).sum())}; max dlat {da.max():.4f}; n>1e-6: {int((da > 1e-6).sum())}")
