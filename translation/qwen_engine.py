import queue
import threading

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TextIteratorStreamer,
)

from config import (
    TRANSLATION_MODEL,
    TRANSLATION_QUANTIZE,
    TRANSLATION_AUTO,
    TRANSLATION_MAX_NEW_TOKENS,
    TRANSLATION_HISTORY,
    GLOSSARY_FILE,
)
from translation.model_selector import pick_model_by_power_limit


# 课程常见术语表（保持术语翻译一致）
GLOSSARY = [
    "GPU → GPU",
    "model → 模型",
    "dataset → 数据集",
    "training → 训练",
    "inference → 推理",
    "gradient → 梯度",
    "loss function → 损失函数",
    "attention mechanism → 注意力机制",
    "transformer → Transformer",
    "neural network → 神经网络",
    "matrix → 矩阵",
    "memory bandwidth → 内存带宽",
    "weights → 权重",
    "token → 词元",
    "algorithm → 算法",
]

# 保留最近几句译文，帮助术语和说法保持一致
MAX_HISTORY = TRANSLATION_HISTORY

# 历史句截断长度，控制提示词大小、降低延迟
HISTORY_TRIM = 80


def _load_glossary_file():
    """读取可选的术语表文件（每行 "英文 -> 中文"）。"""
    extra = []

    if not GLOSSARY_FILE or not GLOSSARY_FILE.exists():
        return extra

    try:
        lines = GLOSSARY_FILE.read_text(encoding="utf-8").splitlines()
    except Exception:
        return extra

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for sep in ("->", "→", "=", ":"):
            if sep in line:
                en, zh = line.split(sep, 1)
                en, zh = en.strip(), zh.strip()
                if en and zh:
                    extra.append(f"{en} → {zh}")
                break

    return extra


class QwenTranslator:

    # 支持流式输出：翻译时逐段回调 on_partial
    streaming = True

    def __init__(self):

        model_name = TRANSLATION_MODEL

        if TRANSLATION_AUTO:
            # 按当前功耗限制自动选模型
            model_name = pick_model_by_power_limit()

        print("Loading Qwen translator...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )

        self.device = "cuda:0"

        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA unavailable. Please check NVIDIA driver and PyTorch CUDA."
            )

        print(
            "Using GPU:",
            torch.cuda.get_device_name(0)
        )

        model_kwargs = dict(
            dtype=torch.float16,
            device_map={
                "": self.device
            },
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )

        if TRANSLATION_QUANTIZE == "8bit":
            # 8bit 量化省显存，但 Windows 上逐层反量化开销大，慢 2-3 倍
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_8bit=True,
            )

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            **model_kwargs
        )

        self.model.eval()

        self.history = []

        self.glossary = GLOSSARY + _load_glossary_file()

        self.max_new_tokens = TRANSLATION_MAX_NEW_TOKENS

        # Qwen3 的 chat 模板默认带思考模式，需要关闭；
        # Qwen2.5 的模板不支持这个参数
        self.need_thinking_off = "Qwen3" in model_name

        print("Qwen ready.")

        print(
            "Model device:",
            self.model.device
        )

    def _build_prompt(self, text):

        parts = [
            "你是实时字幕翻译器，把英文翻译成自然中文。",
            "规则：",
            "1. 保持原意，不漏信息",
            "2. 不要逐词翻译，使用符合中文习惯的表达",
            "3. 专业名词保持准确",
            "4. 术语按术语表翻译，与之前译文保持一致",
            "5. 输出简短字幕格式",
            "6. 只输出中文，不要解释",
            "7. 英文来自语音识别，可能有个别错词或断句问题：",
            "   句子不通顺时，根据上下文合理推测原意再翻译，不要硬译",
            "   省略号（...）表示话没说完，翻译时忽略它",
            "",
            "术语表：",
        ]

        parts.extend(self.glossary)

        if self.history:

            parts.append("")
            parts.append("之前的翻译（保持术语和说法一致）：")

            for en, zh in self.history:
                parts.append(f"EN: {en[:HISTORY_TRIM]}")
                parts.append(f"ZH: {zh[:HISTORY_TRIM]}")

        parts.append("")
        parts.append("当前英文：")
        parts.append(text)
        parts.append("")
        parts.append("中文：")

        return "\n".join(parts)

    def translate(self, text, on_partial=None):

        if not text or not text.strip():
            return ""

        prompt = self._build_prompt(text)

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        template_kwargs = {}

        if self.need_thinking_off:
            # 关闭 Qwen3 思考过程
            template_kwargs["enable_thinking"] = False

        formatted = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            **template_kwargs
        )

        inputs = self.tokenizer(
            formatted,
            return_tensors="pt"
        )

        inputs = {
            key: value.to(self.device)
            for key, value in inputs.items()
        }

        gen_kwargs = dict(
            inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
            temperature=None,
            pad_token_id=self.tokenizer.eos_token_id,
        )

        # 流式输出：每生成一段就回调，网页端中文边生成边显示
        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )

        gen_kwargs["streamer"] = streamer

        def _generate():
            # 必须在推理模式下生成，避免梯度图占用显存、拖慢速度
            with torch.inference_mode():
                self.model.generate(**gen_kwargs)

        thread = threading.Thread(target=_generate)
        thread.start()

        pieces = []

        # 手动轮询流式队列：生成线程崩溃时能立即退出，不会卡到超时
        while True:
            try:
                piece = streamer.text_queue.get(timeout=0.3)
            except queue.Empty:
                if not thread.is_alive() and streamer.text_queue.empty():
                    break
                continue

            if piece is None:
                break

            pieces.append(piece)

            if on_partial:
                on_partial("".join(pieces).strip())

        thread.join()

        result = "".join(pieces).strip()

        if result:

            self.history.append((text, result))

            self.history = self.history[-MAX_HISTORY:]

        return result
