import re
import subprocess


def get_power_limit_watts():
    """读取当前 GPU 功耗限制（瓦），失败返回 None"""

    try:

        out = subprocess.run(
            ["nvidia-smi", "-q", "-d", "POWER"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout

        m = re.search(
            r"Current Power Limit\s*:\s*([\d.]+)",
            out
        )

        if m:
            return float(m.group(1))

    except Exception:

        pass

    return None


def should_translate(min_power_watts=80, min_free_vram_mb=5500):
    """根据当前 GPU 功耗限制 + 可用显存决定是否启用本地翻译。

    - 功耗限制 < 阈值：低功耗模式（静音/省电），不加载翻译模型
    - 可用显存 < 阈值：显存被其他程序占用，不加载翻译模型
      （5500MB = 最小模型 1.5B 的 3.5GB + Whisper 转写余量 2GB，
      否则 Qwen 加载后 Whisper 转写会卡死）
    两种情况都只出英文字幕（网页插件可翻译）。
    - 读不到数值：按充足处理，正常翻译
    """

    limit = get_power_limit_watts()

    if limit is not None and limit < min_power_watts:

        print(
            f"GPU power limit: {limit:.0f}W < {min_power_watts}W, "
            "translation disabled (subtitles only)"
        )

        return False

    free = get_free_vram_mb()

    if free is not None and free < min_free_vram_mb:

        print(
            f"Free VRAM: {free}MB < {min_free_vram_mb}MB, "
            "translation disabled (subtitles only)"
        )

        return False

    print(
        f"GPU power limit: {limit if limit is not None else '?'}W, "
        f"free VRAM: {free if free is not None else '?'}MB, "
        "translation enabled"
    )

    return True


def get_free_vram_mb():
    """读取当前 GPU 可用显存（MB），失败返回 None"""

    try:

        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout

        return int(float(out.strip().splitlines()[0]))

    except Exception:

        return None


def pick_model_by_power_limit():
    """按功耗限制 + 可用显存自动选择翻译模型。

    功耗档位：<=60W 用 1.5B，<=100W 用 3B，>100W 用 4B；
    显存档位：保证 Qwen 加载后还给 Whisper 转写留 ~2GB，
    显存不足自动降级（否则 Whisper 转写会卡死/OOM）。
    读不到数值时按充足处理。
    """

    limit = get_power_limit_watts()

    free = get_free_vram_mb()

    # 功耗档位：1=小 2=中 3=大
    if limit is None:

        power_tier = 3

    elif limit <= 60:

        power_tier = 1

    elif limit <= 100:

        power_tier = 2

    else:

        power_tier = 3

    # 显存档位（free = 加载 Qwen 前的可用显存，MB）。
    # 阈值 = 模型占用 + Whisper 转写余量 ~2GB：
    #   4B fp16 ~7.7GB  -> free >= 10GB
    #   3B fp16 ~6GB    -> free >= 8GB
    #   1.5B fp16 ~3.5GB -> free >= 5.5GB
    if free is None:

        vram_tier = 3

    elif free >= 10000:

        vram_tier = 3      # Qwen3-4B fp16

    elif free >= 8000:

        vram_tier = 2      # Qwen2.5-3B fp16

    else:

        vram_tier = 1      # Qwen2.5-1.5B fp16

    # 取两者中更保守的档位
    tier = min(power_tier, vram_tier)

    models = {
        1: "Qwen/Qwen2.5-1.5B-Instruct",
        2: "Qwen/Qwen2.5-3B-Instruct",
        3: "Qwen/Qwen3-4B",
    }

    tier_names = {
        1: "1.5B (lowest)",
        2: "3B (medium)",
        3: "4B (full quality)",
    }

    if limit is None and free is None:

        print("GPU state unknown, use Qwen3-4B")

    else:

        print(
            f"GPU power limit: {limit if limit is not None else '?'}W, "
            f"free VRAM: {free if free is not None else '?'}MB -> "
            f"select {tier_names[tier]}"
        )

    return models[tier]
