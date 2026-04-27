"""Evaluate MedAI on MedQA-USMLE test split.

Usage:
    python eval/medqa_eval.py --adapter outputs/qwen25-7b-medai-phase1 --limit 200
    python eval/medqa_eval.py --base unsloth/Qwen2.5-7B-Instruct-bnb-4bit  # baseline
"""
import argparse
import json
import re
from pathlib import Path


SYSTEM = (
    "You are a bilingual (Vietnamese-English) medical AI assistant. "
    "For multiple-choice questions, respond with the letter (A/B/C/D/E) followed by a brief justification."
)


def parse_answer(text: str) -> str | None:
    m = re.search(r"\b([A-E])\b", text.strip()[:30])
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default=None, help="Path or HF id of LoRA adapter to load on top of base")
    ap.add_argument("--base", default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--out", default="eval/results/medqa_results.json")
    args = ap.parse_args()

    from unsloth import FastLanguageModel
    from datasets import load_dataset

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter)

    FastLanguageModel.for_inference(model)

    print(f"[data] Loading MedQA test ...")
    ds = load_dataset(
        "bigbio/med_qa", "med_qa_en_4options_source",
        split="test", trust_remote_code=True,
    )

    correct = 0
    total = 0
    results = []

    for i, row in enumerate(ds):
        if i >= args.limit:
            break
        opts_dict = row["options"]
        if isinstance(opts_dict, list):
            opts_dict = {o["key"]: o["value"] for o in opts_dict}
        opts_str = "\n".join(f"{k}. {v}" for k, v in opts_dict.items())
        gold = row["answer_idx"]

        msgs = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"<task:qa> {row['question']}\n\n{opts_str}"},
        ]
        prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=64, do_sample=False, temperature=0.0)
        text = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        pred = parse_answer(text)
        ok = pred == gold
        correct += int(ok)
        total += 1
        results.append({"q_idx": i, "gold": gold, "pred": pred, "ok": ok, "raw": text[:200]})
        if (i + 1) % 25 == 0:
            print(f"  [{i+1}/{args.limit}] running acc = {correct/total:.3f}")

    acc = correct / total if total else 0.0
    print(f"\n=== MedQA accuracy: {acc:.3f} ({correct}/{total}) ===")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "adapter": args.adapter,
            "base": args.base,
            "limit": total,
            "accuracy": acc,
            "results": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"[save] {out_path}")


if __name__ == "__main__":
    main()
