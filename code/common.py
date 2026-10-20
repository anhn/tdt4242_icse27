"""Shared paths and helpers for the analysis scripts."""
from pathlib import Path
import csv
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


def read_csv(rel):
    with open(DATA / rel, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(name, header, rows):
    with open(RESULTS / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def bh(pvals):
    """Benjamini-Hochberg adjusted p-values (q-values)."""
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    q = np.empty(n)
    prev = 1.0
    for i in range(n - 1, -1, -1):
        k = order[i]
        prev = min(prev, p[k] * n / (i + 1))
        q[k] = prev
    return q


def rank_biserial_mw(U, n1, n2):
    """Rank-biserial r for Mann-Whitney U of group 1; + means group 1 tends to be higher."""
    return 2 * U / (n1 * n2) - 1
