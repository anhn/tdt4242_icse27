"""RQ3: tool-detected smells in the code as it was at review time.

Requires the snapshots from make_snapshots.py, lizard and ruff (pip), and the Node tools in
code/tools (npm ci): ESLint 8.57 + eslint-plugin-sonarjs 0.25 + @typescript-eslint 7.18 + jscpd.
Usage : python review_time_smells.py <snap_dir>
Output: results/tool_smells_review_time.csv  (paper version: data/rq3_quality/tool_smells_review_time.csv)

Detection rules (category: rule)
  Duplicate Code : jscpd clones >= 50 tokens; sonarjs/no-identical-functions
  God Component  : source files > 300 non-blank lines
  Long Method    : functions > 50 lines or CCN > 10 (lizard); sonarjs/cognitive-complexity > 15
  Magic Strings  : sonarjs/no-duplicate-string (>= 3 repeats, >= 10 chars); same rule for Python via ast
  Dead Code      : @typescript-eslint/no-unused-vars, no-unreachable, sonarjs/no-unused-collection; ruff F401, F841
  Error Handling : no-empty, no-useless-catch, catch blocks that only log; ruff E722, BLE001, S110
  Performance    : no-await-in-loop
  Weak Typing    : @typescript-eslint/no-explicit-any (TypeScript only)
  Data Clumps    : functions with > 4 parameters (lizard)  [reported as "long parameter list"]
"""
import os, re, sys, json, ast, subprocess, collections, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_csv, ROOT
from final_code_metrics import EXC, CODE, is_test, nloc, JSCPD, JSCPD_IGNORE

TOOLS = ROOT / "code" / "tools"
RULE2CAT = {'sonarjs/no-duplicate-string': 'Magic Strings', 'sonarjs/no-identical-functions': 'Duplicate Code',
            'sonarjs/cognitive-complexity': 'Long Method', '@typescript-eslint/no-unused-vars': 'Dead Code',
            'no-unreachable': 'Dead Code', 'sonarjs/no-unused-collection': 'Dead Code',
            'no-empty': 'Error Handling', 'no-useless-catch': 'Error Handling',
            'no-await-in-loop': 'Performance Smell', '@typescript-eslint/no-explicit-any': 'Weak Typing'}
RUFF2CAT = {'F401': 'Dead Code', 'F841': 'Dead Code', 'E722': 'Error Handling', 'BLE001': 'Error Handling',
            'S110': 'Error Handling'}
CATCHLOG = re.compile(r'catch\s*(\(\s*\w*\s*(:\s*\w+\s*)?\))?\s*\{\s*console\.(log|error|warn)\([^;{}]*\);?\s*\}')
CATS = ['Duplicate Code', 'God Component', 'Long Method', 'Magic Strings', 'Dead Code', 'Error Handling',
        'Performance Smell', 'Weak Typing', 'Data Clumps']


def analyse(d):
    files = []
    for root, ds, fs in os.walk(d):
        ds[:] = [x for x in ds if x not in EXC]
        for f in fs:
            p = os.path.join(root, f)
            if os.path.splitext(f)[1] in CODE and not f.endswith(('.min.js', '.d.ts')) and 'config' not in f \
                    and not is_test(p):
                files.append(p)
    js = [os.path.abspath(f) for f in files if not f.endswith('.py')]
    py = [f for f in files if f.endswith('.py')]
    cnt = collections.Counter(); errors = 0
    size = {p: nloc(p) for p in files}
    cnt['God Component'] = sum(v > 300 for v in size.values())
    if files:
        out = subprocess.run(['lizard', '--csv'] + files, capture_output=True, text=True).stdout
        for line in out.splitlines():
            c = line.split(',')
            try:
                n, ccn, par = int(c[0]), int(c[1]), int(c[3])
            except (ValueError, IndexError):
                continue
            cnt['Long Method'] += (n > 50 or ccn > 10)
            cnt['Data Clumps'] += par > 4
    if js:
        r = subprocess.run([str(TOOLS / 'node_modules/.bin/eslint'), '--no-eslintrc', '-c', str(TOOLS / 'eslintrc.json'),
                            '--resolve-plugins-relative-to', str(TOOLS), '-f', 'json', '--no-ignore'] + js,
                           capture_output=True, text=True, cwd=TOOLS)
        for fr in json.loads(r.stdout or '[]'):
            for m in fr['messages']:
                if m.get('fatal') or not m.get('ruleId'):
                    errors += 1; continue
                if m['ruleId'] in RULE2CAT:
                    cnt[RULE2CAT[m['ruleId']]] += 1
        for f in js:
            cnt['Error Handling'] += len(CATCHLOG.findall(open(f, errors='ignore').read()))
    if py:
        r = subprocess.run(['ruff', 'check', '--select', 'F401,F841,E722,BLE001,S110', '--output-format', 'json',
                            '--no-cache'] + py, capture_output=True, text=True)
        for m in json.loads(r.stdout or '[]'):
            if m['code'] in RUFF2CAT:
                cnt[RUFF2CAT[m['code']]] += 1
        for f in py:
            try:
                lits = [n.value for n in ast.walk(ast.parse(open(f, errors='ignore').read()))
                        if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) >= 10]
                cnt['Magic Strings'] += sum(1 for s, k in collections.Counter(lits).items() if k >= 3)
            except SyntaxError:
                pass
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([str(JSCPD), '--silent', '--reporters', 'json', '--output', out, '--min-tokens', '50',
                        '--ignore', JSCPD_IGNORE, d], capture_output=True)
        try:
            st = json.load(open(f'{out}/jscpd-report.json'))['statistics']['total']
            cnt['Duplicate Code'] += st['clones']; dup = st['percentage']
        except Exception:
            dup = None
    lang = 'py' if py and not js else 'ts' if any(f.endswith(('.ts', '.tsx')) for f in js) else 'js'
    return round(sum(size.values()) / 1000, 2), len(files), lang, dup, errors, cnt


if __name__ == "__main__":
    snap = sys.argv[1]; rows = []
    for g in sorted(os.listdir(snap), key=lambda s: int(s[1:])):
        kloc, nfiles, lang, dup, err, cnt = analyse(f'{snap}/{g}')
        rows.append([g[1:], kloc, nfiles, lang, dup, err] + [cnt.get(c, 0) for c in CATS])
        print(rows[-1], flush=True)
    write_csv("tool_smells_review_time.csv", ["group", "kloc", "files", "language", "dup_pct", "parse_errors"] + CATS, rows)
