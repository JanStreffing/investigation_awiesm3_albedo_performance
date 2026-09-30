#!/bin/bash
#SBATCH --account=paleodyn.paleodyn
#SBATCH --partition=mpp
#SBATCH --qos=12h
#SBATCH --time=00:20:00
#SBATCH --exclusive
#SBATCH --ntasks-per-node=128
#SBATCH --output=bench_albedo_%j_%N.out
source /albedo/work/projects/p_awiesm3_cmip7/jstreffi/runtime/awiesm3-v3.4/PICAL_ccnice/run_21200101-21291231/scripts/env.sh >/dev/null 2>&1
cd /albedo/home/jstreffi/esm_tools/albedo_performance_report/bench
N=$SLURM_JOB_NUM_NODES
echo "nodes: $SLURM_JOB_NODELIST  ($N)"; lscpu | grep -E "Model name|CPU max MHz|CPU min MHz"; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null
( for i in $(seq 1 128); do timeout 5 sh -c 'while :; do :; done' & done; sleep 3; echo "MHz under load: $(grep MHz /proc/cpuinfo | awk '{s+=$4;n++} END{printf "%.0f", s/n}')"; wait ) 2>/dev/null
echo "=== default UCX ==="; srun --cpu-bind=cores ./mpibench_albedo | grep -E "RESULT|CORE"
echo "=== UCX_TLS=rc_x,sm,self ==="; UCX_TLS=rc_x,sm,self srun --cpu-bind=cores ./mpibench_albedo | grep -E "RESULT|CORE"
echo "=== UCX_TLS=dc_x,sm,self ==="; UCX_TLS=dc_x,sm,self srun --cpu-bind=cores ./mpibench_albedo | grep -E "RESULT|CORE"
