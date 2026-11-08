import re
import time

# 省略号占位符：保护 "..."/"…" 不被当作句号切分
_ELLIPSIS = ("...", "…")
_PH_ELLIPSIS = "\x00"
# 缩写占位符：保护 "U.S." "Dr." 这类句号不被误切
_PH_ABBR = "\x01"
_COMMON_ABBR = (
    "Dr.", "Mr.", "Mrs.", "Ms.", "Prof.",
    "e.g.", "i.e.", "etc.", "vs.",
    "U.S.", "U.K.", "No.", "St.",
)
_ABBR = re.compile(r"\b[A-Z]\.(?=\s)")

# 句子边界：句末标点后跟 空白+大写/数字/引号 或 文本结尾
_BOUNDARY = re.compile(r'[.!?。！？]+(?=\s+[A-Z0-9"\'(\[]|\s*$)')


class SentenceMerger:
    """把被 ASR 断句截断的英文片段合并成完整句子，再交给翻译。

    - 以 "..." 或省略号结尾 = 话没说完，攒着等下一段
    - 片段里完整的句子（以 . ! ? 结尾且后接大写）立即输出
    - 攒着的尾巴超过最大词数或等待超时 → 强制输出
    """

    def __init__(self, max_words=40, max_wait=10.0):

        self.max_words = max_words

        self.max_wait = max_wait

        self.pending = ""

        self.start = 0.0

    def add(self, text):
        """加入一个片段，返回可以立即翻译的完整句子列表（可能为空）。

        未完成的尾巴会攒在内部，等下一段拼上来；
        攒太久（超过 max_wait）时新片段一到就合并输出，不会一直不出字幕。
        """

        had_pending = bool(self.pending)

        pending_age = time.time() - self.start if had_pending else 0.0

        if had_pending:

            text = self.pending + " " + text

        self.pending = ""

        self.start = 0.0

        sentences, tail = self._split(text)

        if tail:

            if len(tail.split()) >= self.max_words:

                # 尾巴太长，等不到下一段了，强制输出
                sentences.append(tail)

            elif had_pending and pending_age > self.max_wait:

                # 上一段已经攒了超过 max_wait：不等了，合并后直接输出，
                # 避免句子一直在缓冲里攒着、网页历史长时间不出新字幕
                sentences.append(tail)

            else:

                self.pending = tail

                self.start = time.time()

        return sentences

    def flush_if_stale(self):
        """等待超时的积压句子强制输出（没有新片段时由定时器调用）"""

        if self.pending and time.time() - self.start > self.max_wait:

            out = self.pending

            self.pending = ""

            self.start = 0.0

            return out

        return None

    def _split(self, text):
        """把文本拆成 [完整句子...] + 未完成尾巴。

        例："A. B, c..." -> (["A."], "B, c...")
        例："A... B"    -> ([], "A... B")  省略号不算句号
        """

        t = text

        for e in _ELLIPSIS:

            t = t.replace(e, _PH_ELLIPSIS)

        # 常见缩写（Dr. / U.S. / e.g.）的点先保护起来，避免误切
        for abbr in _COMMON_ABBR:

            t = t.replace(abbr, abbr[:-1] + _PH_ABBR)

        # 单大写字母+点（如 "A." "S."）同理保护
        t = _ABBR.sub(lambda m: m.group()[0] + _PH_ABBR, t)

        boundaries = [

            m.end()

            for m in _BOUNDARY.finditer(t)

        ]

        if not boundaries:

            return [], self._restore(t)

        cut = max(boundaries)

        # 按所有边界位置直接切分（不再用二次正则，避免误切）
        sentences = []

        prev = 0

        for b in boundaries:

            sentences.append(

                self._restore(t[prev:b].strip())

            )

            prev = b

        return (
            [s for s in sentences if s],
            self._restore(t[cut:].strip()),
        )

    def _restore(self, s):
        """把占位符还原为省略号和缩写点"""

        return (
            s.replace(_PH_ABBR, ".")
              .replace(_PH_ELLIPSIS, "...")
        )
