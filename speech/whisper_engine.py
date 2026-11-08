from faster_whisper import WhisperModel
import numpy as np

from config import (
    WHISPER_MODEL,
    WHISPER_DEVICE,
    WHISPER_LANGUAGE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_FINAL_BEAM,
)


# 反幻觉/防重复公共参数：
# - temperature 列表：低分结果自动升温重试，打断重复循环
# - repetition_penalty：惩罚重复词
# - no_repeat_ngram_size：禁止 3-gram 重复
# - compression_ratio_threshold：检测"压缩比异常"（典型重复幻觉特征）
# - no_speech_threshold：非语音内容直接丢弃
# - hallucination_silence_threshold：静音后的幻觉输出抑制

_FINAL_PARAMS = dict(
    beam_size=WHISPER_FINAL_BEAM,
    best_of=WHISPER_FINAL_BEAM,
    temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    repetition_penalty=1.2,
    no_repeat_ngram_size=3,
    compression_ratio_threshold=2.4,
    log_prob_threshold=-1.0,
    no_speech_threshold=0.6,
    hallucination_silence_threshold=2.0,
    condition_on_previous_text=False,
    task="transcribe",
    vad_filter=True,
    vad_parameters={
        "min_silence_duration_ms": 500
    },
    max_new_tokens=128,
)

_PARTIAL_PARAMS = dict(
    beam_size=1,
    best_of=1,
    temperature=[0.0, 0.2],
    repetition_penalty=1.2,
    no_repeat_ngram_size=3,
    compression_ratio_threshold=2.4,
    log_prob_threshold=-1.0,
    no_speech_threshold=0.6,
    hallucination_silence_threshold=2.0,
    condition_on_previous_text=False,
    task="transcribe",
    vad_filter=True,
    vad_parameters={
        "min_silence_duration_ms": 500
    },
    max_new_tokens=128,
)


class WhisperEngine:

    def __init__(
        self,
        model_name=WHISPER_MODEL,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE_TYPE,
    ):

        print("Loading Whisper model...")

        self.model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            num_workers=4,
        )

        self.language = WHISPER_LANGUAGE

        print("Whisper ready.")

    def _run(self, audio, params):

        segments, info = self.model.transcribe(
            audio,
            language=self.language,
            **params
        )

        text = []

        for segment in segments:

            t = segment.text.strip()

            if t:
                text.append(t)

        return " ".join(text).strip()

    # =========================
    # 实时字幕
    # =========================

    def transcribe_realtime(
        self,
        audio: np.ndarray
    ):

        return self._run(
            audio,
            _PARTIAL_PARAMS
        )

    # =========================
    # 最终字幕
    # =========================

    def transcribe(
        self,
        audio: np.ndarray
    ):

        return self._run(
            audio,
            _FINAL_PARAMS
        )
