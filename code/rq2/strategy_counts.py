"""RQ2: generation vs. consolidation strategies per group (Table 4, Section 5.2).

Input : data/rq2_strategies/strategies_recoded.csv, strategy_codebook.csv
Output: results/strategy_prevalence.csv, results/generation_consolidation_per_group.csv
"""
import sys
from pathlib import Path
import numpy as np
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import read_csv, write_csv

book = read_csv("rq2_strategies/strategy_codebook.csv")
S = read_csv("rq2_strategies/strategies_recoded.csv")
gen = [f"S{b['id']}" for b in book if b["type"] == "generation"]
con = [f"S{b['id']}" for b in book if b["type"] == "consolidation"]

write_csv("strategy_prevalence.csv", ["id", "strategy", "type", "groups_using", "of_groups"],
          [[b["id"], b["strategy"], b["type"], sum(int(r[f"S{b['id']}"]) for r in S), len(S)] for b in book])
per = [(r["group"], sum(int(r[k]) for k in gen), sum(int(r[k]) for k in con)) for r in S]
write_csv("generation_consolidation_per_group.csv", ["group", "generation", "consolidation"], per)
g = np.array([p[1] for p in per]); c = np.array([p[2] for p in per])
print(f"groups: {len(per)}")
print(f"generation   median {np.median(g)} (range {g.min()}-{g.max()})")
print(f"consolidation median {np.median(c)} (range {c.min()}-{c.max()})")
print(f"groups with more generation than consolidation: {(g > c).sum()}/{len(per)}")
print(f"groups with no consolidation strategy: {(c == 0).sum()}")
print("Wilcoxon generation vs consolidation:", stats.wilcoxon(g, c))
