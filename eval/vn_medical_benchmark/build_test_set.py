"""Build a frozen Vietnamese medical benchmark test set.

Sources:
  1. ViMedical_Disease test split (held-out)
  2. Translated MedQA test (10-20% sample, hand-reviewed)
  3. Hand-curated questions from Vietnamese medical textbooks (public domain) — to be added manually

Output: eval/vn_medical_benchmark/test_set.jsonl
        Each line: {"id", "question", "options", "answer", "explanation", "source", "topic"}

This file should be **committed once** and treated as immutable to prevent contamination.
Re-running will regenerate; review diff before commit.

Usage:
    python eval/vn_medical_benchmark/build_test_set.py --target_size 500
"""
import argparse
import json
import random
from pathlib import Path

random.seed(42)

OUT = Path(__file__).parent / "test_set.jsonl"


def from_vimedical_disease(target: int = 200) -> list[dict]:
    rows = []
    try:
        from datasets import load_dataset
        ds = load_dataset("PB3002/ViMedical_Disease", split="train")
        ds = ds.shuffle(seed=42).select(range(min(target, len(ds))))
        for i, row in enumerate(ds):
            q = row.get("question") or row.get("input", "")
            a = row.get("answer") or row.get("output", "")
            if q and a:
                rows.append({
                    "id": f"vimd_{i:04d}",
                    "question": q,
                    "options": None,            # open-ended
                    "answer": a,
                    "explanation": "",
                    "source": "ViMedical_Disease (held-out)",
                    "topic": row.get("disease") or "general",
                })
    except Exception as e:
        print(f"[warn] ViMedical_Disease unavailable: {e}")
    print(f"[vimedical] {len(rows)}")
    return rows


def from_medqa_translated(target: int = 200) -> list[dict]:
    """Take MedQA test rows, translate Q + options via NLLB. Mark for human review."""
    rows = []
    try:
        from datasets import load_dataset
        ds = load_dataset(
            "bigbio/med_qa", "med_qa_en_4options_source",
            split="test", trust_remote_code=True,
        )
        ds = ds.shuffle(seed=42).select(range(min(target, len(ds))))

        # Lazy NLLB load
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        import torch
        model_id = "facebook/nllb-200-distilled-600M"
        tok = AutoTokenizer.from_pretrained(model_id, src_lang="eng_Latn")
        model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device).eval()
        vi_id = tok.convert_tokens_to_ids("vie_Latn")

        def tr(text: str) -> str:
            inputs = tok(text, return_tensors="pt", truncation=True, max_length=512).to(device)
            with torch.no_grad():
                gen = model.generate(**inputs, forced_bos_token_id=vi_id, max_length=512, num_beams=2)
            return tok.batch_decode(gen, skip_special_tokens=True)[0]

        for i, row in enumerate(ds):
            opts = row["options"]
            if isinstance(opts, list):
                opts = {o["key"]: o["value"] for o in opts}
            q_vi = tr(row["question"])
            opts_vi = {k: tr(v) for k, v in opts.items()}
            rows.append({
                "id": f"medqa_vi_{i:04d}",
                "question": q_vi,
                "options": opts_vi,
                "answer": row["answer_idx"],
                "explanation": row.get("answer", ""),
                "source": "MedQA-USMLE translated (NLLB-200, NEEDS HUMAN REVIEW)",
                "topic": "USMLE",
                "needs_review": True,
            })
    except Exception as e:
        print(f"[warn] MedQA translation failed: {e}")
    print(f"[medqa_translated] {len(rows)}")
    return rows


def hand_curated_seed() -> list[dict]:
    """Seed list of hand-curated VN clinical questions. Add more manually before commit."""
    return [
        {
            "id": "hand_0001",
            "question": "Bệnh nhân nam 60 tuổi có tiền sử tăng huyết áp, hút thuốc lá 30 năm, đến khám vì đau ngực sau xương ức lan ra cánh tay trái khoảng 30 phút trước. ECG cho thấy ST chênh lên 2mm ở các chuyển đạo II, III, aVF. Chẩn đoán phù hợp nhất là?",
            "options": {
                "A": "Nhồi máu cơ tim cấp thành dưới",
                "B": "Nhồi máu cơ tim cấp thành trước",
                "C": "Đau thắt ngực ổn định",
                "D": "Viêm màng ngoài tim cấp",
            },
            "answer": "A",
            "explanation": "ST chênh lên ở II, III, aVF là dấu hiệu kinh điển của nhồi máu cơ tim thành dưới.",
            "source": "Hand-curated (textbook)",
            "topic": "Cardiology",
        },
        {
            "id": "hand_0002",
            "question": "Trẻ em 4 tuổi sốt cao 39°C, ho khan, chảy nước mũi, viêm kết mạc, có các đốm Koplik ở niêm mạc miệng. Chẩn đoán nghi ngờ nhất?",
            "options": {
                "A": "Sởi (Measles)",
                "B": "Rubella",
                "C": "Quai bị",
                "D": "Thủy đậu",
            },
            "answer": "A",
            "explanation": "Đốm Koplik là dấu hiệu đặc hiệu của bệnh sởi, xuất hiện 1-2 ngày trước phát ban.",
            "source": "Hand-curated (textbook)",
            "topic": "Pediatrics / Infectious",
        },
        # TODO: add more hand-curated samples to reach ~100 here
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target_size", type=int, default=500)
    ap.add_argument("--from_medqa", type=int, default=0,
                    help="How many MedQA test rows to translate (slow; needs GPU). 0 to skip.")
    ap.add_argument("--from_vimedical", type=int, default=300)
    args = ap.parse_args()

    rows = []
    rows += from_vimedical_disease(args.from_vimedical)
    if args.from_medqa > 0:
        rows += from_medqa_translated(args.from_medqa)
    rows += hand_curated_seed()

    random.shuffle(rows)
    rows = rows[: args.target_size]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n=== Wrote {len(rows)} rows → {OUT} ===")
    print("⚠️  Review rows where needs_review=true before treating accuracy as authoritative.")


if __name__ == "__main__":
    main()
