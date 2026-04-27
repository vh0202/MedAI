# MedAI — Phương pháp luận

## Mục tiêu

Xây dựng một **trợ lý AI y tế song ngữ Việt-Anh** thực sự hữu ích với **chi phí $0**, chỉ dùng compute miễn phí (Kaggle P100 + Colab T4), để phương pháp này có thể tái lặp được bởi sinh viên, phòng khám, và nhà nghiên cứu ở môi trường thiếu nguồn lực.

## Lý do cho từng quyết định

### Vì sao chọn Qwen2.5-7B-Instruct làm base

- **Apache 2.0** — license sạch, có thể release adapter tự do.
- **Tokenizer multilingual tốt nhất ở size này** — tỉ lệ token/âm-tiết tiếng Việt ~1.3, so với Llama ~1.6. Tokenization tốt hơn = nhiều nội dung hơn trong context, inference nhanh hơn, training rẻ hơn mỗi epoch.
- **Hỗ trợ Unsloth mạnh** — sẵn checkpoint pre-quantized 4-bit + công thức QLoRA đã test.
- **7B là điểm ngọt** cho 16 GB VRAM của T4/P100 free. Lớn hơn đòi hỏi multi-GPU hoặc tier trả phí.

> **Phương án dự phòng**: nếu `eval/tokenizer_test.py` cho ra >2.5 token/âm-tiết với thuật ngữ y khoa Việt, chuyển sang `Viet-Mistral/Vistral-7B-Chat`.

### Vì sao QLoRA, không full fine-tune

Full fine-tune mô hình 7B cần ~80 GB VRAM và rất nhiều giờ GPU. QLoRA (base 4-bit + adapter low-rank) chỉ cần ~12-14 GB và đánh đổi chỉ ~1-2% độ chính xác. Đây là chuẩn công nghiệp 2025-2026.

### Vì sao single mixed LoRA, không 4 LoRA riêng theo task

| | Single mixed LoRA (đã chọn) | Multi-LoRA |
|---|---|---|
| Compute cost | 1× | 4× |
| Cross-task transfer | Có (giúp grounding) | Không |
| Deployment | 1 adapter | Phải switch adapter |
| Phù hợp khi | Dataset <100k mỗi task | Dataset >100k mỗi task và tasks rất khác biệt |

Ta dùng **task tag** prefix (`<task:qa>`, `<task:summary>`, `<task:edu>`, `<task:dx_edu>`) để model học task conditioning mà không cần adapter riêng.

### Vì sao 60/40 EN/VI (không 50/50, không 70/30)

- 50/50 underfit English benchmark (MedQA, PubMedQA).
- 70/30 khiến thuật ngữ tiếng Việt bị thiếu exposure.
- 60/40 với VI upsample 2-3× cân bằng cả hai, tận dụng cross-lingual transfer đã có trong pretraining của Qwen.

### Vì sao Kaggle P100 chính, không Colab T4

| | Kaggle P100 | Colab T4 |
|---|---|---|
| Session limit | 9h cứng | 12h mềm (idle disconnect ~6-8h thực tế) |
| Quota tuần | 30h | không giới hạn (nhưng không ổn định) |
| VRAM | 16 GB | 16 GB |
| Tốc độ | ~1.0× | ~0.85× |
| Độ ổn định | Ổn định | Hay disconnect |

Kaggle dễ dự đoán hơn. Colab dùng làm backup cho iterate nhanh trên subset nhỏ.

### Vì sao "Giáo dục Chẩn đoán Phân biệt", không "Chẩn đoán Lâm sàng"

Một công cụ hỗ trợ-quyết-định lâm sàng cần chứng nhận quản lý (FDA ở Mỹ, CE ở EU, Bộ Y tế / thiết bị y tế Class B ở Việt Nam). Một **công cụ giáo dục cho sinh viên y khoa** thì không — nó thuộc nội dung giáo dục, không phải thiết bị y tế.

Ta diễn đạt lại prompt: *"Với các triệu chứng X, sinh viên y khoa nên cân nhắc các chẩn đoán phân biệt nào?"* — rõ ràng là tài liệu học, không phải khuyến nghị lâm sàng.

### Vì sao cần DPO/SFT refusal training, dù ngân sách $0

LLM y tế không có safety alignment sẽ:
- Khuyến nghị liều cụ thể
- Tư vấn cấp cứu có thể làm chậm chăm sóc thực sự
- Phản ứng sai với ý nghĩ tự sát / tự hại

Ta tổng hợp ~2k mẫu refusal phủ: kê liều, cấp cứu, nhi khoa/thai kỳ, tự hại. SFT trên dataset này là đủ ở quy mô của ta; DPO tốt hơn nhưng tùy chọn vì tốn compute.

## Pipeline huấn luyện

```
[base: Qwen2.5-7B-Instruct]
        │
        ├── QLoRA load (4-bit, r=16, all linear)
        │
        ├── Phase 1: SFT trên 50k Q&A song ngữ (~10-14h)
        │     ├── tag: <task:qa>
        │     └── checkpoint mỗi 500 step → HF Hub
        │
        ├── Phase 2: tiếp tục SFT thêm +20k summary+edu (~5h)
        │     ├── tag: <task:summary>, <task:edu>
        │     └── replay 10% data Phase 1 (chống forgetting)
        │
        ├── Phase 3: tiếp tục SFT thêm +10k dx_edu + 2k refusal (~3h)
        │     ├── tag: <task:dx_edu>
        │     ├── LR thấp hơn (1e-4) cho safety
        │     └── replay 10% Phase 1+2
        │
        └── Phase 4: merge → GGUF Q4_K_M (~4 GB) → Ollama / HF Space
```

## Chiến lược đánh giá

- **Test set đông cứng** xây **TRƯỚC** training để tránh contamination.
- **MedQA / PubMedQA**: benchmark chuẩn, tự động.
- **VN frozen benchmark**: 500 câu tự xây từ sách giáo khoa y khoa Việt và đề thi, format JSON kèm đáp án tham chiếu.
- **Safety refusal eval**: 100 prompt phủ liều, cấp cứu, nhi, tự hại, tự sát — auto bằng keyword + LLM-as-judge.
- **Manual review**: bác sĩ hoặc sinh viên y kiểm tra 50-100 output mỗi phase.

## Minh bạch chi phí

| Tài nguyên | Chi phí |
|---|---|
| Compute (training) | $0 — Kaggle 30h/tuần + Colab T4 free |
| Storage (HF Hub) | $0 — quota free 50 GB |
| Storage (GitHub) | $0 — chỉ code, không weight |
| Dataset | $0 — toàn bộ license mở |
| Inference (deploy) | $0 — Ollama local, HF Space CPU free |
| **Tổng tiền mặt** | **$0** |
| **Tổng thời gian** | **~3-5 tuần** |

## Tái lặp

1. Clone https://github.com/vh0202/MedAI
2. Tạo tài khoản HuggingFace, lưu `HF_TOKEN` vào Kaggle/Colab Secrets
3. Mở `notebooks/kaggle_qlora.ipynb` trong Kaggle (GPU P100 + Internet)
4. Chạy cell từ trên xuống; cell resume sẵn nếu bị kill
5. Phase 1 mất ~10-14h trên P100 → checkpoint trên HF Hub
6. Lặp lại cho Phase 2, 3, 4 với phase override trong config

Xem [`methodology_en.md`](methodology_en.md) cho bản tiếng Anh.
