from dataclasses import dataclass
import numpy as np


@dataclass(slots=True)
class AudioFrame:
    """
    一帧音频数据。
    """

    samples: np.ndarray
    sample_rate: int
    timestamp: float