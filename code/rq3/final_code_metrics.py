"""RQ3: structural metrics of the final code (lizard + jscpd).

Requires the student repositories (not distributed) under repos/g<N>/ next to this package,
plus lizard (pip) and jscpd (npm, see code/tools/package.json).
Usage : python final_code_metrics.py <repos_dir>
Output: data/rq3_quality/static_metrics_final_code.csv is the version used in the paper.
        Running this script writes results/static_metrics_final_code.csv.
Run summarise_final_metrics.py to get the summary statistics reported in the paper.
"""
import os, sys, json, subprocess, re, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import write_csv, ROOT

EXC = {'node_modules', '.git', 'dist', 'build', '.next', 'coverage', 'venv', '.venv', '__pycache__',
       'migrations', 'public', 'static', 'env'}
CODE = {'.js', '.jsx', '.ts', '.tsx', '.py'}
JSCPD = ROOT / "code" / "tools" / "node_modules" / ".bin" / "jscpd"
JSCPD_IGNORE = ('**/node_modules/**,**/dist/**,**/build/**,**/*.test.*,**/*.spec.*,**/tests/**,'
                '**/__tests__/**,**/*.css,**/*.html,**/*.json,**/*.md')
is_test = lambda p: bool(re.search(r'(^|/)(tests?|__tests__|spec)(/|$)|\.(test|spec)\.|(^|/)test_[^/]*\.py$', p))
nloc = lambda p: sum(1 for l in open(p, errors='ignore') if l.strip())


def source_files(d):
    files, tests = [], []
    for root, ds, fs in os.walk(d):
        ds[:] = [x for x in ds if x not in EXC]
        for f in fs:
            p = os.path.join(root, f)
            if os.path.splitext(f)[1] in CODE and not f.endswith(('.min.js', '.d.ts')) and 'config' not in f:
                (tests if is_test(p) else files).append(p)
    return files, tests


def lizard(files):
    if not files:
        return []
    r = subprocess.run(['lizard', '--csv'] + files, capture_output=True, text=True)
    rows = []
    for line in r.stdout.splitlines():
        c = line.split(',')
        try:
            rows.append((int(c[0]), int(c[1]), int(c[3])))   # NLOC, CCN, parameters
        except (ValueError, IndexError):
            pass
    return rows


def jscpd(d):
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([str(JSCPD), '--silent', '--reporters', 'json', '--output', out, '--min-tokens', '50',
                        '--ignore', JSCPD_IGNORE, d], capture_output=True, text=True)
        try:
            st = json.load(open(f'{out}/jscpd-report.json'))['statistics']['total']
            return st['percentage'], st['clones']
        except Exception:
            return None, None


if __name__ == "__main__":
    repos = sys.argv[1]
    rows = []
    for g in sorted(os.listdir(repos), key=lambda s: int(s[1:])):
        files, tests = source_files(f'{repos}/{g}')
        fn = lizard(files)
        size = {p: nloc(p) for p in files}
        kloc = sum(size.values()) / 1000
        tloc = sum(nloc(p) for p in tests)
        dup, clones = jscpd(f'{repos}/{g}')
        rows.append([g[1:], round(kloc, 2), len(files), sum(v > 300 for v in size.values()),
                     max(size.values()) if size else 0, len(fn), sum(n > 50 for n, c, _ in fn),
                     sum(c > 10 for n, c, _ in fn), dup, clones, tloc,
                     round(tloc / (kloc * 1000), 3) if kloc else 0])
        print(rows[-1], flush=True)
    write_csv("static_metrics_final_code.csv",
              ["group", "kloc", "files", "large_files", "max_file", "functions", "long_funcs",
               "complex_funcs", "dup_pct", "clones", "test_loc", "test_ratio"], rows)
