"""RealtimeTranslator 翻译客户端（主程序）

流程：
    麦克风/系统声音 -> VAD -> 断句 -> Whisper 英文识别 -> Qwen 流式翻译
    -> WebSocket -> 服务端 -> 浏览器字幕

消息协议（发给服务端 8766）：
    {"type":"partial",    "en":...}          实时英文（跟读窗口）
    {"type":"final_start","en":...,"seq":n}  整句确认，开始翻译
    {"type":"final_zh",  "zh":...,"seq":n}   流式中文更新
    {"type":"final",     "en":...,"zh":...,"seq":n} 翻译完成
    {"type":"status",    "status":"listening|translating|idle"} 状态
"""

import asyncio
import itertools
import json
import queue
import re
import sys
import threading
import time
import traceback

import numpy as np
import websockets

from config import (
    SAMPLE_RATE,
    INPUT_SAMPLE_RATE,
    INPUT_CHANNELS,
    BLOCK_SECONDS,
    VAD_THRESHOLD,
    SILENCE_DURATION,
    MAX_SENTENCE_SECONDS,
    REALTIME_INTERVAL,
    PARTIAL_AUDIO_SECONDS,
    CAPTION_WS_PORT,
    SAVE_SUBTITLE,
    WHISPER_MODEL,
    MERGE_MAX_WORDS,
    MERGE_MAX_WAIT,
    TRANSLATION_ENABLED,
    TRANSLATION_MIN_POWER_WATTS,
)
from audio.device_manager import AudioDeviceManager
from audio.recorder import Recorder
from core.logger import SubtitleLogger
from core.sentence_merge import SentenceMerger
from speech.vad import StreamingVAD
from speech.sentence_buffer import SentenceBuffer
from speech.whisper_engine import WhisperEngine
from translation import create_translator
from translation.model_selector import should_translate

WS_URL = f"ws://localhost:{CAPTION_WS_PORT}"

MIN_FINAL_SECONDS = 0.8        # 太短的句子直接丢弃
PARTIAL_MIN_FRAMES = 10        # 攒够 1 秒音频才开始实时识别
BUFFER_MAX_FRAMES = 60         # 实时缓冲上限（6 秒）

# ===============================
# Queues / state
# ===============================

audio_queue = queue.Queue(maxsize=50)

# final 和 partial 分开排队：
# - final_queue：完整句子，转写慢时也不能丢（丢了字幕就没了）
# - partial_queue：实时预览，积压时直接清掉（旧字幕没用了）
final_queue = queue.Queue()

partial_queue = queue.Queue()

# 最多排队 5 句，翻译跟不上时丢最旧的一句，避免字幕越来越滞后
translate_queue = queue.Queue(maxsize=5)

seq_counter = itertools.count(1)


def next_seq():
    return next(seq_counter)


last_partial_text = ""

last_status_sent = ""


def send_status(status: str):
    global last_status_sent
    if status == last_status_sent:
        return
    last_status_sent = status
    send_caption({"type": "status", "status": status})


# ===============================
# Audio device
# ===============================

manager = AudioDeviceManager()

device_index = manager.select_input_device()

print(f"Input device index: {device_index}")

subtitle_logger = SubtitleLogger(enabled=SAVE_SUBTITLE)

recorder = Recorder(
    device_index=device_index,
    audio_queue=audio_queue,
    input_rate=INPUT_SAMPLE_RATE,
    target_rate=SAMPLE_RATE,
    channels=INPUT_CHANNELS,
    blocksize=int(INPUT_SAMPLE_RATE * BLOCK_SECONDS),
)

vad = StreamingVAD(threshold=VAD_THRESHOLD)

sentence_buffer = SentenceBuffer(
    silence_duration=SILENCE_DURATION,
    max_duration=MAX_SENTENCE_SECONDS,
)

print(f"Whisper model: {WHISPER_MODEL}")

whisper = WhisperEngine()


# ===============================
# Translator（后台加载，不阻塞启动）
# ===============================

translator = None

translator_ready = threading.Event()


def load_translator():
    global translator
    try:
        translator = create_translator()
    except Exception as e:
        print("Translator load failed:", e)
        traceback.print_exc()
    finally:
        translator_ready.set()


if TRANSLATION_ENABLED:

    # 功耗充足 → 正常加载翻译模型（后台加载，不阻塞启动）
    # 功耗受限（静音/省电模式）→ 不加载翻译模型，字幕照常显示
    if should_translate(TRANSLATION_MIN_POWER_WATTS):

        threading.Thread(target=load_translator, daemon=True).start()

    else:

        print("Translation disabled (subtitles only)")

        translator_ready.set()

