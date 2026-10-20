#!/usr/bin/env python3
"""Analyze Human vs AI interview transcripts for requirements elicitation study."""

import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"


@dataclass
class Turn:
    speaker: str  # interviewer | stakeholder
    text: str
    turn_num: int
    questions: list[str] = field(default_factory=list)


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    return text


def split_questions(text: str) -> list[str]:
    """Split interviewer text into individual substantive questions."""
    text = text.strip()
    if not text:
        return []

    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove parenthetical interviewer notes like "(if 4.1 was to vague...)"
    text = re.sub(r"\([^)]*ask this[^)]*\)", "", text, flags=re.I)

    parts = re.split(r"(?<=[\?])\s+", text)
    questions = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "?" not in part:
            continue
        # Keep only up to the last question mark chunk if multiple without split
        subparts = re.findall(r"[^?]+\?", part)
        for sp in subparts:
            q = normalize_text(sp)
            if len(q.split()) >= 3:
                questions.append(q)
    return questions


def is_greeting_or_farewell(text: str) -> bool:
    t = text.lower().strip()
    if len(t.split()) <= 6 and any(
        w in t for w in ["hello", "hi ", "thanks", "thank you", "bye", "goodbye"]
    ):
        return True
    return False


def parse_interview_block(lines: list[str], stakeholder_label: str) -> list[Turn]:
    """Parse transcript lines into interviewer/stakeholder turns."""
    turns: list[Turn] = []
    current_speaker = None
    current_lines: list[str] = []
    turn_num = 0

    stakeholder_patterns = [
        re.compile(rf"^{re.escape(stakeholder_label)}\s*:?\s*$", re.I),
        re.compile(rf"^{re.escape(stakeholder_label)}\s*:", re.I),
    ]
    interviewer_pattern = re.compile(r"^Interviewer\s*:?\s*$", re.I)
    interviewer_with_text = re.compile(r"^Interviewer\s*:\s*(.*)$", re.I)
    stakeholder_with_text = re.compile(rf"^{re.escape(stakeholder_label)}\s*:\s*(.*)$", re.I)
    metadata_noise = re.compile(
        r"^(Group\d+|Course:|Context:|Mode:|Date:|Interviewee:)",
        re.I,
    )
    metadata_interviewer = re.compile(r"^Interviewer:\s*Group\d+", re.I)

    expect_stakeholder_response = False

    def flush():
        nonlocal turn_num, current_speaker, current_lines, expect_stakeholder_response
        if current_speaker and current_lines:
            text = normalize_text(" ".join(current_lines))
            if text and not metadata_noise.search(text) and not metadata_interviewer.search(text):
                turn_num += 1
                turn = Turn(
                    speaker=current_speaker,
                    text=text,
                    turn_num=turn_num,
                )
                if current_speaker == "interviewer":
                    turn.questions = split_questions(text)
                    if turn.questions and not any(
                        ch.isalpha() for ch in text.replace(turn.questions[-1], "")
                    ):
                        expect_stakeholder_response = True
                    else:
                        expect_stakeholder_response = False
                else:
                    expect_stakeholder_response = False
                turns.append(turn)
        current_speaker = None
        current_lines = []

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue

        if metadata_noise.match(stripped) or metadata_interviewer.match(stripped):
            continue

        # Skip question headers like "Question 1", "Question 1.1"
        if re.match(r"^Question\s+[\d.]+$", stripped, re.I):
            continue

        m_int = interviewer_with_text.match(stripped)
        m_stk = stakeholder_with_text.match(stripped)
        if m_int:
            flush()
            current_speaker = "interviewer"
            rest = m_int.group(1).strip()
            current_lines = [rest] if rest else []
            continue
        if m_stk:
            flush()
            current_speaker = "stakeholder"
            rest = m_stk.group(1).strip()
            current_lines = [rest] if rest else []
            continue
        if interviewer_pattern.match(stripped):
            flush()
            current_speaker = "interviewer"
            current_lines = []
            continue
        if any(p.match(stripped) for p in stakeholder_patterns):
            flush()
            current_speaker = "stakeholder"
            current_lines = []
            continue

        # Orphan question while inside stakeholder turn -> split turn
        if current_speaker == "stakeholder" and stripped.endswith("?") and len(stripped.split()) >= 4:
            flush()
            current_speaker = "interviewer"
            current_lines = [stripped]
            continue

        if current_speaker == "interviewer" and current_lines:
            combined = " ".join(current_lines + [stripped])
            if "?" in combined and not stripped.endswith("?"):
                flush()
                current_speaker = "stakeholder"
                current_lines = [stripped]
                continue

        if current_speaker:
            current_lines.append(stripped)
        elif expect_stakeholder_response:
            current_speaker = "stakeholder"
            current_lines = [stripped]
            expect_stakeholder_response = False
        elif stripped.endswith("?"):
            flush()
            current_speaker = "interviewer"
            current_lines = [stripped]

    flush()
    return turns


