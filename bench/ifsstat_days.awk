# Seconds per model day from an OpenIFS ifs.stat (24 steps per day at the 3600 s step):
# awk -f ifsstat_days.awk work/ifs.stat  -> one number per model day. Day 1 includes the cold start,
# the last day includes restart writing; steady state = mean of days 2 to N-1.
$3=="STEPO"{split($1,a,":");t=a[1]*3600+a[2]*60+a[3]; if(t<lt)d+=86400; lt=t; t+=d; if(!init){init=1;n0=$4}; n=$4-n0; if(n%24==0){day=n/24; T[day]=t; if(day>mx)mx=day}} END{for(i=1;i<=mx;i++) printf "%d ", T[i]-T[i-1]; print ""}
