#!/bin/bash
# Reorder the PICAL_cc OASIS start set (FESOM dist_768 order) to other CORE3 partitions.
#   bash reorder_cc.sh 384 512 1024 1792
# grids/masks/areas and the CO2 restarts are not globbed by the tool: pass them as rmp_zz_*.nc.
set -euo pipefail
I=/albedo/work/projects/p_awiesm3_cmip7/jstreffi/input
SRC=$I/oasis_ini/cc_from_gmhemi1800_2139
TOOL=/albedo/work/user/jstreffi/software/oasis_reorder_tool
module load intel-oneapi-compilers/2022.1.0 openmpi/4.1.6-intel2021.6.0 2>/dev/null
module load $(module -t avail 2>&1 | grep -m1 '^netcdf-fortran/4.6.1') 2>/dev/null || true
for N in "$@"; do
    IN=$I/oasis_ini/cc_tmp_in_$N; OUT=$I/oasis_ini/cc_from_gmhemi1800_2139_dist$N
    rm -rf $IN; mkdir -p $IN $OUT
    for f in rmp_A096_to_feom_BICUBIC rmp_A096_to_feom_GAUSWGT_25 rmp_feom_to_A096_GAUSWGT_25 rmp_R096_to_RnfA_GAUSWGT_25 \
             rmp_RnfO_to_feom_GAUSWGT_25 rstas rstos vegin; do cp -L $SRC/$f.nc $IN/$f.nc; done
    for f in grids masks areas rst_co2_ao rst_co2_av; do cp -L $SRC/$f.nc $IN/rmp_zz_$f.nc; done
    ( ulimit -s unlimited; OMP_NUM_THREADS=4 srun -A paleodyn.p_paleo_compute -p smp --qos=30min -n 13 -c 4 -t 10 \
        $TOOL/reorder_oasis $I/fesom2/core3/dist_768 $I/fesom2/core3/dist_$N $IN $OUT ) > $I/oasis_ini/reorder_cc_$N.log 2>&1
    for f in grids masks areas rst_co2_ao rst_co2_av; do mv $OUT/rmp_zz_$f.nc $OUT/$f.nc; done
    rm -rf $IN
    echo "dist_$N: $(ls $OUT | wc -l) files, from the dist_768 set $SRC" | tee $OUT/README.txt
done
