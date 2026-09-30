"""Figures for the 2026-09-29 rounds of the albedo performance report.

    python3 make_figs_20260929.py

fig_fesom_spread.png : FESOM compute per 2-month leg and core clock against FESOM ranks per node
fig_critical_path.png: OpenIFS and FESOM compute per coupling interval over a model day (TEST_best25)
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
RUN = "/albedo/work/projects/p_awiesm3_cmip7/jstreffi/runtime/awiesm3-v3.4"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})


def fig_spread():
    # LUCIA timeline computing time (s per 2-month leg) and hardware-counter clock.
    # Same FESOM build (53e095ec), 768 ranks, OpenIFS 384x4 in all runs.
    labels = ["64 per node\n1 thread\n(nolockB4)", "64 per node\n2 threads\n(nolockB1)",
              "96 per node\n1 thread\n(best25)", "128 per node\n1 thread\n(pmcP)"]
    compute = [135.2, 161.0, 154.6, 228.3]
    x_ghz = [0, 2, 3]
    ghz = [2.84, 2.55, 2.33]  # pmcS (= nolockB4 layout), fes96, pmcP
    ghz_labels = ["64 per node", "96 per node", "128 per node"]

    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={"width_ratios": [1.5, 1]})
    x = np.arange(len(compute))
    a.bar(x, compute, width=0.55, color=BLUE, edgecolor=SURFACE, linewidth=2)
    for xi, v in zip(x, compute):
        a.text(xi, v + 4, f"{v:.0f} s", ha="center", va="bottom", color=INK)
    a.set_xticks(x, labels)
    a.set_ylabel("FESOM computing per 2-month leg (s)")
    a.set_ylim(0, 260)
    a.yaxis.grid(True, color=GRID, linewidth=0.8)
    a.set_axisbelow(True)
    a.set_title("(a) FESOM compute, 768 ranks", loc="left", color=INK)

    xb = np.arange(len(ghz))
    b.bar(xb, ghz, width=0.5, color=BLUE, edgecolor=SURFACE, linewidth=2)
    for xi, v in zip(xb, ghz):
        b.text(xi, v + 0.04, f"{v:.2f}", ha="center", va="bottom", color=INK)
    b.set_xticks(xb, ghz_labels)
    b.set_ylabel("clock while running (GHz)")
    b.set_ylim(0, 3.2)
    b.axhline(2.0, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    b.text(0.5, 2.04, "base\n2.0 GHz", ha="center", va="bottom", color=INK2, fontsize=8)
    b.yaxis.grid(True, color=GRID, linewidth=0.8)
    b.set_axisbelow(True)
    b.set_title("(b) FESOM core clock, 1 thread", loc="left", color=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_fesom_spread.png"), dpi=200)


def fig_critical_path():
    sys.path.insert(0, HERE)
    src = open(os.path.join(HERE, "lucia_steps.py")).read().split("oc, ow = intervals")[0]
    ns = {}
    exec(src, ns)
    import glob
    work = glob.glob(f"{RUN}/TEST_best25/run_*/work")[0]
    oc, _ = ns["intervals"](f"{work}/timeline_OpenIFS.nc")
    fc, _ = ns["intervals"](f"{work}/timeline_fesom.nc")
    n = min(len(oc), len(fc))
    oc, fc = oc[:n], fc[:n]
    po = np.array([oc[p::24].mean() for p in range(24)]) * 1000
    pf = np.array([fc[p::24].mean() for p in range(24)]) * 1000

    fig, a = plt.subplots(figsize=(10, 3.6))
    h = np.arange(24)
    a.plot(h, po, color=BLUE, linewidth=2, marker="o", markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.5)
    a.plot(h, pf, color=ORANGE, linewidth=2, marker="o", markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.5)
    a.text(23.4, po[-1], "OpenIFS", color=INK, va="center")
    a.text(23.4, pf[-1] - 6, "FESOM\n(2 steps)", color=INK, va="center")
    a.set_xlim(-0.5, 25.5)
    a.set_xticks(range(0, 24, 3))
    a.set_xlabel("coupling interval within the model day (interval index mod 24, one per 3600 s OpenIFS step)")
    a.set_ylabel("computing per interval (ms)")
    a.set_ylim(0, max(po.max(), pf.max()) * 1.15)
    a.yaxis.grid(True, color=GRID, linewidth=0.8)
    a.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_critical_path.png"), dpi=200)
    return po, pf


if __name__ == "__main__":
    fig_spread()
    po, pf = fig_critical_path()
    print("OpenIFS ms per interval:", np.round(po).astype(int))
    print("FESOM   ms per interval:", np.round(pf).astype(int))
