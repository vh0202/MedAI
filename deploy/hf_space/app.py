"""HuggingFace Space Gradio demo for MedAI.

Free CPU tier — uses GGUF Q4_K_M via llama-cpp-python (~4 GB, slow but works).
"""
import os
from pathlib import Path

import gradio as gr

DISCLAIMER_VI = (
    "⚠️ **Đây là thông tin tham khảo từ AI nghiên cứu/giáo dục. KHÔNG thay thế tư vấn của bác sĩ.** "
    "Trường hợp khẩn cấp: gọi **115** (Việt Nam) hoặc **911** (US)."
)
DISCLAIMER_EN = (
    "⚠️ **This is AI-generated educational information. NOT a substitute for professional medical advice.** "
    "Emergencies: call **115** (Vietnam) or **911** (US)."
)

SYSTEM = (
    "Bạn là MedAI — trợ lý AI y khoa song ngữ. Luôn bắt đầu bằng disclaimer, "
    "không kê liều cụ thể, và yêu cầu tham vấn bác sĩ với mọi câu hỏi lâm sàng. "
    "You are MedAI, a bilingual medical AI for education only — never give specific dosages "
    "and always recommend consulting a clinician."
)

MODEL_PATH = os.environ.get("MEDAI_GGUF", "medai-7b-q4_k_m.gguf")


def load_model():
    """Lazy load — try llama-cpp-python first, fall back to mock."""
    try:
        from llama_cpp import Llama
        if Path(MODEL_PATH).exists():
            print(f"[load] {MODEL_PATH}")
            return Llama(
                model_path=MODEL_PATH,
                n_ctx=4096,
                n_threads=os.cpu_count() or 2,
                chat_format="qwen",
                verbose=False,
            )
    except Exception as e:
        print(f"[warn] llama-cpp-python not available: {e}")
    return None


_LLM = None


def respond(message: str, history: list[tuple[str, str]]) -> str:
    global _LLM
    if _LLM is None:
        _LLM = load_model()
    if _LLM is None:
        return DISCLAIMER_VI + "\n\n" + DISCLAIMER_EN + "\n\n_(Demo placeholder — model not loaded.)_"

    msgs = [{"role": "system", "content": SYSTEM}]
    for user_msg, asst_msg in history:
        msgs.append({"role": "user", "content": user_msg})
        if asst_msg:
            msgs.append({"role": "assistant", "content": asst_msg})
    msgs.append({"role": "user", "content": message})

    out = _LLM.create_chat_completion(
        messages=msgs,
        max_tokens=512,
        temperature=0.3,
        top_p=0.9,
        repeat_penalty=1.05,
    )
    text = out["choices"][0]["message"]["content"].strip()

    if not text.startswith("⚠️"):
        text = DISCLAIMER_VI + "\n\n" + text

    return text


with gr.Blocks(title="MedAI — Bilingual Medical AI") as demo:
    gr.Markdown(f"# MedAI — Bilingual (VN-EN) Medical AI\n\n{DISCLAIMER_VI}\n\n{DISCLAIMER_EN}")
    gr.Markdown(
        "Educational and research tool only. Repository: [vh0202/MedAI](https://github.com/vh0202/MedAI)."
    )
    chat = gr.ChatInterface(
        fn=respond,
        examples=[
            "Bệnh nhân nam 60 tuổi đau ngực sau xương ức 30 phút, chẩn đoán phân biệt gồm những gì?",
            "What's the difference between Type 1 and Type 2 diabetes?",
            "Triệu chứng cảnh báo của đột quỵ là gì?",
            "Summarize the major risk factors for atherosclerosis.",
        ],
    )

if __name__ == "__main__":
    demo.launch()
