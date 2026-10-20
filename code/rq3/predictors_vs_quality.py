"""RQ3: do prompting strategies, prompt styles, or experience explain code quality?
Three families of tests, each corrected with Benjamini-Hochberg FDR:

 A  recoded strategies (used by 3..n-3 groups)  vs. final-code metrics and student-reported smells
 B  tick-box prompt styles                       vs. student-reported smells (Mann-Whitney / Fisher exact)
 C  recoded strategies, prompt styles, strategy counts, experience and scepticism
                                                 vs. tool-detected smells at review time (per KLOC)

Mann-Whitney effect = rank-biserial r (+ = higher in groups using the strategy);
Fisher effect = odds ratio; Spearman effect = rho.
Output: results/predictors_A_strategies_final_code.csv, ..._B_styles_student_smells.csv,
        ..._C_tool_smells.csv
"""
import sys
from pathlib import Path
import numpy as np
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_csv, write_csv, bh, rank_biserial_mw
from standardise_student_smells import per_group

book = read_csv("rq2_strategies/strategy_codebook.csv")
NAME = {f"S{b['id']}": b["strategy"] for b in book}
GEN = [f"S{b['id']}" for b in book if b["type"] == "generation"]
CON = [f"S{b['id']}" for b in book if b["type"] == "consolidation"]
S = {r["group"]: {k: int(v) for k, v in r.items() if k != "group"} for r in read_csv("rq2_strategies/strategies_recoded.csv")}
TB = {r["group"]: {k: int(v) for k, v in r.items() if k != "group"} for r in read_csv("rq2_strategies/prompt_styles_tickbox.csv")}
M = {r["group"]: r for r in read_csv("rq3_quality/static_metrics_final_code.csv")}
T = {r["group"]: r for r in read_csv("rq3_quality/tool_smells_review_time.csv")}
H = {r["group"]: r for r in read_csv("rq4_reflections/experience_scepticism.csv")}
P = per_group()


def mw(a, b):
    U, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    return rank_biserial_mw(U, len(a), len(b)), p


def run_family(name, predictors, outcomes, groups):
    """predictors: list of (type, label, f(g)->0/1 or number, kind); outcomes: dict label -> f(g)->value or None"""
    rows = []
    for ptype, plabel, pf, kind in predictors:
        for olabel, of in outcomes.items():
            gs = [g for g in groups if of(g) is not None and pf(g) is not None]
            if kind == "binary":
                a = [of(g) for g in gs if pf(g) == 1]; b = [of(g) for g in gs if pf(g) == 0]
                if len(a) < 3 or len(b) < 3:
                    continue
                if olabel.startswith("reports "):
                    tab = [[sum(1 for x in a if x), sum(1 for x in a if not x)], [sum(1 for x in b if x), sum(1 for x in b if not x)]]
                    eff, p = stats.fisher_exact(tab)
                    desc = f"{tab[0][0]}/{len(a)} vs {tab[1][0]}/{len(b)}"
                else:
                    eff, p = mw(a, b); desc = f"{np.median(a):.2f} vs {np.median(b):.2f}"
                rows.append([ptype, plabel, olabel, f"{len(a)}/{len(b)}", desc, eff, p])
            else:
                rho, p = stats.spearmanr([pf(g) for g in gs], [of(g) for g in gs])
                rows.append([ptype, plabel, olabel, f"n={len(gs)}", "", rho, p])
    q = bh([r[-1] for r in rows])
    write_csv(name, ["predictor_type", "predictor", "outcome", "n_with/without", "medians_or_counts", "effect", "p", "q_fdr"],
              [r + [qq] for r, qq in zip(rows, q)])
    print(f"{name}: {len(rows)} tests, p<.05: {sum(r[-1] < .05 for r in rows)}, min q = {q.min():.2f}")
    for r, qq in sorted(zip(rows, q), key=lambda x: x[0][-1])[:3]:
        print(f"    {r[1][:30]:30} {r[2][:28]:28} effect={r[5]:+.2f} p={r[6]:.3f} q={qq:.2f}")
    return rows


