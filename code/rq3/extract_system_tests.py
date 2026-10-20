#!/usr/bin/env python3
"""Extract system test rows from Task 3.3 team reports."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pymupdf

FOLDER = Path(__file__).resolve().parent
OUT_CSV = FOLDER / "all_system_tests.csv"
OUT_MD = FOLDER / "all_system_tests.md"

PASS_FAIL_RE = re.compile(r"\b(pass|fail|passed|failed|n/a)\b", re.I)
TEST_ID_RE = re.compile(
    r"^(?:ST-?\s*\d+|T-?\d+|TC-?\s*FR\d+-\d+|TC-?\d+|SYS-?\d+|TEST-?\d+|Test\s*[-–]?\s*\d+|\d+|FR\d+\.\d+|NFR\d+\s*\.\s*\d+|T\d+_[A-Z0-9]+)$",
    re.I,
)
REQ_ID_RE = re.compile(
    r"^(?:FR-?\d+(?:\.\d+)?|NFR-?\d+|US-?\d+|US\d+|R-?\d+|RE-?\d+|REQ-?\d+|FR\d+\.\d+|FR\d+|R\d+)(?:\s*,\s*(?:FR-?\d+|NFR-?\d+))?$",
    re.I,
)

HEADER_ALIASES = {
    "test_id": {"test id", "test_id", "testid", "id", "test / requirement id"},
    "requirement_id": {
        "requirement id",
        "requirement_id",
        "requirement",
        "req id",
        "req. id",
        "req",
        "requirements id",
        "requiremen t id",
    },
    "scenario": {"test scenario", "scenario", "req. scenario", "req scenario"},
    "result": {"pass/fail", "pass / fail", "pass/ fail", "result", "pass fail"},
}


def clean_pdf_text(text: str) -> str:
    return re.sub(r"[\u200b\ufeff]", "", text)


def normalize_cell(value: str | None) -> str:
    if value is None:
        return ""
    text = re.sub(r"[\u200b\ufeff]", "", str(value))
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def normalize_result(value: str) -> str:
    text = normalize_cell(value)
    if not text:
        return ""
    if "❌" in text and "✅" in text:
        return "Fail"
    if "✅" in text and "❌" not in text:
        return "Pass"
    if "❌" in text:
        return "Fail"
    lower = text.lower()
    if lower in {"pass", "passed"}:
        return "Pass"
    if lower in {"fail", "failed"}:
        return "Fail"
    if lower in {"n/a", "na", "not tested", "not testable"}:
        return "N/A"
    m = PASS_FAIL_RE.search(text)
    if m:
        word = m.group(1).lower()
        if word in {"pass", "passed"}:
            return "Pass"
        if word in {"fail", "failed"}:
            return "Fail"
    return ""


def looks_like_test_id(value: str) -> bool:
    v = normalize_cell(value)
    if not v:
        return False
    if TEST_ID_RE.match(v):
        return True
    if re.match(r"^T\d+_[A-Z0-9]+$", v, re.I):
        return True
    if re.match(r"^TC-[A-Z0-9-]+$", v, re.I):
        return True
    if re.match(r"^FR\d+\.\d+$", v, re.I):
        return True
    if re.match(r"^NFR\d+\s*\.\s*\d+$", v, re.I):
        return True
    return False


def looks_like_req_id(value: str) -> bool:
    v = normalize_cell(value)
    if not v:
        return False
    if REQ_ID_RE.match(v):
        return True
    if re.match(r"^FR-S\d+$", v, re.I):
        return True
    if re.match(r"^US\d+$", v, re.I):
        return True
    if re.match(r"^FR\d+$", v, re.I):
        return True
    return False


def map_header(cells: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, cell in enumerate(cells):
        key = normalize_cell(cell).lower()
        key = re.sub(r"\s+", " ", key)
        for field, aliases in HEADER_ALIASES.items():
            if key in aliases and field not in mapping:
                mapping[field] = idx
    return mapping


def _result_from_cells(cells: list[str], header: dict[str, int]) -> str:
    idx = header.get("result")
    if idx is not None and idx < len(cells):
        result = normalize_result(cells[idx])
        if result in {"Pass", "Fail", "N/A"}:
            return result
    for cell in reversed(cells):
        result = normalize_result(cell)
        if result in {"Pass", "Fail", "N/A"}:
            return result
    return ""


def extract_vertical_kv_table(data: list[list], source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not data:
        return rows

    labels = {normalize_cell(r[0]).lower() for r in data if r and r[0]}
    if "test labels" not in labels and "requirement id" not in labels:
        return rows

    kv: dict[str, str] = {}
    test_id = ""
    for row in data:
        if not row:
            continue
        k = normalize_cell(row[0]).lower()
        v = normalize_cell(row[1]) if len(row) > 1 else ""
        if k:
            kv[k] = v
        c0 = normalize_cell(row[0])
        c1 = normalize_cell(row[1]) if len(row) > 1 else ""
        if looks_like_test_id(c0) and not c1:
            test_id = c0

    if "test id" in kv and looks_like_test_id(kv["test id"]):
        test_id = kv["test id"]
    req_id = kv.get("requirement id", "")
    scenario = kv.get("test scenario", "")
    result = normalize_result(kv.get("pass / fail", "") or kv.get("pass/fail", ""))

    if test_id and req_id and scenario and result in {"Pass", "Fail", "N/A"}:
        rows.append(
            {
                "Source_File": source,
                "Test_ID": test_id,
                "Requirement_ID": req_id,
                "Req_Scenario": scenario,
                "Result": result,
            }
        )
    return rows


def row_from_mapped(cells: list[str], header: dict[str, int], source: str) -> dict[str, str] | None:
    def get(field: str) -> str:
        idx = header.get(field)
        if idx is None or idx >= len(cells):
            return ""
        return normalize_cell(cells[idx])

    test_id = get("test_id")
    req_id = get("requirement_id")
    scenario = get("scenario")
    result = _result_from_cells(cells, header)

    if not test_id and not req_id:
        return None
    if not looks_like_test_id(test_id):
        return None
    if req_id and not looks_like_req_id(req_id) and not re.match(r"^US\d+$", req_id, re.I):
        if looks_like_req_id(test_id):
            return None
    if not scenario:
        return None
    if result not in {"Pass", "Fail", "N/A"}:
        return None
    return {
        "Source_File": source,
        "Test_ID": test_id,
        "Requirement_ID": req_id,
        "Req_Scenario": scenario,
        "Result": result,
    }


def infer_columns(cells: list[str]) -> dict[str, int] | None:
    if len(cells) < 3:
        return None
    c0 = normalize_cell(cells[0])
    c1 = normalize_cell(cells[1])
    if looks_like_test_id(c0) and (looks_like_req_id(c1) or re.match(r"^US\d+$", c1, re.I)):
        result_idx = None
        for i in range(len(cells) - 1, 1, -1):
            if normalize_result(cells[i]) in {"Pass", "Fail", "N/A"}:
                result_idx = i
                break
        if result_idx is None:
            for i, cell in enumerate(cells):
                if normalize_result(cell) in {"Pass", "Fail", "N/A"}:
                    result_idx = i
                    break
        if result_idx is None or result_idx <= 2:
            return None
        return {"test_id": 0, "requirement_id": 1, "scenario": 2, "result": result_idx}
    return None


def extract_from_tables(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    doc = pymupdf.open(path)
    source = path.name

    for page in doc:
        finder = page.find_tables()
        for table in finder.tables:
            data = table.extract()
            if not data:
                continue

            for vrow in extract_vertical_kv_table(data, source):
                key = (vrow["Test_ID"], vrow["Requirement_ID"], vrow["Req_Scenario"], vrow["Result"])
                if key not in seen:
                    seen.add(key)
                    rows.append(vrow)

            header = map_header([normalize_cell(c) for c in data[0]])
            start = 1 if header else 0
            if not header:
                guessed = infer_columns([normalize_cell(c) for c in data[0]])
                if guessed:
                    header = guessed
                    start = 0
            if not header:
                for raw in data:
                    cells = [normalize_cell(c) for c in raw]
                    if not any(cells):
                        continue
                    guessed = infer_columns(cells)
                    if not guessed:
                        continue
                    row = row_from_mapped(cells, guessed, source)
                    if not row:
                        continue
                    key = (row["Test_ID"], row["Requirement_ID"], row["Req_Scenario"], row["Result"])
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(row)
                continue
            for raw in data[start:]:
                cells = [normalize_cell(c) for c in raw]
                if not any(cells):
                    continue
                row = row_from_mapped(cells, header, source)
                if not row or not row.get("Requirement_ID"):
                    guessed = infer_columns(cells)
                    if guessed:
                        retry = row_from_mapped(cells, guessed, source)
                        if retry:
                            row = retry
                if not row:
                    continue
                row["Test_ID"] = normalize_test_id(row["Test_ID"])
                key = (row["Test_ID"], row["Requirement_ID"], row["Req_Scenario"], row["Result"])
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
    return rows


def parse_key_value_blocks(text: str, source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    blocks = re.split(r"(?=(?:Test\s*\d+|Test\s*[-–]\s*\d+|TEST_ID\s*:))", text, flags=re.I)
    for block in blocks:
        test_id = ""
        req_id = ""
        scenario = ""
        result = ""

        m = re.search(r"Test\s*ID\s*:?\s*([^\n]+)", block, re.I)
        if m:
            test_id = normalize_cell(m.group(1))
        m = re.search(r"TEST_ID\s*:?\s*([^\n]+)", block, re.I)
        if m:
            test_id = normalize_cell(m.group(1))
        m = re.search(r"Test\s*[-–]\s*(\d+)\s*:", block, re.I)
        if m and not test_id:
            test_id = f"Test-{m.group(1)}"

        m = re.search(r"Requirement\s*ID\s*:?\s*([^\n]+)", block, re.I)
        if m:
            req_id = normalize_cell(m.group(1))
        m = re.search(r"REQUIREMENT_ID\s*:?\s*([^\n]+)", block, re.I)
        if m:
            req_id = normalize_cell(m.group(1))

        m = re.search(
            r"(?:Test\s*Scenario|Scenario)\s*:?\s*(.+?)(?=\n(?:Input/Steps|Steps|Expected|Actual|Pass/Fail|Result:|Evidence|$))",
            block,
            re.I | re.S,
        )
        if m:
            scenario = normalize_cell(m.group(1))

        m = re.search(r"Pass/Fail\s*:?\s*([^\n]+)", block, re.I)
        if m:
            result = normalize_result(m.group(1))
        if not result:
            m = re.search(r"Pass\s*/\s*Fail\s*\n\s*([^\n]+)", block, re.I)
            if m:
                result = normalize_result(m.group(1))
        if not result:
            m = re.search(r"(?m)^Result\s*:?\s*([^\n]+)", block)
            if m:
                result = normalize_result(m.group(1))

        if test_id and req_id and scenario and result in {"Pass", "Fail", "N/A"}:
            rows.append(
                {
                    "Source_File": source,
                    "Test_ID": test_id,
                    "Requirement_ID": req_id,
                    "Req_Scenario": scenario,
                    "Result": result,
                }
            )
    return rows


def parse_ase_st_blocks(text: str, source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for m in re.finditer(
        r"ST-\s*(\d+)\s+"
        r"(FR\d+|NFR\d+)\s+"
        r"(.+?)\s+"
        r"(Pass|Fail|N/A)\b",
        text,
        re.I | re.S,
    ):
        rows.append(
            {
                "Source_File": source,
                "Test_ID": f"ST-{m.group(1)}",
                "Requirement_ID": normalize_cell(m.group(2)),
                "Req_Scenario": normalize_cell(m.group(3)),
                "Result": normalize_result(m.group(4)),
            }
        )
    return rows


def parse_overview_table(text: str, source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    # Compact overview: ST-01 / RE-09 / scenario / Pass
    pattern = re.compile(
        r"(ST-?\d+|T-?\d+|TC-?\d+|SYS-?\d+)\s+"
        r"(FR-?\d+|NFR-?\d+|RE-?\d+|R-?\d+|US-?\d+|REQ-?\d+|FR\d+|R\d+)\s+"
        r"(.+?)\s+"
        r"(Pass|Fail|N/A)\b",
        re.I | re.S,
    )
    for m in pattern.finditer(text):
        rows.append(
            {
                "Source_File": source,
                "Test_ID": normalize_cell(m.group(1)),
                "Requirement_ID": normalize_cell(m.group(2)),
                "Req_Scenario": normalize_cell(m.group(3)),
                "Result": normalize_result(m.group(4)),
            }
        )
    return rows


def parse_numbered_overview(text: str, source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    # tdt4242_exercise_33 style: 1\nFR-1.1\nAssignment declaration\nPass
    for block in re.finditer(
        r"(?m)^(\d+)\s*\n\s*(FR-[\d.]+|NFR-[\d.]+|US-?\d+|REQ-?\d+)\s*\n(.+?)\n\s*(Pass|Fail|N/A)\s*$",
        text,
        re.S,
    ):
        rows.append(
            {
                "Source_File": source,
                "Test_ID": block.group(1),
                "Requirement_ID": normalize_cell(block.group(2)),
                "Req_Scenario": normalize_cell(block.group(3)),
                "Result": normalize_result(block.group(4)),
            }
        )
    return rows


def parse_inline_rows(text: str, source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    # ST01 FR01 scenario ... Pass
    for line in text.splitlines():
        line = normalize_cell(line)
        m = re.match(
            r"^(ST-?\d+|T-?\d+|TC-?\d+)\s+"
            r"(FR-?\d+|NFR-?\d+|FR\d+|US\d+|R-?\d+|RE-?\d+)\s+"
            r"(.+?)\s+"
            r"(Pass|Fail|N/A)\b",
            line,
            re.I,
        )
        if m:
            rows.append(
                {
                    "Source_File": source,
                    "Test_ID": m.group(1),
                    "Requirement_ID": m.group(2),
                    "Req_Scenario": m.group(3),
                    "Result": normalize_result(m.group(4)),
                }
            )
    return rows


def parse_multiline_blocks(text: str, source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    chunks = re.split(r"(?=\bST\d+\b|\bT0?\d+\b|\bTC0?\d+\b|\bSYS-\d+\b)", text)
    for chunk in chunks:
        lines = [normalize_cell(x) for x in chunk.splitlines() if normalize_cell(x)]
        if len(lines) < 4:
            continue
        if not looks_like_test_id(lines[0]):
            continue
        req_idx = 1
        req_id = lines[req_idx]
        if not looks_like_req_id(req_id):
            continue
        result_idx = None
        for i in range(len(lines) - 1, 1, -1):
            if normalize_result(lines[i]) in {"Pass", "Fail", "N/A"}:
                result_idx = i
                break
        if result_idx is None or result_idx <= 2:
            continue
        scenario = " ".join(lines[2:result_idx])
        if len(scenario) < 8:
            continue
        rows.append(
            {
                "Source_File": source,
                "Test_ID": lines[0],
                "Requirement_ID": req_id,
                "Req_Scenario": scenario,
                "Result": normalize_result(lines[result_idx]),
            }
        )
    return rows


def normalize_test_id(value: str) -> str:
    v = normalize_cell(value)
    v = re.sub(r"\s+", "", v)
    return v


def is_valid_extracted_row(row: dict[str, str]) -> bool:
    test_id = row["Test_ID"]
    if not test_id or test_id.lower() in {"test id", "test type", "requirement id", "test labels"}:
        return False
    if not row["Req_Scenario"]:
        return False
    if row["Result"] not in {"Pass", "Fail", "N/A"}:
        return False
    return looks_like_test_id(test_id) or test_id.isdigit()


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        row["Test_ID"] = normalize_test_id(row["Test_ID"])
        if not is_valid_extracted_row(row):
            continue
        key = (row["Source_File"], row["Test_ID"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def extract_file(path: Path) -> list[dict[str, str]]:
    rows = extract_from_tables(path)
    text = clean_pdf_text("\n".join(page.get_text() for page in pymupdf.open(path)))
    rows.extend(parse_key_value_blocks(text, path.name))
    rows.extend(parse_ase_st_blocks(text, path.name))
    rows.extend(parse_overview_table(text, path.name))
    rows.extend(parse_numbered_overview(text, path.name))
    rows.extend(parse_inline_rows(text, path.name))
    rows.extend(parse_multiline_blocks(text, path.name))
    return dedupe_rows(rows)


def write_outputs(rows: list[dict[str, str]]) -> None:
    fieldnames = ["Source_File", "Test_ID", "Requirement_ID", "Req_Scenario", "Result"]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Task 3.3 System Tests — Collected Results",
        "",
        f"Total rows: {len(rows)}",
        "",
    ]
    current = ""
    for row in rows:
        if row["Source_File"] != current:
            current = row["Source_File"]
            lines.extend(["", f"## {current}", "", "| Test ID | Requirement ID | Req. Scenario | Result |", "|---|---|---|---|"])
        scenario = row["Req_Scenario"].replace("|", "\\|")
        lines.append(
            f"| {row['Test_ID']} | {row['Requirement_ID']} | {scenario} | {row['Result']} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    all_rows: list[dict[str, str]] = []
    summary: list[tuple[str, int, str]] = []
    for path in sorted(FOLDER.glob("*.pdf")):
        rows = extract_file(path)
        status = "ok" if rows else "no rows extracted"
        summary.append((path.name, len(rows), status))
        all_rows.extend(rows)

    write_outputs(all_rows)

    print(f"Extracted {len(all_rows)} test rows from {len(summary)} PDFs")
    print(f"Saved {OUT_CSV}")
    print(f"Saved {OUT_MD}")
    print()
    for name, count, status in summary:
        print(f"  {count:3d}  {status:18s}  {name}")


if __name__ == "__main__":
    main()
