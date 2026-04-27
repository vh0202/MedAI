# MedAI

> **Open-source bilingual (Vietnamese–English) medical AI** — Qwen2.5-7B QLoRA fine-tune for medical Q&A, clinical summarization, medical education, and differential-diagnosis training.
>
> **AI y tế song ngữ Việt-Anh mã nguồn mở** — fine-tune Qwen2.5-7B bằng QLoRA cho hỏi-đáp y khoa, tóm tắt hồ sơ bệnh án, giáo dục y khoa và luyện chẩn đoán phân biệt.

> ⚠️ **Educational / research use only — NOT a substitute for professional medical advice.** See [DISCLAIMER.md](DISCLAIMER.md).

---

## Why this project

Most medical LLMs are English-only and trained on cloud GPUs costing thousands of dollars. MedAI is a deliberate experiment to build a useful bilingual (Vietnamese + English) medical assistant **on a $0 cash budget** using only free-tier compute (Kaggle P100 / Colab T4) — to make the methodology reproducible for students, researchers, and small clinics in low-resource settings.

| Goal | Choice |
|---|---|
| Base model | **Qwen2.5-7B-Instruct** (Apache 2.0, multilingual, best VN tokenizer in class) |
| Training | **Unsloth + QLoRA 4-bit + TRL SFT** (fits 16 GB VRAM, ~2× speed) |
| Compute | **Kaggle P100 (primary) + Colab T4 (backup)** — free tier only |
| Strategy | Single mixed-instruction LoRA with task tags (`<task:qa>`, `<task:summary>`, `<task:edu>`, `<task:dx_edu>`) |
| Languages | 60% English / 40% Vietnamese (with VI upsampling) |
| Deployment | GGUF Q4_K_M (Ollama, ~4 GB) + HF Space demo |

---

## Roadmap

- **Phase 0 — Setup** ✅ scaffold, configs, tokenizer test
- **Phase 1 — MVP Q&A bilingual** (1–2 weeks)
- **Phase 2 — Summarization + Medical Education** (1 week)
- **Phase 3 — Differential Diagnosis Education + Safety alignment** (1 week)
- **Phase 4 — Quantize (GGUF) + Deploy (Ollama, HF Space)** (2–3 days)

See [`docs/methodology_en.md`](docs/methodology_en.md) / [`docs/methodology_vi.md`](docs/methodology_vi.md).

---

## Repo structure

```
configs/      training hyperparameters (YAML)
data/         dataset preparation: english/, vietnamese/, translation_qa/, safety/
scripts/      train_sft.py, resume_training.py, merge_lora.py, quantize_gguf.sh
notebooks/    Kaggle / Colab QLoRA notebooks
eval/         MedQA, PubMedQA, VN frozen benchmark, safety refusal eval, tokenizer test
deploy/       Ollama Modelfile, vLLM serve, HF Space Gradio app
docs/         methodology (VI/EN), safety alignment notes
```

## Quick start (training)

```bash
# 1. Install (in Kaggle/Colab notebook)
pip install -q unsloth transformers trl peft bitsandbytes datasets accelerate

# 2. Sanity-check tokenizer on VN medical terms
python eval/tokenizer_test.py

# 3. Prepare bilingual mixed dataset (Phase 1)
python data/prepare_bilingual_mix.py --phase 1 --out data/phase1_mix.jsonl

# 4. Train (Kaggle P100 ~10–14 h, 2 epochs, ~50k samples)
python scripts/train_sft.py --config configs/qwen25_7b_qlora.yaml --data data/phase1_mix.jsonl

# 5. Resume after Kaggle 9-h timeout
python scripts/resume_training.py --checkpoint hf://vh0202/medai-phase1-ckpt
```

## Quick start (inference, after Phase 4)

```bash
# Local via Ollama
ollama run vh0202/medai-7b-q4

# Or HF Space demo (browser)
# https://huggingface.co/spaces/vh0202/medai-demo
```

---

## Datasets

**English** — MedQA-USMLE, MedMCQA, PubMedQA, ChatDoctor / HealthCareMagic, MedAlpaca, Meditron clinical guidelines.
**Vietnamese** — ViMedical_Disease, ViMQ, VietMed-MCQ + ~25 k EN→VI samples translated via NLLB-200 (with human review for critical drug/dosage terms).

Mix: 60 % EN / 40 % VI, with VI upsampled 2–3× to compensate for smaller volume.

> **License caveats**: ChatDoctor and MedAlpaca are non-commercial. Adapter weights are released under Apache 2.0 but the dataset mix contains NC components — research / educational use only.

---

## Evaluation targets

| Benchmark | Baseline (Qwen2.5-7B) | Phase 1 target | Phase 3 target |
|---|---|---|---|
| MedQA-USMLE | ~45 % | ≥ 50 % | ≥ 60 % |
| PubMedQA | ~60 % | ≥ 70 % | ≥ 70 % |
| VN frozen benchmark (500 q) | manual | ≥ 60 % | ≥ 70 % |
| Safety refusal rate (100 prompts) | low | — | ≥ 95 % |

---

## License

Code: Apache 2.0 — see [LICENSE](LICENSE).
Adapter weights: Apache 2.0.
Training data: mixed (some non-commercial) — see [MODEL_CARD.md](MODEL_CARD.md).

## Contributing

Issues and PRs welcome — especially Vietnamese medical eval contributions and translation reviews. Please read [DISCLAIMER.md](DISCLAIMER.md) before opening medically-sensitive issues.
