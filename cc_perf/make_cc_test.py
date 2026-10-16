"""Make a 1-month performance test runscript from the PICAL_cc production runscript.

    python make_cc_test.py NAME [key=value ...]

keys (defaults = production): fesom_nproc=768 fesom_omp=1 fesom_rpn=96 fesom_groups=1
                              oifs_nproc=384 oifs_omp=4 oasis_dir=<production set>
                              xios_rpn=2 xios_into=oifs rnfmap_into=oifs lpjg_into= lpjg_rpn= lpjg_omp=8
fesom_rpn=0 drops ranks_per_node (ranks packed one per omp block).
Writes runscripts/awiesm3/develop/awiesm3-develop-cc-albedo-TCO95L91-CORE3_TEST_<NAME>.yaml
"""
import sys

SRC = "/albedo/home/jstreffi/esm_tools/runscripts/awiesm3/develop/awiesm3-develop-cc-albedo-TCO95L91-CORE3_PICAL_cc.yaml"
name = sys.argv[1]
p = dict(fesom_nproc="768", fesom_omp="1", fesom_rpn="96", fesom_groups="1", oifs_nproc="384", oifs_omp="4",
         oasis_dir="/albedo/work/projects/p_awiesm3_cmip7/jstreffi/input/oasis_ini/cc_from_gmhemi1800_2139/",
         xios_rpn="2", xios_into="oifs", rnfmap_into="oifs", lpjg_into="", lpjg_rpn="", lpjg_omp="8", fesom_bin="")
for a in sys.argv[2:]:
    k, v = a.split("=", 1)
    assert k in p, k
    p[k] = v
s = open(SRC).read()


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('    account: "clidyn.clidyn"\n', '    account: "paleodyn.paleodyn"\n')
i = s.index('    compute_time: "10:00:00"'); j = s.index("\n", i)
s = s[:i] + '    compute_time: "00:30:00"' + s[j:]
i = s.index('    final_date: "2145-01-01"'); j = s.index("\n", i)
s = s[:i] + '    final_date: "2140-02-01"   # one month' + s[j:]
rep("    nmonth: 0\n", "    nmonth: 1\n")
i = s.index("    nyear: 5"); j = s.index("\n", i)
s = s[:i] + "    nyear: 0" + s[j:]
rep("    use_venv: True\n", "    use_venv: False   # test: local esm_tools checkout\n")
rep("    restart_rate: 5\n    restart_unit: 'y'\n    restart_first: 5\n", "    restart_rate: 1\n    restart_unit: 'm'\n    restart_first: 1\n")
rep("    use_lucia: false\n", "    use_lucia: true\n")
fes = f"    nproc: {p['fesom_nproc']}\n    omp_num_threads: {p['fesom_omp']}\n"
if p["fesom_rpn"] != "0":
    fes += f"    ranks_per_node: {p['fesom_rpn']}\n"
if p["fesom_groups"] != "1":
    fes += f"    mpi_num_groups: {p['fesom_groups']}\n"
rep("    nproc: 768\n    omp_num_threads: 1\n    ranks_per_node: 96\n", fes)
if p["fesom_groups"] != "1":
    rep("    add_namelist_changes:\n        namelist.oce:\n            oce_dyn:\n                mix_scheme: 'cvmix_TKE+cvmix_IDEMIX'\n",
        "    add_namelist_changes:\n        namelist.config:\n            run_config:\n"
        f"                num_fesom_groups: {p['fesom_groups']}\n"
        "        namelist.oce:\n            oce_dyn:\n                mix_scheme: 'cvmix_TKE+cvmix_IDEMIX'\n")
rep("    nproc: 384\n    omp_num_threads: 4\n", f"    nproc: {p['oifs_nproc']}\n    omp_num_threads: {p['oifs_omp']}\n")
rep('    ini_restart_dir: "/albedo/work/projects/p_awiesm3_cmip7/jstreffi/input/oasis_ini/cc_from_gmhemi1800_2139/"\n',
    f'    ini_restart_dir: "{p["oasis_dir"]}"\n')
rep("    omp_num_threads: 4\n    interleave_into: [oifs]\n    ranks_per_node: 2\n",
    f"    omp_num_threads: 4\n    interleave_into: [{p['xios_into']}]\n    ranks_per_node: {p['xios_rpn']}\n")
rep("rnfmap:\n    omp_num_threads: 4\n    interleave_into: [oifs]\n",
    f"rnfmap:\n    omp_num_threads: 4\n    interleave_into: [{p['rnfmap_into']}]\n")
if p["lpjg_omp"] != "8":
    rep("    nproc: 64\n    omp_num_threads: 8\n", f"    nproc: 64\n    omp_num_threads: {p['lpjg_omp']}\n")
if p["lpjg_into"]:
    rep(f"    nproc: 64\n    omp_num_threads: {p['lpjg_omp']}\n",
        f"    nproc: 64\n    omp_num_threads: {p['lpjg_omp']}\n    interleave_into: [{p['lpjg_into']}]\n    ranks_per_node: {p['lpjg_rpn']}\n")
if p["fesom_bin"]:
    rep("/albedo/work/user/jstreffi/model_codes/awiesm3-develop-cc/fesom-bin/ccgmhemi_90074f13/", p["fesom_bin"], 2)
hdr = (f"# TEST_{name}: 1-month performance test of PICAL_cc (REcoM on), "
       + " ".join(f"{k}={v}" for k, v in p.items() if k not in ("oasis_dir", "fesom_bin")) + ". THROWAWAY.\n")
out = SRC.replace("PICAL_cc.yaml", f"TEST_{name}.yaml")
open(out, "w").write(hdr + s)
print(out)
