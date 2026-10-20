"""RQ3: standardise smell labels from students' code-review reports into 19 categories
(Table "student-reported smells"). A label naming several smells goes to the smell named first.

Input : data/rq3_quality/student_reported_smells.csv
Output: results/student_smells_by_category.csv, results/student_smells_per_group.csv
"""
import sys, re, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import read_csv, write_csv

CATS = [  # (category, regex)
 ('God Component', r'god|large (class|component|module|controller)|large backend controller|bloater \(large|mixed responsib|low cohesion|srp|long component|complexity'),
 ('Duplicate Code', r'duplicat|\bdry\b|copy-paste'),
 ('Long Method', r'long (method|function)|long methods|bloater \(long|complex (function|callback)|deeply nested'),
 ('Magic Strings', r'magic|hard-?coded'),
 ('Error Handling Smell', r'error handling|exception'),
 ('Dead Code', r'dead|unused|unreachable|dispensable|speculative'),
 ('Performance Smell', r'perform|n\+1|redundant data fetching|in-memory|sequential'),
 ('Divergent Change', r'divergent|inconsistent (logic|validation|api|dependency)'),
 ('Vulnerabilities', r'secur|secret|credential|leakage|enumeration|sql interp|authentication|objectid'),
 ('Improper Layering', r'layer|separation of concerns|mixing ui|mixed concerns|coupler|logic / ui|route clutter'),
 ('UI / State Management Smell', r'react|state management|hook|inline style|loading state|client component|\bux\b|ui, state'),
 ('Tight Coupling', r'(?<!temporal )coupl|intimacy|shotgun|scattered'),
 ('Weak Typing', r'typing|type coercion|type definitions'),
 ('Excessive Comments', r'comment|whitespace'),
 ('Poor Abstraction', r'abstraction|extraction|anemic'),
 ('Data Clumps', r'clump|prop drilling|parameter list'),
 ('Temporal Coupling', r'temporal|race condition'),
 ('Architectural Smell', r'architectur'),
 ('Primitive Obsession', r'primitive'),
]


def category(label):
    l = label.lower(); best = None
    for c, rx in CATS:
        m = re.search(rx, l)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), c)
    return best[1] if best else 'Other'


def per_group():
    per = collections.defaultdict(collections.Counter)
    for r in read_csv("rq3_quality/student_reported_smells.csv"):
        n = float(r["occurrences"]) if r["occurrences"] else 1.0
        per[r["group"]][category(r["smell_label"])] += n
    return per


if __name__ == "__main__":
    per = per_group()
    tot = collections.Counter(); ng = collections.Counter()
    for g, cs in per.items():
        for c, n in cs.items():
            tot[c] += n; ng[c] += 1
    T = sum(tot.values())
    rows = sorted(tot.items(), key=lambda x: (-x[1], -ng[x[0]]))
    write_csv("student_smells_by_category.csv", ["category", "occurrences", "percent", "groups"],
              [[c, int(n), round(100 * n / T, 1), ng[c]] for c, n in rows])
    cats = [c for c, _ in rows]
    write_csv("student_smells_per_group.csv", ["group"] + cats,
              [[g] + [int(per[g].get(c, 0)) for c in cats] for g in sorted(per, key=int)])
    print(f"total occurrences {T:.0f} from {len(per)} groups")
    for c, n in rows:
        print(f"{n:5.0f}  {100*n/T:5.1f}%  groups {ng[c]:2d}  {c}")
