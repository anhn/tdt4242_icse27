"""RQ3: students' code-review reports vs. static analysis of the same code at review time
(Table "tool vs students").

Input : data/rq3_quality/tool_smells_review_time.csv, data/rq3_quality/student_reported_smells.csv
Output: results/tool_vs_students.csv
Agreement on presence per group (Cohen's kappa) and on counts (Spearman rho).
Weak Typing is compared for TypeScript repositories only.
"""
import sys
from pathlib import Path
import numpy as np
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_csv, write_csv
from standardise_student_smells import per_group

PAIRS = [  # (label in paper, tool column, student category)
    ("Duplicate code", "Duplicate Code", "Duplicate Code"),
    ("God component", "God Component", "God Component"),
    ("Long/complex method", "Long Method", "Long Method"),
    ("Repeated strings", "Magic Strings", "Magic Strings"),
    ("Dead code", "Dead Code", "Dead Code"),
    ("Error handling", "Error Handling", "Error Handling Smell"),
    ("Performance", "Performance Smell", "Performance Smell"),
    ("Weak typing", "Weak Typing", "Weak Typing"),
    ("Long parameter list", "Data Clumps", "Data Clumps"),
]


def kappa(a, b):
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return (po - pe) / (1 - pe) if pe < 1 else float('nan')


tool = {r["group"]: r for r in read_csv("rq3_quality/tool_smells_review_time.csv")}
stud = per_group()
rows = []
for label, tc, sc in PAIRS:
    gs = [g for g in tool if g in stud and (tc != "Weak Typing" or tool[g]["language"] == "ts")]
    t = np.array([float(tool[g][tc]) for g in gs]); s = np.array([stud[g].get(sc, 0) for g in gs])
    rho, p = stats.spearmanr(t, s)
    rows.append([label, len(gs), int((t > 0).sum()), int(t.sum()), int((s > 0).sum()), int(s.sum()),
                 int(((t > 0) & (s > 0)).sum()), int(((t > 0) & (s == 0)).sum()), int(((t == 0) & (s > 0)).sum()),
                 int(((t == 0) & (s == 0)).sum()), round(kappa(t > 0, s > 0), 3), round(rho, 3), round(p, 3)])
write_csv("tool_vs_students.csv", ["category", "groups_compared", "tool_groups", "tool_instances", "student_groups",
                                   "student_instances", "both", "tool_only", "students_only", "neither",
                                   "kappa_presence", "spearman_counts", "p"], rows)
for r in rows:
    print(f"{r[0]:22} n={r[1]:2}  tool {r[2]:2} ({r[3]:3})  students {r[4]:2} ({r[5]:3})  both {r[6]:2}  kappa {r[10]:+.2f}  rho {r[11]:+.2f}")
print("totals: tool groups", sum(r[2] for r in rows), "| student groups", sum(r[4] for r in rows), "| both", sum(r[6] for r in rows))
print("tool instances", sum(r[3] for r in rows), "| student instances", sum(r[5] for r in rows))
