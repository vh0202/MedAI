"""Merge LoRA adapter into base model and save as a full model directory.

Use after final SFT phase, before quantizing to GGUF.

    python scripts/merge_lora.py \
        --base unsloth/Qwen2.5-7B-Instruct-bnb-4bit \
        --adapter outputs/qwen25-7b-medai-phase3 \
        --out outputs/medai-merged
"""
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--push_to_hub", default=None)
    args = ap.parse_args()

    from unsloth import FastLanguageModel

    print(f"[load] {args.base}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )

    print(f"[lora] Loading adapter from {args.adapter}")
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, args.adapter)

    print(f"[merge] Merging LoRA into base ...")
    # Unsloth recommends save_pretrained_merged for proper merge with quantized base
    model.save_pretrained_merged(args.out, tokenizer, save_method="merged_16bit")

    if args.push_to_hub:
        print(f"[push] {args.push_to_hub}")
        model.push_to_hub_merged(args.push_to_hub, tokenizer, save_method="merged_16bit")

    print(f"\n=== Merged model → {args.out} ===")
    print("Next: bash scripts/quantize_gguf.sh", args.out)


if __name__ == "__main__":
    main()
