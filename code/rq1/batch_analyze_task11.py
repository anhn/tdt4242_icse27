#!/usr/bin/env python3
"""Batch-analyze all Task 1.1 interview files; write per-file results and summary."""

from __future__ import annotations

import csv
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sentence_transformers import SentenceTransformer

from analyze_interview_pair import MODEL_NAME, analyze_file

INPUT_DIR = Path(__file__).resolve().parent / "Task1.1"
RESULT_DIR = Path(__file__).resolve().parent / "result"

METRICS = [f"M{i}" for i in range(13)]

METRIC_LABELS = {
    "M0": "Interviewer turns",
    "M1": "Stakeholder turns",
    "M2": "Interviewer questions",
    "M3": "Total words",
    "M4": "Interviewer words",
    "M5": "Stakeholder words",
    "M6": "Talk ratio (Interviewer/Stakeholder)",
    "M7": "Follow-up questions",
    "M8": "Clarification questions",
    "M9": "Vendi Score",
    "M10": "Mean semantic distance",
    "M11": "Topic coverage",
    "M12": "Mean semantic information gain",
}


def discover_files(input_dir: Path) -> list[Path]:
    files = []
    for ext in ("*.txt", "*.pdf", "*.docx"):
        files.extend(input_dir.glob(ext))
    files = sorted(
        [f for f in files if "feedback" not in f.name.lower()],
        key=lambda p: p.name.lower(),
    )
    return files


def write_markdown_report(result: dict, out_path: Path) -> None:
    s = result["summary"]
    lines = [
        f"# Interview Analysis — {Path(result['file']).name}",
        "",
        f"- Source: `{result['file']}`",
        f"- Model: `{result.get('model', MODEL_NAME)}`",
        "",
        "## Summary",
        "",
        "| Metric | Human Interview | AI Interview |",
        "|---|---:|---:|",
    ]
    for key in METRICS:
        label = METRIC_LABELS[key]
        human = s[key]["human"]
        ai = s[key]["ai"]
        lines.append(f"| {label} | {human} | {ai} |")

    lines.extend(["", "## Data quality notes", ""])
    for note in result.get("data_quality_notes", []):
        lines.append(f"- {note}")

    if result.get("error"):
        lines.extend(["", f"**Error:** {result['error']}"])

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def flatten_summary_row(file_name: str, summary: dict, status: str) -> dict:
    row = {"File": file_name, "Status": status}
    for key in METRICS:
        row[f"{key}_Human"] = summary.get(key, {}).get("human", "")
        row[f"{key}_AI"] = summary.get(key, {}).get("ai", "")
    return row


def write_summary_csv(rows: list[dict], out_path: Path) -> None:
    fieldnames = ["File", "Status"]
    for key in METRICS:
        fieldnames.extend([f"{key}_Human", f"{key}_AI"])
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary_markdown(rows: list[dict], out_path: Path) -> None:
    lines = [
        "# Task 1.1 — Interview Metrics Summary (All Files)",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Embedding model: `{MODEL_NAME}`",
        "",
    ]

    for row in rows:
        if row["Status"] != "ok":
            lines.extend([f"## {row['File']} — {row['Status']}", ""])
            continue
        lines.extend([
            f"## {row['File']}",
            "",
            "| Metric | Human Interview | AI Interview |",
            "|---|---:|---:|",
        ])
        for key in METRICS:
            lines.append(
                f"| {METRIC_LABELS[key]} | {row[f'{key}_Human']} | {row[f'{key}_AI']} |"
            )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else INPUT_DIR
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    files = discover_files(input_dir)
    if not files:
        print(f"No input files found in {input_dir}")
        return 1

    print(f"Loading embedding model {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    summary_rows: list[dict] = []
    errors: list[dict] = []

    for path in files:
        stem = path.stem
        print(f"Analyzing {path.name}...")
        try:
            result = analyze_file(path, model=model)
            result["status"] = "ok"

            json_path = RESULT_DIR / f"{stem}.json"
            md_path = RESULT_DIR / f"{stem}.md"
            json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            write_markdown_report(result, md_path)

            summary_rows.append(flatten_summary_row(path.name, result["summary"], "ok"))
        except Exception as exc:
            err = {
                "file": str(path),
                "status": "error",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
            errors.append(err)
            (RESULT_DIR / f"{stem}.error.json").write_text(
                json.dumps(err, indent=2), encoding="utf-8"
            )
            summary_rows.append(flatten_summary_row(path.name, {}, f"ERROR: {exc}"))

    write_summary_csv(summary_rows, RESULT_DIR / "all_files_metrics_summary.csv")
    write_summary_markdown(summary_rows, RESULT_DIR / "all_files_metrics_summary.md")

    manifest = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "input_dir": str(input_dir),
        "result_dir": str(RESULT_DIR),
        "files_processed": len(files),
        "ok": sum(1 for r in summary_rows if r["Status"] == "ok"),
        "errors": len(errors),
        "error_files": [e["file"] for e in errors],
    }
    (RESULT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps(manifest, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
