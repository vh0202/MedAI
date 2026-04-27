"""Tokenizer fragmentation test for Vietnamese medical terms.

Run BEFORE committing to a base model. Threshold: average tokens-per-Vietnamese-word
should be < 2.5 — otherwise consider a Vietnamese-tuned base (Vistral, SeaLLM).

Usage:
    python eval/tokenizer_test.py --model unsloth/Qwen2.5-7B-Instruct-bnb-4bit
    python eval/tokenizer_test.py --model Viet-Mistral/Vistral-7B-Chat
"""
import argparse
import statistics

VI_MEDICAL_TERMS = [
    "viêm phổi",
    "nhồi máu cơ tim",
    "viêm cầu thận cấp",
    "đái tháo đường",
    "tăng huyết áp",
    "suy tim sung huyết",
    "đột quỵ não",
    "viêm gan siêu vi B",
    "ung thư phổi không tế bào nhỏ",
    "rối loạn nhịp tim",
    "hen phế quản",
    "viêm khớp dạng thấp",
    "suy thận mạn giai đoạn cuối",
    "bệnh phổi tắc nghẽn mạn tính",
    "thiếu máu cơ tim cục bộ",
    "viêm tụy cấp",
    "loét dạ dày tá tràng",
    "xuất huyết não",
    "tiền sản giật",
    "động kinh cục bộ",
]

VI_SENTENCES = [
    "Bệnh nhân nam 65 tuổi nhập viện vì đau ngực dữ dội kèm khó thở, tiền sử tăng huyết áp và đái tháo đường type 2.",
    "Kết quả điện tâm đồ cho thấy ST chênh lên ở các chuyển đạo V1 đến V4, gợi ý nhồi máu cơ tim cấp thành trước.",
    "Chỉ định dùng aspirin 325 mg liều nạp, sau đó duy trì 81 mg/ngày, kết hợp clopidogrel 75 mg/ngày trong 12 tháng.",
    "Bệnh nhân được chỉ định chụp cộng hưởng từ não để loại trừ đột quỵ thiếu máu cục bộ giai đoạn cấp.",
    "Theo dõi dấu hiệu sinh tồn mỗi 15 phút trong 4 giờ đầu, đặc biệt chú ý mạch, huyết áp và độ bão hòa oxy.",
]


def count_words_vi(text: str) -> int:
    # Vietnamese is space-separated by syllable, but a "word" can be 1-3 syllables.
    # Use syllable count as proxy (each space-separated token = 1 syllable).
    return len(text.split())


def test_tokenizer(model_name: str, threshold: float = 2.5) -> bool:
    print(f"\n=== Tokenizer test: {model_name} ===\n")

    try:
        from transformers import AutoTokenizer
    except ImportError:
        raise SystemExit("Install: pip install transformers")

    tok = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    print(f"Vocab size: {tok.vocab_size}")
    print(f"Model max length: {tok.model_max_length}\n")

    print("--- Medical terms ---")
    term_ratios = []
    for term in VI_MEDICAL_TERMS:
        ids = tok.encode(term, add_special_tokens=False)
        syllables = count_words_vi(term)
        ratio = len(ids) / syllables
        term_ratios.append(ratio)
        flag = " ⚠️" if ratio > threshold else ""
        print(f"  {len(ids):3d} tok / {syllables:2d} syl = {ratio:.2f}{flag}  | {term}")

    print("\n--- Clinical sentences ---")
    sent_ratios = []
    for s in VI_SENTENCES:
        ids = tok.encode(s, add_special_tokens=False)
        syllables = count_words_vi(s)
        ratio = len(ids) / syllables
        sent_ratios.append(ratio)
        flag = " ⚠️" if ratio > threshold else ""
        print(f"  {len(ids):4d} tok / {syllables:3d} syl = {ratio:.2f}{flag}")
        print(f"      {s[:80]}{'...' if len(s) > 80 else ''}")

    avg_term = statistics.mean(term_ratios)
    avg_sent = statistics.mean(sent_ratios)
    overall = statistics.mean(term_ratios + sent_ratios)

    print("\n=== Summary ===")
    print(f"  Avg ratio (medical terms):    {avg_term:.2f} tok/syl")
    print(f"  Avg ratio (clinical sentences): {avg_sent:.2f} tok/syl")
    print(f"  Overall:                      {overall:.2f} tok/syl")
    print(f"  Threshold:                    {threshold:.2f}")

    passed = overall <= threshold
    print(f"\n  Result: {'PASS' if passed else 'FAIL — consider VN-tuned base'}\n")
    return passed


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--model",
        default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
        help="HF model ID to test",
    )
    p.add_argument("--threshold", type=float, default=2.5)
    args = p.parse_args()
    ok = test_tokenizer(args.model, args.threshold)
    raise SystemExit(0 if ok else 1)
