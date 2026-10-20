"""RQ3: extract each repository as it was when its code review was submitted.

For each group with a git history, takes the last commit before the review timestamp
(git rev-list -1 --before=<timestamp> HEAD) and exports it with git archive.
Groups 12 and 13 had no usable history; their submitted zip was analysed instead.
Usage: python make_snapshots.py <repos_dir> <snap_dir>
Input: data/rq3_quality/code_review_dates.csv
"""
import os, sys, subprocess, shutil, io, tarfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import read_csv

repos, snap = sys.argv[1], sys.argv[2]
dates = {r["group"]: r["review_submitted_utc"] for r in read_csv("rq3_quality/code_review_dates.csv")}
os.makedirs(snap, exist_ok=True)
for g in sorted(os.listdir(repos), key=lambda s: int(s[1:])):
    src, dst, n = f"{repos}/{g}", f"{snap}/{g}", g[1:]
    if os.path.isdir(f"{src}/.git") and n in dates:
        sha = subprocess.run(["git", "-C", src, "rev-list", "-1", f"--before={dates[n]}", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        if sha:
            tar = subprocess.run(["git", "-C", src, "archive", sha], capture_output=True).stdout
            os.makedirs(dst, exist_ok=True)
            tarfile.open(fileobj=io.BytesIO(tar)).extractall(dst)
            print(g, "commit", sha[:10], "before", dates[n])
            continue
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "node_modules"))
    print(g, "no history before review: submitted version used")
