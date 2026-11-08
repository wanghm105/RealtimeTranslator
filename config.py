from pathlib import Path

ROOT = Path(__file__).parent

# =========================
# 音频采集
# =========================
SAMPLE_RATE = 16000            # 处理采样率
INPUT_SAMPLE_RATE = 48000      # 设备采集采样率（与 16k 不同会自动重采样）
INPUT_CHANNELS = 2             # 设备采集声道数（自动混合为单声道）
BLOCK_SECONDS = 0.1            # 每帧音频时长（秒），影响实时字幕刷新粒度

# =========================
# Whisper 识别
# =========================
# 课堂推荐 large-v3-turbo：质量接近 large-v3 但快 4 倍，延迟更低。
# 追求最高准确率（不在乎延迟）可改 "large-v3"。
WHISPER_MODEL = "large-v3-turbo"
WHISPER_DEVICE = "cuda"
# int8_float16：实测识别结果与 float16 完全一致，但省 ~1.5GB 显存、更快
WHISPER_COMPUTE_TYPE = "int8_float16"
WHISPER_LANGUAGE = "en"
# 最终识别 beam 宽度：5=质量最好（推荐），1=贪心最快但容易重复/出错
WHISPER_FINAL_BEAM = 5
WHISPER_NUM_WORKERS = 4

# =========================
# VAD / 断句
# =========================
VAD_THRESHOLD = 0.5
# 静音多久（秒）判定一句话结束。
# 0.8 秒：断句更勤，句子一句句出、转写更快，被切半的句子由合并器拼回；
# 1.2 秒：等更完整的停顿才断句，识别结果更容易带句号，但容易一次出多句。
SILENCE_DURATION = 0.8
# 单句最大时长（秒）：连续讲话超过此时长会被硬切（句中被切断的主要原因）。
# 12 秒：转写更快、显存峰值更低；被切半的句子由合并器拼回。
# 追求完整可调回 20，但长音频转写慢且吃显存。
MAX_SENTENCE_SECONDS = 12

# =========================
# 断句合并（修复中间被切断的翻译）
# =========================
# 以省略号结尾（话没说完、ASR 硬截断）不算句末，会与下一段合并再翻译。
# 合并缓冲上限：最多攒多少词 / 最多等多久（秒）强制翻译。
# 窗口越大句子越完整，但字幕出现越慢、越容易一次憋出多句。
# 觉得翻译出得慢 → 调小；觉得句子总被切半 → 调大。
MERGE_MAX_WORDS = 24
MERGE_MAX_WAIT = 3.0

# =========================
# 实时字幕（partial）
# =========================
# 多久跑一次实时识别（秒）。越小越跟手，但更占 GPU。
REALTIME_INTERVAL = 0.7
# 实时识别用最近多少秒音频
PARTIAL_AUDIO_SECONDS = 3

# =========================
# 启动提示
# =========================
# 选麦克风超时（秒）：超时自动用上次选择
DEVICE_PROMPT_TIMEOUT = 5
# 其他提示超时（秒）
PROMPT_TIMEOUT = 10

# =========================
# 翻译
# =========================
# 是否启用本地翻译（手动总开关）：
#   True  - 按功耗限制自动决定：功耗充足就翻译，受限就不翻译（见 TRANSLATION_MIN_POWER_WATTS）
#   False - 始终不加载翻译模型（字幕照常显示，中文区留空给浏览器插件）
TRANSLATION_ENABLED = True
# 功耗限制阈值（瓦）：GPU 当前功耗限制低于此值 → 自动不翻译，只出英文字幕。
# 静音/省电模式一般 55W（<80 → 不翻译），正常模式 175W（>=80 → 翻译）。
# 读不到功耗限制时按充足处理（正常翻译）。
TRANSLATION_MIN_POWER_WATTS = 80
# 引擎选择：
#   "qwen" - LLM 翻译，质量好，支持流式逐字显示
#   "nllb" - 极快（每句 0.1-0.3s），质量一般，显存 ~1.5GB
TRANSLATION_ENGINE = "qwen"
# 自动按功耗限制选择模型：
#   True  - 启动时读 nvidia-smi 功耗限制，低功耗自动用 1.5B，足量用 Qwen3-4B
#   False - 固定使用下面 TRANSLATION_MODEL 指定的模型
TRANSLATION_AUTO = True
# Qwen 加载精度：
#   "none" - fp16 全精度，最快（Qwen3-4B 占 ~7.7GB，需 Whisper 用 int8）
#   "8bit" - 量化省显存（~4.2GB）但慢 2-3 倍
TRANSLATION_QUANTIZE = "none"
# TRANSLATION_AUTO=False 时使用的模型：
#   Qwen/Qwen3-4B               质量最好
#   Qwen/Qwen2.5-3B-Instruct    质量好，fp16 占 ~6GB
#   Qwen/Qwen2.5-1.5B-Instruct  质量一般但最快
TRANSLATION_MODEL = "Qwen/Qwen3-4B"
# 每句最多生成多少 token（字幕一句 80 足够；改小更快）
TRANSLATION_MAX_NEW_TOKENS = 80
# 翻译时带最近几句译文，帮助术语保持一致（改大更一致、更慢）
TRANSLATION_HISTORY = 3
SOURCE_LANG = "eng_Latn"
TARGET_LANG = "zho_Hans"
# 可选术语表文件：每行 "英文 -> 中文"（也支持 →、=、: 分隔），# 开头为注释
GLOSSARY_FILE = ROOT / "glossary.txt"

# =========================
# 服务端 / WebSocket
# =========================
HOST = "127.0.0.1"
HTTP_PORT = 18090             # 字幕网页（8080/8090 在本机被系统拒绝绑定）
BROWSER_WS_PORT = 8765        # 浏览器字幕推送
CAPTION_WS_PORT = 8766        # 翻译客户端推送
# 服务端保留的最近字幕条数（刷新网页后历史不丢）
HISTORY_MAX = 200

# =========================
# 字幕保存
# =========================
# 整节课字幕自动保存到 subtitles/ 目录
SAVE_SUBTITLE = True
SUBTITLE_DIR = ROOT / "subtitles"
LOG_DIR = ROOT / "logs"
