---
language:
  - vi
  - en
license: apache-2.0
tags:
  - medical
  - bilingual
  - qlora
  - vietnamese
  - healthcare
base_model: Qwen/Qwen2.5-7B-Instruct
library_name: peft
pipeline_tag: text-generation
---

# MedAI — Bilingual (Vietnamese-English) Medical Assistant (QLoRA on Qwen2.5-7B)

> ⚠️ **Educational / research use only.** Not a medical device. See [DISCLAIMER](https://github.com/vh0202/MedAI/blob/main/DISCLAIMER.md).

## Model description

MedAI is a QLoRA adapter fine-tuned on top of `Qwen/Qwen2.5-7B-Instruct`, specialized for bilingual (Vietnamese + English) medical instruction following across four task types:

| Task tag | Use case |
|---|---|
| `<task:qa>` | Medical Q&A — patient-facing and student-facing |
| `<task:summary>` | Clinical-note / abstract summarization |
| `<task:edu>` | Medical education content |
| `<task:dx_edu>` | Differential-diagnosis exercises (educational, not clinical) |

## Intended use

✅ **Allowed**
- Medical-student practice questions
- Patient education (general health information)
- Literature summarization
- Differential-diagnosis exercises with medical-faculty oversight

❌ **Not allowed**
- Diagnosing real patients
- Prescribing or recommending dosages
- Emergency triage or clinical decision support without a licensed clinician
- Any commercial use (training data has non-commercial licenses)

## Training data

| Dataset | License | Lang | Used for |
|---|---|---|---|
| MedQA-USMLE | research | EN | qa |
| MedMCQA | research | EN | qa |
| PubMedQA-labeled | research | EN | qa |
| ChatDoctor / HealthCareMagic | **non-commercial** | EN | qa |
| MedAlpaca | **CC-BY-NC** | EN | qa |
| ViMedical_Disease | research | VI | qa |
| ViMQ | research | VI | qa |
| VietMed-MCQ | research | VI | qa |
| EN→VI NLLB-200 translations | derivative | VI | qa |
| Synthetic refusal dataset | Apache 2.0 (this repo) | EN+VI | safety |

Mix ratio: **60% EN / 40% VI** with VI upsampled 2-3×.

## Training details

- Base: `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`
- Method: **QLoRA** (4-bit base, rank-16 LoRA, all-linear targets)
- Compute: **Kaggle P100** (16 GB VRAM) — free tier
- Epochs: 2 (Phase 1), +1 (Phase 2), +1 (Phase 3)
- Effective batch size: 16 (per-device 2 × grad-accum 8)
- Learning rate: 2e-4 (1e-4 for Phase 3 safety alignment)
- Optimizer: paged_adamw_8bit
- Max seq length: 2048

## Evaluation (placeholder — will update after Phase 1)

| Benchmark | Baseline (Qwen2.5-7B) | MedAI Phase 1 | MedAI Phase 3 |
|---|---|---|---|
| MedQA-USMLE | ~45% | TBD | TBD |
| PubMedQA | ~60% | TBD | TBD |
| VN frozen benchmark (500 q) | TBD | TBD | TBD |
| Safety refusal rate | low | — | TBD |

## Limitations & biases

- **Hallucinations**: like all LLMs, MedAI fabricates plausible-but-wrong drug names, doses, and citations. Always verify against authoritative sources.
- **Vietnamese coverage**: smaller than English. Some specialized topics (pediatric pharmacology, traditional Vietnamese medicine) may underperform.
- **Translation drift**: NLLB-translated data may have subtle terminology errors despite the medical glossary post-processing. Human review covers ~1k critical samples.
- **Qwen base biases**: Qwen2.5 has learned filters around politically sensitive content; we did not retrain these. Medical questions about reproductive health or topics regulated differently across jurisdictions may trigger unnecessary refusals — adjust the system prompt if needed for legitimate research.
- **Eval gaps**: no peer-reviewed clinical validation. Do not use for any decision affecting patient outcomes.

## Citation

```bibtex
@misc{medai2026,
  title  = {MedAI: A Bilingual Vietnamese-English Medical Assistant via QLoRA on Qwen2.5-7B},
  author = {vh0202 and contributors},
  year   = {2026},
  url    = {https://github.com/vh0202/MedAI},
  note   = {Trained entirely on free-tier compute (Kaggle/Colab)}
}
```