else:

    # 手动关闭本地翻译：不加载模型，final 英文直接进网页历史
    print("Local translation disabled (use browser plugin)")

    translator_ready.set()


# ===============================
# WebSocket（独立线程 + 自动重连）
# ===============================

ws = None

loop = asyncio.new_event_loop()


async def connect_ws():
    global ws
    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=20) as conn:
                ws = conn
                print("WebSocket connected:", WS_URL)
                await conn.wait_closed()
        except Exception:
            pass

        ws = None
        print("WebSocket lost, retrying in 3s...")
        await asyncio.sleep(3)


def _consume_future(fut):
    try:
        fut.result()
    except Exception:
        pass


def send_caption(data):
    """线程安全发送字幕消息；服务端不在线时静默丢弃"""
    if ws is None:
        return
    try:
        fut = asyncio.run_coroutine_threadsafe(
            ws.send(json.dumps(data, ensure_ascii=False)),
            loop,
        )
        fut.add_done_callback(_consume_future)
    except Exception:
        pass


def start_ws():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(connect_ws())


threading.Thread(target=start_ws, daemon=True).start()


# ===============================
# ASR worker
# ===============================

def asr_worker():
    while True:
        # final 优先处理；partial 有空闲才处理。
        # 注意：两个队列里存的都是 numpy 音频数组（不是元组）
        kind = None
        audio = None

        try:
            audio = final_queue.get_nowait()
            kind = "final"
        except queue.Empty:
            try:
                audio = partial_queue.get_nowait()
                kind = "partial"
            except queue.Empty:
                time.sleep(0.05)
                continue

        if kind == "final":

            # 转写前清掉积压的 partial（旧的实时预览没用了），
            # 只清 partial_queue，绝不动 final_queue
            while True:
                try:
                    partial_queue.get_nowait()
                except queue.Empty:
                    break

            try:

                t0 = time.time()

                english = whisper.transcribe(audio)

                elapsed = time.time() - t0

                if elapsed > 8:

                    # 转写异常慢：通常是显存不足或 GPU 被占，提示便于诊断
                    print(
                        f"WARNING: transcribe took {elapsed:.1f}s "
                        f"({len(audio) / SAMPLE_RATE:.1f}s audio)"
                    )

            except Exception as e:

                # 识别失败不崩溃线程，下一句继续
                print("ASR final error:", e)

                english = ""

            if english.strip():
                print("FINAL:", english)

                try:
                    translate_queue.put_nowait(english)
                except queue.Full:
                    # 积压时丢掉最旧的一句再入队
                    try:
                        translate_queue.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        translate_queue.put_nowait(english)
                    except queue.Full:
                        pass

        else:

            try:

                english = whisper.transcribe_realtime(audio)

            except Exception as e:

                print("ASR partial error:", e)

                english = ""

            if english.strip():
                print("LIVE:", english)
                send_partial(english)


threading.Thread(target=asr_worker, daemon=True).start()


def send_partial(text: str):
    global last_partial_text
    if text == last_partial_text:
        return
    last_partial_text = text
    send_caption({"type": "partial", "en": text})


# ===============================
# Translate worker
# ===============================

# 被截断的片段先合并成完整句子再翻译
merger = SentenceMerger(
    max_words=MERGE_MAX_WORDS,
    max_wait=MERGE_MAX_WAIT,
)

# 翻译输入里去掉省略号（"from 20... five years ago" -> "from 20 five years ago"）
_ELLIPSIS = re.compile(r"(?:\.\s*){2,}|…+")


