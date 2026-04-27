"""Prepare bilingual (EN+VI) medical instruction dataset for SFT.

Output: JSONL where each line is {"messages": [...], "task": "qa|summary|edu|dx_edu", "lang": "en|vi"}.
Format follows ChatML — applied later by tokenizer.apply_chat_template in train_sft.py.

Phase 1 sources (Q&A):
  EN: MedQA-USMLE, MedMCQA, PubMedQA-labeled, ChatDoctor-HealthCareMagic, MedAlpaca
  VI: ViMedical_Disease, ViMQ, VietMed-MCQ
  Translated: ~25k EN samples translated to VI via translate_nllb.py

Mix ratio: 60% EN / 40% VI with VI upsampled 2-3× to fight underrepresentation.

Usage:
    python data/prepare_bilingual_mix.py --phase 1 --out data/phase1_mix.jsonl
"""
import argparse
import json
import random
from pathlib import Path
from typing import Iterator

random.seed(42)

SYSTEM_VI = (
    "Bạn là một trợ lý AI y khoa song ngữ Việt-Anh. Trả lời cẩn trọng, có dẫn chứng "
    "khi có thể, và LUÔN nhắc người dùng tham vấn bác sĩ khi câu hỏi liên quan đến "
    "chẩn đoán, kê đơn, hoặc quyết định lâm sàng cụ thể."
)
SYSTEM_EN = (
    "You are a bilingual (Vietnamese-English) medical AI assistant. Answer carefully "
    "with citations when possible, and ALWAYS remind the user to consult a licensed "
    "clinician for diagnostic, prescription, or treatment decisions."
)


def make_message(system: str, user: str, assistant: str, task: str, lang: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"<task:{task}> {user}".strip()},
            {"role": "assistant", "content": assistant},
        ],
        "task": task,
        "lang": lang,
    }


# ---------- Loaders (lazy: import datasets only when needed) ----------

def load_medqa_usmle() -> Iterator[dict]:
    from datasets import load_dataset
    ds = load_dataset("bigbio/med_qa", "med_qa_en_4options_source", split="train", trust_remote_code=True)
    for row in ds:
        opts = "\n".join(f"{k}. {v}" for k, v in row["options"].items()) if isinstance(row["options"], dict) else \
               "\n".join(f"{o['key']}. {o['value']}" for o in row["options"])
        user = f"{row['question']}\n\n{opts}"
        ans = row.get("answer_idx") or row.get("answer", "")
        explanation = row.get("answer", "")
        assistant = f"Answer: {ans}. {explanation}".strip()
        yield make_message(SYSTEM_EN, user, assistant, "qa", "en")


def load_medmcqa(limit: int = 50000) -> Iterator[dict]:
    from datasets import load_dataset
    ds = load_dataset("openlifescienceai/medmcqa", split="train")
    for i, row in enumerate(ds):
        if i >= limit:
            break
        opts = (
            f"A. {row['opa']}\nB. {row['opb']}\nC. {row['opc']}\nD. {row['opd']}"
        )
        ans_letter = ["A", "B", "C", "D"][row["cop"]]
        explanation = row.get("exp") or ""
        user = f"{row['question']}\n\n{opts}"
        assistant = f"Answer: {ans_letter}. {explanation}".strip()
        yield make_message(SYSTEM_EN, user, assistant, "qa", "en")


def load_pubmedqa() -> Iterator[dict]:
    from datasets import load_dataset
    ds = load_dataset("bigbio/pubmed_qa", "pubmed_qa_labeled_fold0_source", split="train", trust_remote_code=True)
    for row in ds:
        ctx = " ".join(row["context"]["contexts"]) if isinstance(row["context"], dict) else str(row["context"])
        user = f"Context:\n{ctx}\n\nQuestion: {row['question']}\nAnswer yes/no/maybe with brief reasoning."
        assistant = f"{row['final_decision']}. {row.get('long_answer', '')}".strip()
        yield make_message(SYSTEM_EN, user, assistant, "qa", "en")


def load_chatdoctor(limit: int = 30000) -> Iterator[dict]:
    from datasets import load_dataset
    # HealthCareMagic-100k subset of ChatDoctor
    ds = load_dataset("lavita/ChatDoctor-HealthCareMagic-100k", split="train")
    for i, row in enumerate(ds):
        if i >= limit:
            break
        yield make_message(SYSTEM_EN, row["input"], row["output"], "qa", "en")


