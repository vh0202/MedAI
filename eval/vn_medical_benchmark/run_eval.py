"""Evaluate MedAI on the frozen Vietnamese medical benchmark."""
import argparse
import json
import re
from pathlib import Path

TEST_SET = Path(__file__).parent / "test_set.jsonl"

SYSTEM = (
    "Bạn là trợ lý AI y khoa song ngữ. Với câu hỏi trắc nghiệm, trả lời bằng chữ cái "
    "(A/B/C/D) kèm giải thích ngắn. Với câu hỏi mở, trả lời ngắn gọn, có dẫn chứng."
)


def parse_letter(text: str) -> str | None:
    m = re.search(r"\b([A-E])\b", text.strip()[:30])
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--base", default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit")
    ap.add_argument("--out", default="eval/results/vn_benchmark_results.json")
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    args = ap.parse_args()

    if not TEST_SET.exists():
        raise SystemExit(f"Missing {TEST_SET} — run build_test_set.py first")

    from unsloth import FastLanguageModel
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base, max_seq_length=2048, dtype=None, load_in_4bit=True,
    )
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter)
    FastLanguageModel.for_inference(model)

    rows = []
    with open(TEST_SET, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    if args.limit:
        rows = rows[: args.limit]

    mc_correct = 0
    mc_total = 0
    open_outputs = []  # for downstream judge / manual review

    for i, row in enumerate(rows):
        q = row["question"]
        opts = row.get("options")
        gold = row["answer"]

        if opts:
            opts_str = "\n".join(f"{k}. {v}" for k, v in opts.items())
            user = f"<task:qa> {q}\n\n{opts_str}"
        else:
            user = f"<task:qa> {q}"

        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=128, do_sample=False, temperature=0.0)
        text = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        if opts:
            pred = parse_letter(text)
            ok = pred == gold
            mc_correct += int(ok)
            mc_total += 1
        else:
            ok = None
            open_outputs.append({"id": row["id"], "q": q, "gold": gold, "model": text})

        if (i + 1) % 25 == 0 and mc_total:
            print(f"  [{i+1}/{len(rows)}] MC acc = {mc_correct/mc_total:.3f}")

    mc_acc = mc_correct / mc_total if mc_total else 0.0
    print(f"\n=== VN benchmark MC accuracy: {mc_acc:.3f} ({mc_correct}/{mc_total}) ===")
    print(f"=== Open-ended outputs: {len(open_outputs)} (manual review or LLM-judge needed) ===")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "adapter": args.adapter,
            "mc_accuracy": mc_acc,
            "mc_total": mc_total,
            "open_outputs": open_outputs[:50],  # cap for log size
        }, f, indent=2, ensure_ascii=False)
    print(f"[save] {out_path}")


if __name__ == "__main__":
    main()
