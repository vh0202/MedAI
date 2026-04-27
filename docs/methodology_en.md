# MedAI — Methodology

## Goal

Build a useful **bilingual (Vietnamese-English) medical assistant** on **$0 cash**, using only free-tier compute (Kaggle P100 + Colab T4), so the methodology is reproducible by students, clinics, and researchers in low-resource settings.

## Why these choices

### Why Qwen2.5-7B-Instruct as base

- **Apache 2.0** — clean license for both code and adapter release.
- **Best multilingual tokenizer at this size** — the Vietnamese token-per-syllable ratio is ~1.3, compared with ~1.6 for Llama-family. Better tokenization means more content per context, faster inference, and lower training cost per epoch.
- **Strong Unsloth support** — pre-quantized 4-bit checkpoints + tested QLoRA recipes.
- **7B is the sweet spot** for free-tier 16 GB VRAM (T4 / P100). Larger needs multi-GPU or paid tier.

> **Fallback**: if `eval/tokenizer_test.py` shows >2.5 tok/syllable on Vietnamese medical terms, switch to `Viet-Mistral/Vistral-7B-Chat`.

### Why QLoRA and not full fine-tuning

Full fine-tuning of a 7B model needs ~80 GB VRAM and many GPU-hours. QLoRA (4-bit base + low-rank adapter) needs ~12-14 GB and trades only ~1-2% accuracy. Industry standard in 2025-2026.

### Why a single mixed LoRA, not 4 task-specific LoRAs

| | Single mixed LoRA (chosen) | Multi-LoRA |
|---|---|---|
| Compute cost | 1× | 4× |
| Cross-task transfer | Yes (helps grounding) | No |
| Deployment | Single adapter | Adapter switching needed |
| Best when | Datasets <100k per task | Datasets >100k per task and tasks are very distinct |

We add a **task tag** prefix (`<task:qa>`, `<task:summary>`, `<task:edu>`, `<task:dx_edu>`) so the model can learn task conditioning without separate adapters.

### Why 60/40 EN/VI (not 50/50, not 70/30)

- 50/50 underfits English benchmarks (MedQA, PubMedQA).
- 70/30 leaves Vietnamese terminology underrepresented.
- 60/40 with VI upsampled 2-3× balances both, leveraging cross-lingual transfer in Qwen's pretraining.

### Why Kaggle P100 primary, not Colab T4

| | Kaggle P100 | Colab T4 |
|---|---|---|
| Session limit | 9 h hard | 12 h soft (idle disconnect ~6-8 h actual) |
| Weekly quota | 30 h | unlimited (but flaky) |
| VRAM | 16 GB | 16 GB |
| Speed | ~1.0× | ~0.85× |
| Reliability | Stable | Frequent disconnects |

Kaggle is more predictable. Colab is the backup for fast iteration on small subsets.

### Why "Differential Diagnosis Education" not "Clinical Diagnosis"

A clinical-decision-support tool would require regulatory clearance (FDA in US, CE in EU, Bộ Y tế / Class B medical device in Vietnam). An **educational tool for medical students** does not — it falls under educational content, not medical device.

We rephrase prompts as: *"Given symptoms X, what differentials should a medical student consider?"* — explicitly framed as study aid, not clinical recommendation.

### Why DPO/SFT refusal training, even at $0 budget

Medical LLMs without safety alignment will:
- Recommend specific dosages
- Give triage advice that may delay emergency care
- Engage with self-harm / suicide ideation incorrectly

We synthesize ~2k refusal examples covering: dosage prescription, emergency triage, pediatric/pregnancy specifics, self-harm. SFT on these samples is enough at our scale; DPO is preferred but optional given compute.

## Training pipeline

```
[base: Qwen2.5-7B-Instruct]
        │
        ├── QLoRA load (4-bit, r=16, all linear)
        │
        ├── Phase 1: SFT on 50k bilingual Q&A (~10-14 h)
        │     ├── tag: <task:qa>
        │     └── checkpoint every 500 steps → HF Hub
        │
        ├── Phase 2: continue SFT on +20k summary+edu (~5 h)
        │     ├── tags: <task:summary>, <task:edu>
        │     └── replay 10% Phase 1 data (anti-forgetting)
        │
        ├── Phase 3: continue SFT on +10k dx_edu + 2k refusal (~3 h)
        │     ├── tag: <task:dx_edu>
        │     ├── lower LR (1e-4) for safety
        │     └── replay 10% Phase 1+2
        │
        └── Phase 4: merge → GGUF Q4_K_M (~4 GB) → Ollama / HF Space
```

## Evaluation strategy

- **Frozen test sets** built **before training** to prevent contamination.
- **MedQA / PubMedQA**: standard benchmarks, automated.
- **VN frozen benchmark**: 500 questions hand-curated from Vietnamese medical textbooks and exam questions, JSON format with reference answers.
- **Safety refusal eval**: 100 prompts spanning dosage, emergency, pediatric, self-harm, suicide — automated keyword + LLM-as-judge for refusal compliance.
- **Manual review**: medical-student or physician spot-check on 50-100 outputs per phase.

## Cost transparency

| Resource | Cost |
|---|---|
| Compute (training) | $0 — Kaggle 30 h/week + Colab T4 free |
| Storage (HF Hub) | $0 — 50 GB free quota |
| Storage (GitHub) | $0 — code only, no model weights |
| Datasets | $0 — all open-license |
| Inference (deploy) | $0 — local Ollama, free HF Space CPU |
| **Total cash** | **$0** |
| **Total time** | **~3-5 weeks** |

## Reproducing

1. Clone https://github.com/vh0202/MedAI
2. Create HuggingFace account, set `HF_TOKEN` in Kaggle/Colab Secrets
3. Open `notebooks/kaggle_qlora.ipynb` in Kaggle (P100 GPU + Internet)
4. Run cells top-to-bottom; resume cell ready if killed
5. Phase 1 takes ~10-14 h on P100 → checkpoint on HF Hub
6. Repeat for Phase 2, 3, 4 with config phase overrides

See [`methodology_vi.md`](methodology_vi.md) for the Vietnamese version.
