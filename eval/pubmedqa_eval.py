"""Evaluate on PubMedQA labeled split (yes/no/maybe)."""
import argparse
import json
import re
from pathlib import Path


SYSTEM = "You are a medical AI assistant. Read the context and answer the question with exactly one of: yes / no / maybe."


def parse_yn(text: str) -> str | None:
    t = text.strip().lower()
    for token in ("yes", "no", "maybe"):
        if re.match(rf"\b{token}\b", t):
            return token
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--base", default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--out", default="eval/results/pubmedqa_results.json")
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

    ds = load_dataset(
        "bigbio/pubmed_qa", "pubmed_qa_labeled_fold0_source",
        split="test", trust_remote_code=True,
    )

    correct = 0
    total = 0
    results = []

    for i, row in enumerate(ds):
        if i >= args.limit:
            break
        ctx = " ".join(row["context"]["contexts"]) if isinstance(row["context"], dict) else str(row["context"])
        msgs = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"<task:qa> Context:\n{ctx[:2000]}\n\nQuestion: {row['question']}\nAnswer:"},
        ]
        prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=8, do_sample=False, temperature=0.0)
        text = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        pred = parse_yn(text)
        gold = row["final_decision"].strip().lower()
        ok = pred == gold
        correct += int(ok)
        total += 1
        results.append({"q_idx": i, "gold": gold, "pred": pred, "ok": ok})
        if (i + 1) % 25 == 0:
            print(f"  [{i+1}/{args.limit}] acc = {correct/total:.3f}")

    acc = correct / total if total else 0.0
    print(f"\n=== PubMedQA accuracy: {acc:.3f} ({correct}/{total}) ===")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"adapter": args.adapter, "accuracy": acc, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"[save] {out_path}")


if __name__ == "__main__":
    main()
