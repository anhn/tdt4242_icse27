"""RQ3: summary statistics of the final code reported in the paper.
Input: data/rq3_quality/static_metrics_final_code.csv
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import read_csv

M = read_csv("rq3_quality/static_metrics_final_code.csv")
f = lambda k: np.array([float(r[k]) for r in M])
F = f("functions").sum()
print(f"repositories: {len(M)}")
print(f"median KLOC: {np.median(f('kloc')):.2f} (range {f('kloc').min()}-{f('kloc').max()})")
print(f"median duplication: {np.median(f('dup_pct')):.2f}% (range {f('dup_pct').min()}-{f('dup_pct').max()})")
print(f"functions > 50 lines: {100*f('long_funcs').sum()/F:.1f}% of {F:.0f}")
print(f"functions with CCN > 10: {100*f('complex_funcs').sum()/F:.1f}%")
print(f"files > 300 lines: {f('large_files').sum():.0f} in {(f('large_files')>0).sum()} repositories")
print(f"repositories with tests: {(f('test_loc')>0).sum()}")