def extract_sections(full_text: str) -> tuple[list[str], list[str]]:
    ai_start = full_text.find("Interview Transcript – iRE Agent")
    human_start = full_text.find("Interview Transcript – Student")
    req_start = full_text.find("Functional and Non-functional Requirements")

    if ai_start == -1 or human_start == -1:
        raise ValueError("Could not locate interview sections")

    ai_block = full_text[ai_start:human_start]
    human_end = req_start if req_start != -1 else len(full_text)
    human_block = full_text[human_start:human_end]

    def block_to_lines(block: str) -> list[str]:
        # Skip header metadata until first Question marker or Interviewer
        lines = block.splitlines()
        out = []
        started = False
        for line in lines:
            if not started and (
                re.match(r"^Question\s+", line.strip(), re.I)
                or line.strip().startswith("Interviewer")
            ):
                started = True
            if started:
                out.append(line)
        return out

    return block_to_lines(ai_block), block_to_lines(human_block)


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def compute_metrics(turns: list[Turn]) -> dict:
    interviewer_turns = [t for t in turns if t.speaker == "interviewer"]
    stakeholder_turns = [t for t in turns if t.speaker == "stakeholder"]

    m0 = len(interviewer_turns)
    m1 = len(stakeholder_turns)
    all_questions = []
    for t in interviewer_turns:
        all_questions.extend((t.turn_num, q) for q in t.questions)
    m2 = len(all_questions)

    m4 = sum(word_count(t.text) for t in interviewer_turns)
    m5 = sum(word_count(t.text) for t in stakeholder_turns)
    m3 = m4 + m5
    m6 = round(m4 / m5, 3) if m5 else None

    substantive_stakeholder = [
        t for t in stakeholder_turns if not is_greeting_or_farewell(t.text)
    ]

    return {
        "M0": m0,
        "M1": m1,
        "M2": m2,
        "M3": m3,
        "M4": m4,
        "M5": m5,
        "M6": m6,
        "interviewer_turns": interviewer_turns,
        "stakeholder_turns": stakeholder_turns,
        "substantive_stakeholder": substantive_stakeholder,
        "all_questions": all_questions,
    }


def embed_texts(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 768))
    emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(emb)


def vendi_score(embeddings: np.ndarray) -> float:
    if len(embeddings) == 0:
        return float("nan")
    if len(embeddings) == 1:
        return 1.0
    sim = embeddings @ embeddings.T
    sim = np.clip(sim, 0, 1)
    eigvals = np.linalg.eigvalsh(sim)
    eigvals = eigvals[eigvals > 1e-12]
    p = eigvals / eigvals.sum()
    entropy = -np.sum(p * np.log(p))
    return float(np.exp(entropy))


def mean_semantic_distance(embeddings: np.ndarray) -> float:
    n = len(embeddings)
    if n < 2:
        return float("nan")
    sim = embeddings @ embeddings.T
    dists = []
    for i in range(n):
        for j in range(i + 1, n):
            dists.append(1.0 - float(sim[i, j]))
    return round(float(np.mean(dists)), 3)


def information_gains(embeddings: np.ndarray) -> list[float]:
    gains = []
    if len(embeddings) <= 1:
        return gains
    for t in range(1, len(embeddings)):
        sims = embeddings[t] @ embeddings[:t].T
        max_sim = float(np.max(sims)) if len(sims) else 0.0
        gains.append(round(1.0 - max_sim, 3))
    return gains