def load_medalpaca(limit: int = 20000) -> Iterator[dict]:
    from datasets import load_dataset
    ds = load_dataset("medalpaca/medical_meadow_medqa", split="train")
    for i, row in enumerate(ds):
        if i >= limit:
            break
        user = row.get("input") or row.get("instruction", "")
        assistant = row.get("output", "")
        if user and assistant:
            yield make_message(SYSTEM_EN, user, assistant, "qa", "en")


def load_vimedical_disease() -> Iterator[dict]:
    from datasets import load_dataset
    try:
        ds = load_dataset("PB3002/ViMedical_Disease", split="train")
    except Exception as e:
        print(f"[warn] ViMedical_Disease load failed: {e}")
        return
    for row in ds:
        q = row.get("question") or row.get("input", "")
        a = row.get("answer") or row.get("output", "")
        if q and a:
            yield make_message(SYSTEM_VI, q, a, "qa", "vi")


def load_vimq() -> Iterator[dict]:
    """ViMQ — Vietnamese Medical Questions. Often comes as classification — convert to instruction."""
    from datasets import load_dataset
    candidates = ["tarudesu/ViMQ", "ViMQ"]
    ds = None
    for c in candidates:
        try:
            ds = load_dataset(c, split="train")
            break
        except Exception:
            continue
    if ds is None:
        print("[warn] ViMQ not available — skipping")
        return
    for row in ds:
        q = row.get("question") or row.get("text", "")
        intent = row.get("intent") or row.get("label", "")
        if q:
            assistant = f"Đây là câu hỏi y khoa thuộc nhóm '{intent}'. Bạn nên cung cấp thêm bối cảnh và tham vấn bác sĩ để có lời khuyên chính xác."
            yield make_message(SYSTEM_VI, q, assistant, "qa", "vi")


def load_translated_qa(path: str = "data/translation_qa/en2vi.jsonl") -> Iterator[dict]:
    """Pre-translated EN→VI samples produced by data/translate_nllb.py."""
    p = Path(path)
    if not p.exists():
        print(f"[warn] {path} not found — run data/translate_nllb.py first")
        return
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            yield make_message(
                SYSTEM_VI,
                row["question_vi"],
                row["answer_vi"],
                row.get("task", "qa"),
                "vi",
            )


# ---------- Phase recipes ----------

PHASE_RECIPES = {
    "1": {
        "en_loaders": [
            ("medqa", load_medqa_usmle, None),
            ("medmcqa", lambda: load_medmcqa(50000), 50000),
            ("pubmedqa", load_pubmedqa, None),
            ("chatdoctor", lambda: load_chatdoctor(30000), 30000),
            ("medalpaca", lambda: load_medalpaca(20000), 20000),
        ],
        "vi_loaders": [
            ("vimedical_disease", load_vimedical_disease, None),
            ("vimq", load_vimq, None),
            ("translated", load_translated_qa, None),
        ],
        "target_en": 30000,
        "target_vi": 20000,
        "vi_upsample": 2,
    },
}


def collect(loaders, max_total: int) -> list[dict]:
    rows = []
    for name, fn, _ in loaders:
        before = len(rows)
        try:
            for r in fn():
                rows.append(r)
                if len(rows) >= max_total:
                    break
        except Exception as e:
            print(f"[warn] {name} failed: {e}")
        print(f"  [{name}] +{len(rows) - before} → {len(rows)} total")
        if len(rows) >= max_total:
            break
    return rows[:max_total]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="1")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit_en", type=int, default=None)
    ap.add_argument("--limit_vi", type=int, default=None)
    args = ap.parse_args()

    recipe = PHASE_RECIPES[args.phase]
    target_en = args.limit_en or recipe["target_en"]
    target_vi = args.limit_vi or recipe["target_vi"]

    print(f"=== Phase {args.phase}: target {target_en} EN + {target_vi} VI (×{recipe['vi_upsample']} upsample) ===\n")

    print("--- English ---")
    en_rows = collect(recipe["en_loaders"], target_en)
    print(f"\n--- Vietnamese ---")
    vi_rows = collect(recipe["vi_loaders"], target_vi)

    # Upsample VI
    vi_final = vi_rows * recipe["vi_upsample"]
    print(f"\nUpsampled VI: {len(vi_rows)} → {len(vi_final)}")

    all_rows = en_rows + vi_final
    random.shuffle(all_rows)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n=== Wrote {len(all_rows)} samples → {out} ===")
    en_count = sum(1 for r in all_rows if r["lang"] == "en")
    vi_count = sum(1 for r in all_rows if r["lang"] == "vi")
    print(f"   EN: {en_count} ({en_count/len(all_rows):.0%})")
    print(f"   VI: {vi_count} ({vi_count/len(all_rows):.0%})")


if __name__ == "__main__":
    main()
