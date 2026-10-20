# Data and analysis code: "Same Prompts, Different Code: Engineering Control in an AI-Native Software Engineering Course"

This package contains the anonymised, group-level data and the analysis scripts behind the
paper's results. Groups are identified only by their course group number (1–25).

## Contents

```
data/
  rq1_interviews/interview_metrics.csv      13 interview measures per group, human vs. AI stakeholder (19 groups)
  rq2_strategies/strategy_codebook.csv      24 prompting strategies and their type (generation / consolidation / other)
  rq2_strategies/strategies_recoded.csv     strategy use per group, 0/1 (22 groups)
  rq2_strategies/prompt_styles_tickbox.csv  first, tick-box coding of prompt styles per group
  rq2_strategies/ai_tools_reported.csv      AI tools named in each group's reports (blank = not stated)
  rq3_quality/student_reported_smells.csv   smell labels and occurrences from students' code-review reports (21 groups)
  rq3_quality/static_metrics_final_code.csv lizard / jscpd metrics of the final code (17 repositories)
  rq3_quality/code_review_dates.csv         submission time of each group's code review
  rq3_quality/tool_smells_review_time.csv   tool-detected smells in the code at review time (17 repositories)
  rq3_quality/system_tests.csv              every executed cross-group system test (22 reports, ids R01–R22)
  rq4_reflections/reflection_codes.csv      presence (0/1) of each theme in the final reflections (20 reports)
  rq4_reflections/experience_scepticism.csv rated web-development experience and scepticism towards AI (1–5)
code/
  common.py                                 paths, Benjamini–Hochberg FDR, rank-biserial r
  rq1/rq1_wilcoxon.py                       Table 3: Wilcoxon signed-rank tests, r, FDR
  rq1/analyze_interview_pair.py,
  rq1/batch_analyze_task11.py               computation of the 13 interview measures from transcripts
  rq2/strategy_counts.py                    strategy prevalence; generation vs. consolidation per group
  rq3/standardise_student_smells.py         19 smell categories from students' labels
  rq3/final_code_metrics.py                 final-code metrics (needs repositories)
  rq3/summarise_final_metrics.py            summary of final-code metrics
  rq3/make_snapshots.py                     code as it was at review time (needs repositories)
  rq3/review_time_smells.py                 static analysis of the snapshots (needs repositories)
  rq3/tool_vs_students.py                   students' reviews vs. static analysis
  rq3/predictors_vs_quality.py              strategies, styles, experience vs. quality (three test families, FDR)
  rq3/extract_system_tests.py               extraction of tests from system-test reports (needs reports)
  rq3/system_tests.py                       system-testing summary
  rq4/theme_counts.py                       counts in the thematic map; experience vs. scepticism
  tools/                                    pinned Node tools and ESLint configuration
results/                                    output of the scripts that run on the included data
```

## Running

```
pip install numpy scipy
cd code
python rq1/rq1_wilcoxon.py
python rq2/strategy_counts.py
python rq3/standardise_student_smells.py
python rq3/summarise_final_metrics.py
python rq3/tool_vs_students.py
python rq3/system_tests.py
python rq3/predictors_vs_quality.py
python rq4/theme_counts.py
```

Each script prints the figures reported in the paper and writes a CSV to `results/`.
The scripts marked "needs repositories / reports / transcripts" document how the included data
were derived from material that is not shared (see below). To run them, install
`requirements.txt` and `npm install` in `code/tools`.

## Where the paper's numbers come from

| Paper element | Script | Output |
|---|---|---|
| Table 3, RQ1 results | rq1/rq1_wilcoxon.py | rq1_wilcoxon.csv |
| Table 4, generation vs. consolidation (median 5 vs. 1) | rq2/strategy_counts.py | strategy_prevalence.csv, generation_consolidation_per_group.csv |
| Student-reported smells table (349 occurrences, 21 groups) | rq3/standardise_student_smells.py | student_smells_by_category.csv |
| Final-code metrics (median 2.08 KLOC, 2.79% duplication) | rq3/summarise_final_metrics.py | — |
| Students' reviews vs. static analysis (58 of 86 / 84) | rq3/tool_vs_students.py | tool_vs_students.csv |
| Null results for strategies, styles, experience (99, 55, 220 tests) | rq3/predictors_vs_quality.py | predictors_*.csv |
| System testing | rq3/system_tests.py | system_tests_per_report.csv |
| Thematic map; experience vs. scepticism (rho = .60) | rq4/theme_counts.py | thematic_map_counts.csv |

## Methods notes

- Rank-biserial r is positive when the AI condition (RQ1) or the group using a strategy (RQ3) is higher.
- FDR correction is applied within each family of tests: 13 interview measures; 99, 55 and 220
  tests for the three predictor families.
- Snapshots: for each repository with a git history, the last commit before the code-review
  submission time. Groups 12 and 13 had no usable history; their submitted code was analysed.
- System testing: requirements are counted once per report and summed over reports;
  pass/fail counts are test executions, excluding N/A results.
- Reflections: group 3's reflection report is a copy of group 4's and is excluded, leaving 20.
  Columns `X_*` in reflection_codes.csv are themes added after the initial coding.

## Not included

The raw student material is not shared because it contains personal data and was collected
for teaching: interview transcripts, assignment and reflection reports, quotations from
them, code repositories and their URLs, and the names of students. The repositories also
contain credentials. Requests for access to this material can be made to the authors and
are subject to the conditions under which the data were collected.

## Licence

Data: CC BY 4.0. Code: MIT.
