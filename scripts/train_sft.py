"""SFT training entry-point for MedAI — Unsloth + QLoRA + TRL.

Designed to fit Kaggle P100 (16 GB) and Colab T4 free tier.

Usage:
    python scripts/train_sft.py \
        --config configs/qwen25_7b_qlora.yaml \
        --data data/phase1_mix.jsonl \
        [--resume_from auto]      # auto = latest checkpoint in output_dir or HF Hub

Resume safety:
    - Checkpoints every save_steps (default 500) → output_dir + HF Hub
    - On Kaggle 9-h kill: re-run with --resume_from auto, training continues seamlessly
"""
import argparse
import json
import os
from pathlib import Path

import yaml


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_latest_checkpoint(output_dir: str) -> str | None:
    p = Path(output_dir)
    if not p.exists():
        return None
    ckpts = sorted(
        [d for d in p.iterdir() if d.is_dir() and d.name.startswith("checkpoint-")],
        key=lambda d: int(d.name.split("-")[1]),
    )
    return str(ckpts[-1]) if ckpts else None


def format_chatml(example: dict) -> dict:
    """Convert {messages: [...]} to ChatML text via tokenizer chat template."""
    return example  # actual templating done by SFTTrainer with tokenizer.apply_chat_template


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config")
    ap.add_argument("--data", required=True, help="Path to JSONL training data")
    ap.add_argument(
        "--resume_from",
        default=None,
        help='Resume path or "auto" to find latest checkpoint',
    )
    ap.add_argument("--phase", default=None, help="Apply phase override block from config")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.phase and f"phase_{args.phase}" in cfg:
        for dotted_key, value in cfg[f"phase_{args.phase}"].items():
            section, key = dotted_key.split(".")
            cfg[section][key] = value
        print(f"[config] Applied phase_{args.phase} overrides")

    # Lazy imports — Unsloth must be imported before transformers for its patches
    from unsloth import FastLanguageModel, is_bfloat16_supported
    from datasets import load_dataset
    from trl import SFTTrainer, SFTConfig

    print(f"[model] Loading {cfg['model']['name']} ...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=cfg["model"]["name"],
        max_seq_length=cfg["model"]["max_seq_length"],
        dtype=None,
        load_in_4bit=cfg["model"]["load_in_4bit"],
    )

    print("[lora] Adding LoRA adapters ...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=cfg["lora"]["r"],
        lora_alpha=cfg["lora"]["alpha"],
        lora_dropout=cfg["lora"]["dropout"],
        bias=cfg["lora"]["bias"],
        target_modules=cfg["lora"]["target_modules"],
        use_gradient_checkpointing=cfg["lora"]["use_gradient_checkpointing"],
        use_rslora=cfg["lora"]["use_rslora"],
        random_state=cfg["lora"]["random_state"],
    )

    print(f"[data] Loading {args.data} ...")
    ds = load_dataset("json", data_files=args.data, split="train")

    def to_text(example):
        # Expect example["messages"] = [{"role": ..., "content": ...}, ...]
        text = tokenizer.apply_chat_template(
            example["messages"], tokenize=False, add_generation_prompt=False
        )
        return {"text": text}

    if "messages" in ds.column_names:
        ds = ds.map(to_text, remove_columns=ds.column_names)
    print(f"[data] Loaded {len(ds)} samples")
    print(f"[data] Sample 0:\n{ds[0]['text'][:500]}\n...")

    # Resolve resume
    resume = args.resume_from
    if resume == "auto":
        resume = find_latest_checkpoint(cfg["training"]["output_dir"])
        print(f"[resume] auto -> {resume!r}")

    t = cfg["training"]
    sft_cfg = SFTConfig(
        per_device_train_batch_size=t["per_device_train_batch_size"],
        gradient_accumulation_steps=t["gradient_accumulation_steps"],
        warmup_steps=t["warmup_steps"],
        num_train_epochs=t["num_train_epochs"],
        learning_rate=t["learning_rate"],
        embedding_learning_rate=t.get("embedding_learning_rate"),
        logging_steps=t["logging_steps"],
        save_strategy=t["save_strategy"],
        save_steps=t["save_steps"],
        save_total_limit=t["save_total_limit"],
        optim=t["optim"],
        weight_decay=t["weight_decay"],
        lr_scheduler_type=t["lr_scheduler_type"],
        seed=t["seed"],
        bf16=is_bfloat16_supported() and t.get("bf16", True),
        fp16=not is_bfloat16_supported() or t.get("fp16", False),
        report_to=t["report_to"],
        output_dir=t["output_dir"],
        push_to_hub=t.get("push_to_hub", False),
        hub_model_id=t.get("hub_model_id"),
        hub_strategy=t.get("hub_strategy", "every_save"),
        hub_private_repo=t.get("hub_private_repo", False),
        max_seq_length=cfg["model"]["max_seq_length"],
        packing=cfg["dataset"].get("packing", False),
        dataset_text_field=cfg["dataset"].get("text_field", "text"),
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=ds,
        args=sft_cfg,
    )

    print("[train] Starting ...")
    trainer.train(resume_from_checkpoint=resume)

    print("[save] Final adapter ...")
    trainer.save_model(t["output_dir"])
    tokenizer.save_pretrained(t["output_dir"])

    if t.get("push_to_hub"):
        print(f"[push] {t['hub_model_id']}")
        trainer.push_to_hub()

    # Persist final metrics
    metrics_path = Path(t["output_dir"]) / "training_metrics.json"
    if hasattr(trainer.state, "log_history"):
        with open(metrics_path, "w") as f:
            json.dump(trainer.state.log_history, f, indent=2, default=str)
        print(f"[save] Metrics → {metrics_path}")


if __name__ == "__main__":
    main()
