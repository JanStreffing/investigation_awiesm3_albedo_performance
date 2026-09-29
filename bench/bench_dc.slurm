#!/bin/bash
#SBATCH --account=paleodyn.paleodyn
#SBATCH --partition=mpp
#SBATCH --qos=12h
#SBATCH --time=00:30:00
#SBATCH --exclusive
#SBATCH --nodes=16
#SBATCH --ntasks-per-node=128
#SBATCH --output=bench_dc_%j.out
source /albedo/work/projects/p_awiesm3_cmip7/runtime/awiesm3-v3.4/PICAL_ccnice/run_21200101-21291231/scripts/env.sh >/dev/null 2>&1
cd /albedo/home/jstreffi/esm_tools/albedo_performance_report/bench
echo "nodes: $SLURM_JOB_NODELIST"
for V in "default|X=1" "dc_x only|UCX_TLS=sm,self,dc_x" "dc_x NUM_DCI=16|UCX_TLS=sm,self,dc_x UCX_DC_MLX5_NUM_DCI=16" "dc_x NUM_DCI=32|UCX_TLS=sm,self,dc_x UCX_DC_MLX5_NUM_DCI=32" "dc_x NUM_DCI=64|UCX_TLS=sm,self,dc_x UCX_DC_MLX5_NUM_DCI=64" "dc_x tx=rand NUM_DCI=32|UCX_TLS=sm,self,dc_x UCX_DC_MLX5_NUM_DCI=32 UCX_DC_MLX5_TX_POLICY=rand" "dc_x unified NUM_DCI=32|UCX_TLS=sm,self,dc_x UCX_DC_MLX5_NUM_DCI=32 UCX_UNIFIED_MODE=y" "ud_x only|UCX_TLS=sm,self,ud_x" "rc_x reference|UCX_TLS=sm,self,rc_x"; do
  name=${V%%|*}; vars=${V#*|}
  for B in 2048 16384; do echo "=== ${B}B: $name"; env HALO_BYTES=$B $vars srun --cpu-bind=cores ./mpibench_albedo 2>&1 | grep -E "RESULT" | sed -E 's/triad.*//'; done
done
