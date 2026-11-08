from collections import deque
from threading import Lock
import numpy as np


class RingBuffer:
    """
    固定长度环形缓冲区

    用于实时音频缓存。

    内部保存 float32 PCM 数据。
    """

    def __init__(self, max_seconds: float, sample_rate: int):
        self.sample_rate = sample_rate
        self.max_samples = int(max_seconds * sample_rate)

        self._buffer = deque(maxlen=self.max_samples)
        self._lock = Lock()

    def append(self, audio: np.ndarray):
        """
        添加新的音频数据
        """
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        with self._lock:
            self._buffer.extend(audio)

    def clear(self):
        with self._lock:
            self._buffer.clear()

    def get_all(self) -> np.ndarray:
        """
        获取当前全部音频
        """
        with self._lock:
            return np.array(self._buffer, dtype=np.float32)

    def get_last_seconds(self, seconds: float) -> np.ndarray:
        """
        获取最近 N 秒音频
        """
        samples = int(seconds * self.sample_rate)

        with self._lock:
            if samples >= len(self._buffer):
                return np.array(self._buffer, dtype=np.float32)

            return np.array(
                list(self._buffer)[-samples:],
                dtype=np.float32
            )

    @property
    def duration(self):
        with self._lock:
            return len(self._buffer) / self.sample_rate