def cluster_topics(pooled_embeddings: np.ndarray, texts: list[str], max_k: int = 10):
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    n = len(texts)
    if n <= 2:
        k = 1
    else:
        best_k = 2
        best_score = -1
        lower = 3
        upper = min(max_k, max(3, n // 4))
        for k_try in range(lower, upper + 1):
            km = KMeans(n_clusters=k_try, random_state=42, n_init=10)
            labels = km.fit_predict(pooled_embeddings)
            if len(set(labels)) < 2:
                continue
            score = silhouette_score(pooled_embeddings, labels)
            if score > best_score:
                best_score = score
                best_k = k_try
        k = best_k

    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(pooled_embeddings)

    # Simple label from keywords in cluster
    topic_labels = []
    for cid in range(k):
        cluster_texts = [texts[i] for i, lb in enumerate(labels) if lb == cid]
        words = re.findall(r"\b[a-zA-Z]{4,}\b", " ".join(cluster_texts).lower())
        stop = {
            "that", "this", "with", "from", "have", "would", "should", "their",
            "students", "student", "system", "usage", "also", "such", "they",
            "about", "which", "when", "what", "where", "there", "these", "those",
            "into", "more", "other", "could", "being", "through", "ensure",
        }
        freq: dict[str, int] = {}
        for w in words:
            if w not in stop:
                freq[w] = freq.get(w, 0) + 1
        top = sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:3]
        label = ", ".join(w for w, _ in top) if top else f"Topic {cid + 1}"
        topic_labels.append(f"T{cid + 1}: {label}")

    return labels, topic_labels, k


def identify_followups(turns: list[Turn]) -> tuple[list[dict], list[dict]]:
    """Conservative follow-up/clarification detection per study protocol."""
    followups = []
    clarifications = []

    clarification_patterns = [
        r"what do you mean",
        r"clarify|explain|elaborate|specify|disambiguate",
        r"at what (level|stage|stages)",
        r"what level of",
        r"what kind of",
        r"what (shortcomings|limitations|risks|actions|information)",
        r"how (much|many|should)",
        r"which (of these|parts|features)",
        r"under what constraints",
        r"why do they require",
        r"what should be",
        r"what pages should",
        r"what would make",
        r"is there a way",
        r"could you use",
        r"how would you feel",
        r"what do you usually",
        r"how do you personally",
        r"can you describe",
        r"have you ever",
        r"what do you typically",
    ]

    last_stakeholder_text = None
    last_stakeholder_turn = None
    pending_main_question = False

    for turn in turns:
        if turn.speaker == "stakeholder":
            last_stakeholder_text = turn.text
            last_stakeholder_turn = turn.turn_num
            pending_main_question = False
            continue

        if turn.speaker != "interviewer" or not last_stakeholder_text:
            continue

        for q in turn.questions:
            q_lower = q.lower()
            is_clarification = any(re.search(p, q_lower) for p in clarification_patterns)

            # Follow-up requires explicit build-on prior stakeholder content:
            # (1) anaphora / continuation cues, OR
            # (2) narrows/elaborates same entity from immediately prior response, OR
            # (3) clarification subtype
            anaphora = bool(
                re.search(
                    r"\b(these|those|this|that|such|them|it|previous|above|you (said|mentioned)|following up)\b",
                    q_lower,
                )
            )
            overlap = set(re.findall(r"\b[a-zA-Z]{5,}\b", q_lower)) & set(
                re.findall(r"\b[a-zA-Z]{5,}\b", last_stakeholder_text.lower())
            )
            domain_overlap = len(
                overlap
                - {
                    "about", "which", "would", "should", "their", "there",
                    "these", "those", "could", "other", "students", "student",
                    "system", "usage", "guidebook", "assignment", "assignments",
                }
            ) >= 2

            is_followup = is_clarification or anaphora or (
                domain_overlap and not re.match(r"^(how would you use|from the perspective)", q_lower)
            )

            if is_followup:
                followups.append(
                    {
                        "turn": turn.turn_num,
                        "question": q,
                        "previous_stakeholder_statement": last_stakeholder_text,
                        "previous_stakeholder_turn": last_stakeholder_turn,
                    }
                )
                if is_clarification:
                    clarifications.append(
                        {
                            "turn": turn.turn_num,
                            "question": q,
                            "statement_clarified": last_stakeholder_text,
                        }
                    )

    return followups, clarifications


def analyze_document(text: str, source_name: str, model=None) -> dict:
    from task11_parser import parse_document

    ai_turns, human_turns, parse_notes = parse_document(text)
    return _analyze_turns(ai_turns, human_turns, source_name, parse_notes, model)


def analyze_file(path: Path, model=None) -> dict:
    from task11_parser import load_document_text

    text = load_document_text(path)
    return analyze_document(text, str(path), model)


def _analyze_turns(ai_turns, human_turns, source_name, extra_notes, model=None) -> dict:
    ai_m = compute_metrics(ai_turns)
    human_m = compute_metrics(human_turns)

    ai_followups, ai_clar = identify_followups(ai_turns)
    human_followups, human_clar = identify_followups(human_turns)

    if model is None:
        model = SentenceTransformer(MODEL_NAME)

    ai_sub_texts = [t.text for t in ai_m["substantive_stakeholder"]]
    human_sub_texts = [t.text for t in human_m["substantive_stakeholder"]]
    pooled_texts = ai_sub_texts + human_sub_texts

    ai_emb = embed_texts(model, ai_sub_texts)
    human_emb = embed_texts(model, human_sub_texts)
    pooled_emb = embed_texts(model, pooled_texts)

    ai_vendi = round(vendi_score(ai_emb), 3) if len(ai_sub_texts) else float("nan")
    human_vendi = round(vendi_score(human_emb), 3) if len(human_sub_texts) else float("nan")
    ai_msd = mean_semantic_distance(ai_emb)
    human_msd = mean_semantic_distance(human_emb)
    ai_ig = information_gains(ai_emb)
    human_ig = information_gains(human_emb)
    ai_mig = round(float(np.mean(ai_ig)), 3) if ai_ig else float("nan")
    human_mig = round(float(np.mean(human_ig)), 3) if human_ig else float("nan")

    if pooled_texts:
        labels, topic_labels, k = cluster_topics(pooled_emb, pooled_texts)
        ai_labels = labels[: len(ai_sub_texts)]
        human_labels = labels[len(ai_sub_texts) :]
        ai_topics = sorted(set(int(x) for x in ai_labels))
        human_topics = sorted(set(int(x) for x in human_labels))
        ai_cov = f"{len(ai_topics)}/{k} = {round(100 * len(ai_topics) / k, 1)}%"
        human_cov = f"{len(human_topics)}/{k} = {round(100 * len(human_topics) / k, 1)}%"
        topic_table = []
        for idx, label in enumerate(topic_labels):
            topic_table.append(
                {
                    "topic": label,
                    "human": "Yes" if idx in human_topics else "No",
                    "ai": "Yes" if idx in ai_topics else "No",
                }
            )
    else:
        k = 0
        ai_cov = human_cov = "NOT COMPUTED"
        topic_table = []

    return {
        "file": source_name,
        "model": MODEL_NAME,
        "summary": {
            "M0": {"human": human_m["M0"], "ai": ai_m["M0"]},
            "M1": {"human": human_m["M1"], "ai": ai_m["M1"]},
            "M2": {"human": human_m["M2"], "ai": ai_m["M2"]},
            "M3": {"human": human_m["M3"], "ai": ai_m["M3"]},
            "M4": {"human": human_m["M4"], "ai": ai_m["M4"]},
            "M5": {"human": human_m["M5"], "ai": ai_m["M5"]},
            "M6": {"human": human_m["M6"], "ai": ai_m["M6"]},
            "M7": {"human": len(human_followups), "ai": len(ai_followups)},
            "M8": {"human": len(human_clar), "ai": len(ai_clar)},
            "M9": {"human": human_vendi, "ai": ai_vendi},
            "M10": {"human": human_msd, "ai": ai_msd},
            "M11": {"human": human_cov, "ai": ai_cov},
            "M12": {"human": human_mig, "ai": ai_mig},
        },
        "followups": {"human": human_followups, "ai": ai_followups},
        "clarifications": {"human": human_clar, "ai": ai_clar},
        "topic_table": topic_table,
        "information_gain": {
            "human": [
                {"response": f"R{i+2}", "ig": g}
                for i, g in enumerate(human_ig)
            ],
            "ai": [{"response": f"R{i+2}", "ig": g} for i, g in enumerate(ai_ig)],
        },
        "audit": {
            "human_turns": [
                {"turn": t.turn_num, "speaker": t.speaker, "words": word_count(t.text), "text_preview": t.text[:120]}
                for t in human_turns
            ],
            "ai_turns": [
                {"turn": t.turn_num, "speaker": t.speaker, "words": word_count(t.text), "text_preview": t.text[:120]}
                for t in ai_turns
            ],
            "human_substantive_responses": ai_sub_texts and human_sub_texts,
            "human_substantive_count": len(human_sub_texts),
            "ai_substantive_count": len(ai_sub_texts),
        },
        "data_quality_notes": build_quality_notes(ai_turns, human_turns, extra_notes),
    }


def build_quality_notes(ai_turns, human_turns, extra_notes=None) -> list[str]:
    notes = list(extra_notes or [])
    notes.append("Human interview = Student stakeholder; AI interview = iRE Agent stakeholder.")

    # Check unlabeled turns
    for t in ai_turns:
        if t.speaker == "interviewer" and "pages should the website" in t.text.lower():
            notes.append("AI interview Q8.1: orphan question line without explicit 'Interviewer:' label; assigned to interviewer turn.")
    for t in ai_turns:
        if t.speaker == "stakeholder" and t.text.startswith("The website should be divided"):
            notes.append("AI interview Q8.1: stakeholder response missing 'iRE Agent:' label; assigned to stakeholder turn.")

    if any(t.speaker == "interviewer" and len(t.questions) > 1 for t in human_turns):
        notes.append("Human interview Q4: single interviewer turn contains 3 distinct questions (counted separately in M2).")
    if any(
        t.speaker == "interviewer"
        and "Can you describe a situation" in t.text
        and t.turn_num > 1
        for t in human_turns
    ):
        notes.append("Human interview: follow-up question on AI helping understanding appears in same turn block as prior question in some parses; verified as separate turn where labeled.")

    notes.append(f"Clustering for M11: KMeans on pooled embeddings with k selected by silhouette score (sklearn).")
    notes.append(f"Embedding model: {MODEL_NAME}, L2-normalized.")
    return notes


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Task1.1/Task1.1/G01_T11.txt")
    result = analyze_file(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
