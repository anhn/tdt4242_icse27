"""RQ4: counts behind the thematic map (Figure "thematic map") and the experience-scepticism correlation.

Input : data/rq4_reflections/reflection_codes.csv  (20 independent reflection reports; group 3's
        report duplicates group 4's and is excluded), data/rq4_reflections/experience_scepticism.csv
Output: results/thematic_map_counts.csv
"""
import sys
from pathlib import Path
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import read_csv, write_csv

THEMES = [  # (activity, valence, label in figure, code)
 ("Requirements", "+", "Broad domain knowledge", "R+2"), ("Requirements", "+", "Fast, clear answers", "R+1"),
 ("Requirements", "-", "No real stakeholder view", "R-2"), ("Requirements", "-", "Agreeable, non-proactive", "R-4"),
 ("Requirements", "-", "Weakens elicitation", "R-1"), ("Requirements", "-", "Inconsistent answers", "R-3"),
 ("Testing", "+", "Diagnosing errors and smells", "T+1"), ("Testing", "+", "Implementing fixes", "T+3"),
 ("Testing", "+", "Generating tests quickly", "X_test_generation"), ("Testing", "+", "Learning through testing", "T+2"),
 ("Testing", "-", "Humans carry verification", "T-3"), ("Testing", "-", "Failed or false fixes", "X_failed_fixes"),
 ("Testing", "-", "Monolithic code hard to test", "T-2"),
 ("Design & implementation", "+", "Working code, few fixes", "D+1"), ("Design & implementation", "+", "Productivity and speed", "D+4"),
 ("Design & implementation", "+", "Learning web development", "D+2"), ("Design & implementation", "+", "Structure and stack advice", "D+3"),
 ("Design & implementation", "+", "Confidence in delivering", "D+5"),
 ("Design & implementation", "-", "Defects and code smells", "D-1"), ("Design & implementation", "-", "Human revision still needed", "D-3"),
 ("Design & implementation", "-", "Reduced ownership", "D-2"), ("Design & implementation", "-", "Works but poorly structured", "D-4"),
 ("Design & implementation", "-", "Outdated library knowledge", "X_outdated_libraries"),
 ("Design & implementation", "-", "Over-engineering", "X_over_engineering"),
 ("Cross-cutting", "", "Role shifts from writing code to reviewing and orchestrating AI", "X_role_shift"),
]
R = read_csv("rq4_reflections/reflection_codes.csv")
rows = [[a, v, lab, code, sum(int(r[code]) for r in R), len(R)] for a, v, lab, code in THEMES]
write_csv("thematic_map_counts.csv", ["activity", "valence", "theme", "code", "reports", "of_reports"], rows)
for r in rows:
    print(f"{r[0]:24} {r[1]:1} {r[2]:62} {r[4]:2}/{r[5]}")
E = read_csv("rq4_reflections/experience_scepticism.csv")
rho, p = stats.spearmanr([float(e["webdev_experience_1to5"]) for e in E], [float(e["scepticism_1to5"]) for e in E])
print(f"\nexperience vs scepticism: rho = {rho:.2f}, p = {p:.3f}, n = {len(E)}")
