"""RQ1: paired comparison of human vs. AI stakeholder interviews (Table 3).

Input : data/rq1_interviews/interview_metrics.csv  (one row per group, *_Human / *_AI columns)
Output: results/rq1_wilcoxon.csv
Wilcoxon signed-rank test on AI - human differences (zero differences dropped),
matched-pairs rank-biserial r (+ = higher with the AI stakeholder), BH-FDR over 13 measures.
"""
import sys, re
from pathlib import Path
import numpy as np
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import read_csv, write_csv, bh

NAMES = {"M0": "Interviewer turns", "M1": "Stakeholder turns", "M2": "Interviewer questions",
         "M3": "Total words", "M4": "Interviewer words", "M5": "Stakeholder words",
         "M6": "Talk ratio", "M7": "Follow-up questions", "M8": "Clarification questions",
         "M9": "Vendi Score", "M10": "Mean semantic distance", "M11": "Topic coverage (%)",
         "M12": "Info gain / response"}


def num(x):
    m = re.search(r"=\s*([\d.]+)%", x)          # "3/5 = 60.0%" -> 60.0
    return float(m.group(1)) if m else float(x)


rows = read_csv("rq1_interviews/interview_metrics.csv")
out = []
for m, name in NAMES.items():
    h = np.array([num(r[f"{m}_Human"]) for r in rows])
    a = np.array([num(r[f"{m}_AI"]) for r in rows])
    d = a - h
    nz = d[d != 0]
    W, p = stats.wilcoxon(a, h)
    ranks = stats.rankdata(np.abs(nz))
    r = (ranks[nz > 0].sum() - ranks[nz < 0].sum()) / ranks.sum()
    out.append([m, name, len(rows), np.median(h), np.median(a), h.min(), h.max(), a.min(), a.max(),
                int((d > 0).sum()), int((d == 0).sum()), W, p, r])
q = bh([o[12] for o in out])
write_csv("rq1_wilcoxon.csv",
          ["id", "measure", "n_groups", "median_human", "median_ai", "min_human", "max_human",
           "min_ai", "max_ai", "groups_ai_higher", "ties", "W", "p", "r_rank_biserial", "q_fdr"],
          [o + [qq] for o, qq in zip(out, q)])
for o, qq in zip(out, q):
    print(f"{o[1]:26} human {o[3]:8.3f}  AI {o[4]:8.3f}  r={o[13]:+.2f}  p={o[12]:.4f}  q={qq:.4f}  AI higher in {o[9]}/{o[2]}")