def translate_worker():
    while True:
        try:
            # 轮询间隔小于合并等待时间，让超时句子尽快被强制翻译
            english = translate_queue.get(timeout=2)
        except queue.Empty:
            # 没有新片段时，检查积压句子是否超时该翻
            merged = merger.flush_if_stale()
            if merged is None:
                continue
            sentences = [merged]
        else:
            # SentenceMerger.add 返回可立即翻译的完整句子列表；
            # 没说完的尾巴会攒在 merger 里等下一段
            sentences = merger.add(english)
            if not sentences:
                continue

        # 字幕优先：先发 final_start，英文立即上卡片（"翻译中"状态），
        # 模型加载中/加载失败也不会让历史区空着。
        # 多句时逐句上屏（间隔 0.5 秒），避免三句同时出现
        seqs = []

        for sentence in sentences:

            seq = next_seq()

            seqs.append(seq)

            send_caption(
                {"type": "final_start", "en": sentence, "seq": seq}
            )

            if len(sentences) > 1:

                time.sleep(0.5)

        # 等翻译模型后台加载完。
        # 功耗模式下加载可能很慢，最多等 120 秒，超时跳过翻译继续出字幕
        if not translator_ready.is_set():
            print("Waiting for translator model...")
            translator_ready.wait(timeout=120)

        # 翻译并完成卡片（用 seq 更新已显示的英文卡片）
        for sentence, seq in zip(sentences, seqs):

            if translator is None:

                # 本地翻译未启用（或加载失败）：
                # 不带 zh 字段，网页端中文区留空给翻译插件
                zh = ""

                caption = {
                    "type": "final",
                    "en": sentence,
                    "seq": seq,
                    "ts": time.time(),
                }

            else:

                supports_stream = bool(
                    getattr(translator, "streaming", False)
                )

                def on_partial(zh, _seq=seq):
                    send_caption(
                        {"type": "final_zh", "zh": zh, "seq": _seq}
                    )

                # 翻译输入清理：合并后句中残留的省略号会影响理解，去掉再翻
                clean = re.sub(
                    r"\s+", " ", _ELLIPSIS.sub(" ", sentence)
                ).strip()

                try:

                    zh = translator.translate(
                        clean or sentence,
                        on_partial=on_partial if supports_stream else None,
                    )

                except Exception as e:

                    print("Translate error:", e)

                    zh = ""

                caption = {
                    "type": "final",
                    "en": sentence,
                    "zh": zh or "",
                    "seq": seq,
                    "ts": time.time(),
                }

            send_caption(caption)

            subtitle_logger.log(sentence, zh or "")

        # 翻译完了：没新句子排队就回到待机，老师还在讲就回到聆听中
        if not translate_queue.empty():
            continue
        if sentence_buffer.is_speaking:
            send_status("listening")
        else:
            send_status("idle")


threading.Thread(target=translate_worker, daemon=True).start()


# ===============================
# 主循环
# ===============================

def run():
    global last_partial_text

    recorder.start()

    print("Realtime Translator Started")

    realtime_buffer = []

    last_recognize = time.time()

    prev_speaking = False

    while True:
        frame = audio_queue.get()
        audio = frame.samples

        # --------------------------
        # VAD + 断句
        # --------------------------

        speech = vad.is_speech(audio)

        sentence = sentence_buffer.add(audio, speech)

        speaking = sentence_buffer.is_speaking

        if speaking and not prev_speaking:
            send_status("listening")

        if not speaking and prev_speaking:
            # 说话结束且没有待处理内容 -> 待机
            if final_queue.empty() and translate_queue.empty():
                send_status("idle")

        prev_speaking = speaking

        # --------------------------
        # Final sentence
        # --------------------------

        if sentence is not None:
            duration = len(sentence) / SAMPLE_RATE

            if duration >= MIN_FINAL_SECONDS:
                # final 进专用队列：转写再慢也不会被丢弃
                final_queue.put(sentence)
                send_status("translating")

            # 清空实时缓存和去重状态，让新句子从头开始
            realtime_buffer.clear()
            last_partial_text = ""

        # --------------------------
        # Realtime buffer
        # --------------------------

        realtime_buffer.append(audio)

        if len(realtime_buffer) > BUFFER_MAX_FRAMES:
            realtime_buffer.pop(0)

        # --------------------------
        # Realtime Whisper
        # --------------------------

        now = time.time()

        if now - last_recognize >= REALTIME_INTERVAL:
            last_recognize = now

            # 队列不空闲就跳过本轮 partial，避免实时字幕积压延迟
            partial_frames = int(PARTIAL_AUDIO_SECONDS / BLOCK_SECONDS)

            if (
                len(realtime_buffer) >= PARTIAL_MIN_FRAMES
                and final_queue.empty()
            ):
                buffer_audio = np.concatenate(
                    realtime_buffer[-partial_frames:]
                )
                # partial 进专用队列：积压时由 asr_worker 清掉，不影响 final
                partial_queue.put(buffer_audio)


def main():
    try:
        run()
    except KeyboardInterrupt:
        print("\nStopping...")
        recorder.stop()
        subtitle_logger.close()
        print("Stopped")
        sys.exit(0)
    except Exception:
        traceback.print_exc()
        print("Fatal error, exiting (start.bat will restart in 5s)")
        try:
            recorder.stop()
            subtitle_logger.close()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
