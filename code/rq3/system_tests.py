"""RQ3: cross-group system testing summary (Table "system testing").
Requirements are counted once per report, outcomes per executed test.
Input : data/rq3_quality/system_tests.csv  (report ids R01..R22 replace the original file names)
Output: results/system_tests_per_report.csv
"""
import sys, re, statistics, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import read_csv, write_csv

norm = lambda r: re.sub(r"\(REQ\d+\)", "", re.sub(r"\s+", "", r.strip().upper()), flags=re.I)
split = lambda f: [norm(p) for p in re.split(r"[,;]+", f or "") if norm(p)]
rows = read_csv("rq3_quality/system_tests.csv")
by = collections.defaultdict(list)
for r in rows:
    by[r["Source_File"]].append(r)
out = []
for rep, rs in sorted(by.items()):
    fr, nfr = set(), set(); fp = ff = np_ = nf = 0
    for r in rs:
        ids = split(r["Requirement_ID"])
        for i in ids:
            (nfr if i.startswith("NFR") else fr).add(i)
        nonf = bool(ids) and all(i.startswith("NFR") for i in ids)
        res = r["Result"].strip()
        if res not in {"Pass", "Fail"}:          # N/A and blank results excluded
            continue
        if nonf:
            np_ += res == "Pass"; nf += res == "Fail"
        else:
            fp += res == "Pass"; ff += res == "Fail"
    out.append([rep, len(fr | nfr), len(fr), len(nfr), fp, ff, np_, nf])
write_csv("system_tests_per_report.csv", ["report", "reqs", "functional_reqs", "nonfunctional_reqs", "func_pass",
                                          "func_fail", "nonfunc_pass", "nonfunc_fail"], out)
cols = ["requirements", "functional", "non-functional", "func pass", "func fail", "non-func pass", "non-func fail"]
print(f"reports: {len(out)}  (requirement totals are summed per report; requirement ids such as FR1 recur across reports)")
glob_f = {i for r in rows for i in split(r["Requirement_ID"]) if not i.startswith("NFR")}
glob_n = {i for r in rows for i in split(r["Requirement_ID"]) if i.startswith("NFR")}
print(f"for comparison, distinct requirement id strings across all reports: {len(glob_f | glob_n)} ({len(glob_f)} functional, {len(glob_n)} non-functional)")
for i, c in enumerate(cols, 1):
    v = [o[i] for o in out]
    print(f"{c:15} total {sum(v):4}  median {statistics.median(v):4}  range {min(v)}-{max(v)}")
