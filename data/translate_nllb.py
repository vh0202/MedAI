"""Translate English medical Q&A to Vietnamese via NLLB-200 (free).

Strategy:
  - Use facebook/nllb-200-distilled-600M (free, ~2.4 GB, fits Colab T4 easily)
  - Translate top-K English samples (e.g., 25k from MedQA + MedMCQA)
  - Output JSONL: {question_vi, answer_vi, source: "...", task: "qa"}
  - Human review recommended for ~1k critical samples (drug dosages, pediatric)

Usage (Colab T4, ~30-60 min for 25k samples):
    python data/translate_nllb.py --input data/english/medqa_subset.jsonl \
        --output data/translation_qa/en2vi.jsonl --limit 25000
"""
import argparse
import json
from pathlib import Path
from typing import Iterator


# Vietnamese medical terms that NLLB often gets wrong — post-process replacements
GLOSSARY_FIXES = {
    "myocardial infarction": "nhồi máu cơ tim",
    "acute kidney injury": "tổn thương thận cấp",
    "chronic kidney disease": "bệnh thận mạn",
    "diabetes mellitus": "đái tháo đường",
    "hypertension": "tăng huyết áp",
    "atrial fibrillation": "rung nhĩ",
    "pneumonia": "viêm phổi",
    "stroke": "đột quỵ",
    "ECG lead V1": "chuyển đạo V1 (ECG)",
    "ECG lead V2": "chuyển đạo V2 (ECG)",
    "ECG lead V3": "chuyển đạo V3 (ECG)",
    "ECG lead V4": "chuyển đạo V4 (ECG)",
    "mg/dL": "mg/dL",  # keep units intact
    "mmol/L": "mmol/L",
    "mmHg": "mmHg",
}


def apply_glossary(text: str) -> str:
    # Case-insensitive replace, but preserve unit casing
    import re
    for en, vi in GLOSSARY_FIXES.items():
        text = re.sub(re.escape(en), vi, text, flags=re.IGNORECASE)
    return text


def iter_jsonl(path: str) -> Iterator[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSONL with {question, answer} or {messages}")
    ap.add_argument("--output", required=True)
    ap.add_argument("--limit", type=int, default=25000)
    ap.add_argument("--model", default="facebook/nllb-200-distilled-600M")
    ap.add_argument("--batch_size", type=int, default=16)
    args = ap.parse_args()

    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[device] {device}")

    print(f"[model] Loading {args.model} ...")
    tok = AutoTokenizer.from_pretrained(args.model, src_lang="eng_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model).to(device)
    model.eval()
    vi_id = tok.convert_tokens_to_ids("vie_Latn")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    def translate_batch(texts: list[str]) -> list[str]:
        inputs = tok(texts, return_tensors="pt", padding=True, truncation=True, max_length=512).to(device)
        with torch.no_grad():
            generated = model.generate(
                **inputs,
                forced_bos_token_id=vi_id,
                max_length=512,
                num_beams=2,
            )
        return [apply_glossary(t) for t in tok.batch_decode(generated, skip_special_tokens=True)]

    written = 0
    buffer_q, buffer_a, buffer_meta = [], [], []

    def flush():
        nonlocal written
        if not buffer_q:
            return
        q_vi = translate_batch(buffer_q)
        a_vi = translate_batch(buffer_a)
        with open(out, "a", encoding="utf-8") as f:
            for i, meta in enumerate(buffer_meta):
                f.write(json.dumps({
                    "question_vi": q_vi[i],
                    "answer_vi": a_vi[i],
                    "question_en": buffer_q[i],
                    "answer_en": buffer_a[i],
                    "task": meta.get("task", "qa"),
                    "source": meta.get("source", "unknown"),
                }, ensure_ascii=False) + "\n")
        written += len(buffer_q)
        buffer_q.clear()
        buffer_a.clear()
        buffer_meta.clear()
        print(f"  [progress] {written} translated")

    print(f"[translate] {args.input} → {args.output}")
    if out.exists():
        out.unlink()  # fresh file

    for i, row in enumerate(iter_jsonl(args.input)):
        if i >= args.limit:
            break
        # Support both {question, answer} and {messages: [{role, content}]}
        if "messages" in row:
            msgs = row["messages"]
            user_msg = next((m["content"] for m in msgs if m["role"] == "user"), "")
            asst_msg = next((m["content"] for m in msgs if m["role"] == "assistant"), "")
            q, a = user_msg, asst_msg
        else:
            q, a = row.get("question", ""), row.get("answer", "")
        if not q or not a:
            continue
        buffer_q.append(q[:1500])
        buffer_a.append(a[:1500])
        buffer_meta.append({"task": row.get("task", "qa"), "source": row.get("source", args.input)})
        if len(buffer_q) >= args.batch_size:
            flush()

    flush()
    print(f"\n=== Done: {written} translated → {out} ===")
    print("⚠️  Recommended: human-review ~1k critical samples (drug doses, pediatric, dosage units)")


if __name__ == "__main__":
    main()
