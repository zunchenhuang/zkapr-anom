"""Scaling figure from results.json (and dscaling.json if present): fig_scaling.pdf.
Usage: python3 make_figure.py [results_dir]"""
import json, os, sys
from config import RESULTS

def plot(rows, out):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "#e6e6e6", "grid.linewidth": 0.6, "axes.axisbelow": True,
                         "legend.frameon": False, "pdf.fonttype": 42})
    C = {"Micro": "#D9822B", "SV": "#3B6EA8", "IC": "#2E7D4F"}
    ds_path = os.path.join(out, "dscaling.json")
    npan = 3 if os.path.exists(ds_path) else 2
    fig, ax = plt.subplots(1, npan, figsize=(7.0, 2.25))
    for key, lab in (("Micro", "hand-written"), ("SV", "SV-COMP"), ("IC", "IntroClass")):
        g = [x for x in rows if x["set"] == key]
        ax[0].scatter([x["hint_steps"] * x["Q"] / 1e3 for x in g], [x["r1cs"] / 1e3 for x in g], s=22, color=C[key], label=lab, zorder=3)
    xs = [x["hint_steps"] * x["Q"] / 1e3 for x in rows]; ys = [x["r1cs"] / 1e3 for x in rows]
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n; den = sum((a - mx) ** 2 for a in xs)
    if n > 1 and den > 0:
        k = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / den
        ax[0].plot([0, max(xs) * 1.05], [my - k * mx, my + k * (max(xs) * 1.05 - mx)], color="#888888", lw=0.8, ls="--", zorder=2)
    ax[0].set_xlabel("hint steps $\\times$ lemma width (thousands)"); ax[0].set_ylabel("constraints (thousands)")
    ax[0].set_title("(a) circuit size", loc="left", fontsize=8); ax[0].legend(loc="upper left")
    allr = sorted(rows, key=lambda x: x["r1cs"])
    for key, lab, mk, col in (("t_setup", "setup (customer)", "s", "#7A7A7A"), ("t_crscheck", "CRS check (vendor)", "^", "#B5462F"),
                              ("t_prove", "proving (vendor)", "o", "#2E7D4F")):
        ax[1].plot([x["r1cs"] / 1e3 for x in allr], [x[key] or 0 for x in allr], marker=mk, ms=3.5, lw=0.8, color=col, label=lab)
    ax[1].set_xscale("log"); ax[1].set_yscale("log"); ax[1].set_ylim(0.5, 20000)
    ax[1].set_xlabel("constraints (thousands, log scale)"); ax[1].set_ylabel("seconds (log scale)")
    ax[1].set_title("(b) one-time cost", loc="left", fontsize=8); ax[1].legend(loc="upper left", fontsize=7)
    if npan == 3:
        ds = json.load(open(ds_path))
        for (bname, pts), col, mk in zip(ds.items(), ("#3B6EA8", "#6B6B6B"), ("o", "s")):
            ax[2].plot([p["D"] for p in pts], [p["hint_steps"] for p in pts], marker=mk, ms=3.5, lw=0.9, color=col, label=bname)
        ax[2].set_xlabel("bound $D$"); ax[2].set_ylabel("hint steps"); ax[2].legend(loc="upper left")
        ax[2].set_title("(c) effect of the bound", loc="left", fontsize=8)
    plt.tight_layout(pad=0.4, w_pad=1.2); plt.savefig(os.path.join(out, "fig_scaling.pdf"))

if __name__ == "__main__":
    rd = sys.argv[1] if len(sys.argv) > 1 else RESULTS
    rows = json.load(open(os.path.join(rd, "results.json")))
    ex = set(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bench", "descriptions.json"))).get("_paper_exclude", []))
    plot([x for x in rows if x["name"] not in ex], rd); print("fig_scaling.pdf written")