def varying(groups, table, keys):
    return [k for k in keys if 3 <= sum(table[g][k] for g in groups if g in table) <= len([g for g in groups if g in table]) - 3]


# ---- A: recoded strategies vs final-code metrics and student-reported smells (22 groups)
gA = sorted(S, key=int)
fm = lambda k: (lambda g: float(M[g][k]) if g in M else None)
outA = {"student smells": lambda g: sum(P[g].values()) if g in P else None,
        "student smells / KLOC": lambda g: sum(P[g].values()) / float(M[g]["kloc"]) if g in P and g in M else None,
        "duplication %": fm("dup_pct"),
        "long functions / KLOC": lambda g: float(M[g]["long_funcs"]) / float(M[g]["kloc"]) if g in M else None,
        "complex functions / KLOC": lambda g: float(M[g]["complex_funcs"]) / float(M[g]["kloc"]) if g in M else None,
        "files > 300 lines": fm("large_files"), "test / code ratio": fm("test_ratio")}
predA = [("Recoded strategy", NAME[k], (lambda g, k=k: S[g][k]), "binary")
         for k in NAME if 3 <= sum(S[g][k] for g in gA) <= len(gA) - 3]
run_family("predictors_A_strategies_final_code.csv", predA, outA, gA)

# ---- B: tick-box prompt styles vs student-reported smells (groups with both)
gB = sorted([g for g in TB if g in P], key=int)
top = sorted({c for g in gB for c in P[g]}, key=lambda c: -sum(1 for g in gB if P[g].get(c, 0) > 0))
top = top[:9]   # the nine categories reported by most groups
outB = {"total smells": lambda g: sum(P[g].values()), "distinct smell types": lambda g: len(P[g])}
outB.update({f"reports {c}": (lambda g, c=c: P[g].get(c, 0) > 0) for c in top})
styles = list(next(iter(TB.values())))
predB = [("Prompt style", s, (lambda g, s=s: TB[g][s]), "binary") for s in varying(gB, TB, styles)]
run_family("predictors_B_styles_student_smells.csv", predB, outB, gB)

# ---- C: everything vs tool-detected smells at review time (17 groups)
gC = sorted(T, key=int)
CATS = ["Duplicate Code", "God Component", "Long Method", "Magic Strings", "Dead Code", "Error Handling",
        "Performance Smell", "Data Clumps"]
k = lambda g: float(T[g]["kloc"])
outC = {"total smells / KLOC": lambda g: sum(float(T[g][c]) for c in CATS + ["Weak Typing"]) / k(g),
        "duplication %": lambda g: float(T[g]["dup_pct"])}
outC.update({f"{c} / KLOC": (lambda g, c=c: float(T[g][c]) / k(g)) for c in CATS})
predC = [("Recoded strategy", NAME[s], (lambda g, s=s: S[g][s] if g in S else 0), "binary")
         for s in NAME if 3 <= sum(S[g][s] for g in gC if g in S) <= len(gC) - 3]
predC += [("Prompt style", s, (lambda g, s=s: TB.get(g, {}).get(s, 0)), "binary")
          for s in styles if 3 <= sum(TB.get(g, {}).get(s, 0) for g in gC) <= len(gC) - 3]
predC += [("Count", "# generation strategies", lambda g: sum(S[g][x] for x in GEN), "continuous"),
          ("Count", "# consolidation strategies", lambda g: sum(S[g][x] for x in CON), "continuous"),
          ("Rating", "web-development experience", lambda g: float(H[g]["webdev_experience_1to5"]) if g in H else None, "continuous"),
          ("Rating", "scepticism towards AI", lambda g: float(H[g]["scepticism_1to5"]) if g in H else None, "continuous")]
run_family("predictors_C_tool_smells.csv", predC, outC, gC)
