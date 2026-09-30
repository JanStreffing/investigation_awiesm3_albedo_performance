#!/bin/bash
#SBATCH --account=paleodyn.paleodyn
#SBATCH --partition=mpp
#SBATCH --qos=12h
#SBATCH --time=00:30:00
#SBATCH --exclusive
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=128
#SBATCH --output=bench_intranode_%j.out
source /albedo/work/projects/p_awiesm3_cmip7/jstreffi/runtime/awiesm3-v3.4/PICAL_ccnice/run_21200101-21291231/scripts/env.sh >/dev/null 2>&1
cd /albedo/home/jstreffi/esm_tools/albedo_performance_report/bench
echo "node: $SLURM_JOB_NODELIST"
for B in 2048 16384; do
for V in "default|X=1" "levante-like mm,knem,cma|UCX_TLS=mm,knem,cma,self" "posix only (no syscalls)|UCX_TLS=posix,self" "sysv only|UCX_TLS=sysv,self" "cma only|UCX_TLS=posix,cma,self UCX_RNDV_THRESH=intra:1024" "knem|UCX_TLS=posix,knem,self UCX_RNDV_THRESH=intra:1024" "no zero-copy (eager up to 256K)|UCX_RNDV_THRESH=intra:262144" "ob1+vader (no UCX)|OMPI_MCA_pml=ob1 OMPI_MCA_btl=self,vader"; do
  name=${V%%|*}; vars=${V#*|}; echo "=== ${B}B: $name"; env HALO_BYTES=$B $vars srun --cpu-bind=cores ./mpibench_albedo 2>&1 | grep -E "RESULT" | sed -E 's/triad.*//'
done; done
