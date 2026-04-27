"""Resume training from latest checkpoint (HF Hub or local).

Use case: Kaggle session got killed at 9 h. Spin up a new session, run this.

    python scripts/resume_training.py \
        --config configs/qwen25_7b_qlora.yaml \
        --data data/phase1_mix.jsonl \
        --hub_repo vh0202/medai-qwen25-7b-phase1-ckpt
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def pull_from_hub(repo_id: str, local_dir: str) -> str:
    """Download latest checkpoint folder from HF Hub."""
    from huggingface_hub import snapshot_download

    print(f"[hub] Downloading {repo_id} → {local_dir}")
    path = snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
    )
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument(
        "--hub_repo",
        default=None,
        help="Pull checkpoint from this HF Hub repo first (recommended for Kaggle)",
    )
    ap.add_argument("--local_ckpt", default=None, help="Use this local path directly")
    ap.add_argument("--phase", default=None)
    args = ap.parse_args()

    if args.hub_repo:
        # Read output_dir from config to know where to download
        import yaml
        cfg = yaml.safe_load(open(args.config))
        out = cfg["training"]["output_dir"]
        Path(out).mkdir(parents=True, exist_ok=True)
        pull_from_hub(args.hub_repo, out)
        resume_arg = "auto"  # train_sft.py will find latest checkpoint-N folder
    elif args.local_ckpt:
        resume_arg = args.local_ckpt
    else:
        resume_arg = "auto"

    cmd = [
        sys.executable,
        "scripts/train_sft.py",
        "--config", args.config,
        "--data", args.data,
        "--resume_from", resume_arg,
    ]
    if args.phase:
        cmd += ["--phase", args.phase]

    print(f"[resume] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
