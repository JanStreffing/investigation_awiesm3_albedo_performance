"""SYPD against node-hours per model year for all PICAL_cc (REcoM) layout tests of 2026-10-03.

    python plot_sypd_cost.py        reads results_20261003.txt, writes ../fig_recom_sypd_cost.png
"""
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rows = []
for line in open("results_20261003.txt"):
    p = line.split("|")
    if len(p) < 3 or line.startswith("test"):
        continue
    a = p[0].split()
    lay = dict(kv.split("=") for kv in p[2].split() if "=" in kv)
    rows.append(dict(name=a[0], nodes=int(a[1]), sypd=float(a[4]), nhy=float(a[5]),
                     nproc=int(lay["fesom_nproc"]), omp=int(lay["fesom_omp"]), rpn=int(lay["fesom_rpn"]),
                     groups=int(lay["fesom_groups"]), oifs=int(lay["oifs_nproc"]),
                     warm=bool(re.match(r"cc(R|P)\d", a[0]))))

# colour = FESOM ranks per group (ordered light to dark), marker = how the cores are used
ranks = [512, 768, 1024, 1792, 2688, 3584]
colour = dict(zip(ranks, ["#b9c4d0", "#8fa3b8", "#5f86ad", "#2f6ba3", "#c2571a", "#7a2e0e"]))
# hand-placed labels where points crowd; ccA and ccZ1 are named by the two call-outs, ccW sits under ccR4
NOLABEL = {"ccA", "ccW", "ccZ1"}
OFFSET = {"ccZ3": (-7, -11, "right"), "ccZ2": (-7, 6, "right"), "ccZ4": (4, 17, "left"), "ccV": (8, 1, "left"),
          "ccY": (-7, 6, "right"), "ccS": (7, -11, "left"), "ccX": (0, -14, "center"), "ccT": (-2, 9, "center"),
          "ccR5": (7, -12, "left"), "ccR4": (7, 3, "left"), "ccP1": (7, 4, "left"), "ccO": (0, -14, "center"), "ccN": (0, 9, "center"), "ccP": (0, -14, "center"),
          "ccC": (-7, -12, "right"), "ccD": (9, -9, "left"), "ccG1": (0, -14, "center"), "ccR3": (-7, 7, "right"),
          "ccL": (0, 10, "center"), "ccM": (7, -12, "left")}
fig, ax = plt.subplots(figsize=(11, 7.5))
for r in rows:
    kind = "groups" if r["groups"] > 1 else "omp" if r["omp"] > 1 else "plain"
    marker = {"plain": "o", "omp": "s", "groups": "^"}[kind]
    ax.scatter(r["nhy"], r["sypd"], s=230 if r["name"] == "ccZ4" else 95, marker=marker, color=colour[r["nproc"]],
               edgecolor="black" if r["warm"] else "white", linewidth=1.4 if r["warm"] else 0.8,
               zorder=2 if r["name"] == "ccZ4" else 3)
    if kind == "groups":
        lab = f"{r['groups']}x{r['nproc']} @{r['rpn']}"
    elif kind == "omp":
        lab = f"{r['nproc']}x{r['omp']} thr @{r['rpn']}"
    else:
        lab = f"@{r['rpn']}" if r["name"] != "ccZ4" else f"3584 ranks @{r['rpn']} (ring)"
    lab += f", {r['nodes']} n"
    if r["oifs"] != 384:
        lab += f", OIFS {r['oifs']}"
    if r["name"] in NOLABEL:
        continue
    dx, dy, ha = OFFSET.get(r["name"], (7, 3, "left"))
    ax.annotate(lab, (r["nhy"], r["sypd"]), xytext=(dx, dy), textcoords="offset points", fontsize=7,
                color="#333333", ha=ha)

prod = next(r for r in rows if r["name"] == "ccA")
rec = next(r for r in rows if r["name"] == "ccZ1")
ax.annotate("production now\n(768 ranks, 25 nodes)", (prod["nhy"], prod["sypd"]), xytext=(-10, -42),
            textcoords="offset points", fontsize=9, ha="center", arrowprops=dict(arrowstyle="-", color="#555555"))
ax.annotate("chosen for the continuation\n(2688 ranks @96, OIFS 192, 36 nodes)", (rec["nhy"], rec["sypd"]), xytext=(25.5, 55.5),
            textcoords="data", fontsize=9, ha="center", arrowprops=dict(arrowstyle="-", color="#555555"))

h = [plt.Line2D([], [], marker="o", ls="", color=colour[k], markersize=9, label=f"{k} FESOM ranks per group") for k in ranks]
h += [plt.Line2D([], [], marker="o", ls="", color="#888888", markersize=9, label="1 group, 1 thread"),
      plt.Line2D([], [], marker="s", ls="", color="#888888", markersize=9, label="OpenMP threads"),
      plt.Line2D([], [], marker="^", ls="", color="#888888", markersize=9, label="tracer groups"),
      plt.Line2D([], [], marker="o", ls="", color="#cccccc", markeredgecolor="black", markeredgewidth=1.4,
                 markersize=9, label="continuation from the 2145 restarts")]
ax.legend(handles=h, fontsize=8.5, loc="upper right", frameon=False, ncol=2)
ax.set_xlabel("cost: node-hours per model year (lower is cheaper)")
ax.set_ylabel("speed: simulated years per day")
ax.set_title("AWI-ESM3 with REcoM on albedo: speed against cost of every layout tested (one-month runs, 2026-10-03)\n"
             "labels: FESOM ranks per node (@), total nodes (n); OpenIFS is 384x4 unless noted", fontsize=10, loc="left")
ax.grid(alpha=0.25, zorder=0)
ax.set_xlim(13, 54)
ax.set_ylim(8, 66)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout()
out = "../fig_recom_sypd_cost.png"
fig.savefig(out, dpi=170)
print("wrote", out, len(rows), "tests")
