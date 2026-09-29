#!/bin/bash
#SBATCH --account=paleodyn.paleodyn
#SBATCH --partition=mpp
#SBATCH --qos=12h
#SBATCH --time=00:25:00
#SBATCH --exclusive
#SBATCH --ntasks-per-node=128
#SBATCH --output=bench_env_%j.out
source /albedo/work/projects/p_awiesm3_cmip7/runtime/awiesm3-v3.4/PICAL_ccnice/run_21200101-21291231/scripts/env.sh >/dev/null 2>&1
cd /albedo/home/jstreffi/esm_tools/albedo_performance_report/bench
echo "nodes: $SLURM_JOB_NODELIST"
run() { echo "=== $1"; shift; env "$@" srun --cpu-bind=cores ./mpibench_albedo | grep RESULT; }
run "default"                                   X=1
run "pml=ucx explicit"                          OMPI_MCA_pml=ucx
run "rc_x,sm,self"                              UCX_TLS=rc_x,sm,self
run "levante-like: dc_x,sm,self unified"        OMPI_MCA_pml=ucx OMPI_MCA_btl=self UCX_TLS=dc_x,sm,self UCX_UNIFIED_MODE=y
run "rc_x,sm,self + coll/han"                   UCX_TLS=rc_x,sm,self OMPI_MCA_coll_han_priority=100
run "dc_x,sm,self unified + coll/han"           OMPI_MCA_pml=ucx UCX_TLS=dc_x,sm,self UCX_UNIFIED_MODE=y OMPI_MCA_coll_han_priority=100
run "default + coll/han"                        OMPI_MCA_coll_han_priority=100
