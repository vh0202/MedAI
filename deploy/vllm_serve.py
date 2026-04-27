"""Optional: serve merged MedAI via vLLM for higher-throughput API.

Requires: pip install vllm
Run on machine with >= 16 GB GPU.

    python deploy/vllm_serve.py --model vh0202/medai-qwen25-7b-merged --port 8000
"""
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--max_model_len", type=int, default=4096)
    ap.add_argument("--gpu_memory_utilization", type=float, default=0.85)
    args = ap.parse_args()

    import subprocess
    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", args.model,
        "--host", args.host,
        "--port", str(args.port),
        "--max-model-len", str(args.max_model_len),
        "--gpu-memory-utilization", str(args.gpu_memory_utilization),
        "--chat-template", "auto",
    ]
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
