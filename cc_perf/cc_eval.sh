#!/bin/bash
# One line per PICAL_cc performance test: bash cc_eval.sh ccA ccB ...
# s/day = mean of model days 2..N-1 from ifs.stat (day 1 = cold start, last day = restart writing).
RT=/albedo/work/projects/p_awiesm3_cmip7/jstreffi/runtime/awiesm3-v3.4
AWK=$(dirname "$0")/../bench/ifsstat_days.awk
printf "%-6s %5s %-10s %7s %6s %8s | %7s %7s %7s %7s %7s | %s\n" test nodes state s/day SYPD nodeh/y fes_tot tracer recom output ice layout
for t in "$@"; do
    R=$(ls -d $RT/TEST_$t/run_* 2>/dev/null | head -1); [ -z "$R" ] && continue
    L=$(ls $RT/TEST_$t/log/TEST_${t}_awiesm3_compute_2*.log 2>/dev/null | tail -1)
    nodes=$(cat $RT/TEST_$t/scripts/*compute*.run $R/scripts/*compute*.run 2>/dev/null | grep -m1 -- "--nodes=" | sed "s/.*=//")
    j=${L##*_}; j=${j%.log}
    st=$(sacct -j $j -X -n -o state 2>/dev/null | head -1 | tr -d ' ')
    days=$(awk -f $AWK $R/work/ifs.stat 2>/dev/null)
    spd=$(echo $days | awk '{n=0;s=0;for(i=2;i<NF;i++){s+=$i;n++}; if(n) printf "%.2f", s/n}')
    [ -z "$spd" ] && spd=0
    g() { grep -a -m1 "$1" $L | sed 's/.*: *//' | awk '{print $1}'; }
    ft=$(g "Runtime for all timesteps"); tr=$(g "runtime oce. tracer"); rc=$(g "runtime recom:"); ou=$(g "> runtime output"); ic=$(g "> runtime ice  ")
    lay=$(head -1 $R/scripts/*TEST_$t.yaml | sed 's/.*(REcoM on), //; s/ xios_into.*//')
    awk -v t=$t -v n=$nodes -v st=$st -v s=$spd -v ft="$ft" -v tr="$tr" -v rc="$rc" -v ou="$ou" -v ic="$ic" -v lay="$lay" 'BEGIN{
        sypd = s>0 ? 86400/(s*365.25) : 0; nh = s*365.25*n/3600;
        printf "%-6s %5d %-10s %7.2f %6.2f %8.1f | %7.1f %7.1f %7.1f %7.1f %7.1f | %s\n", t, n, st, s, sypd, nh, ft, tr, rc, ou, ic, lay}'
done
