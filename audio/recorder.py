import queue
import time

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly

from core.audio_frame import AudioFrame


class Recorder:
    def __init__(
        self,
        device_index: int,
        audio_queue: queue.Queue,
        input_rate: int = 48000,
        target_rate: int = 16000,
        channels: int = 2,
        blocksize: int = None,
    ):
        self.device_index = device_index
        self.audio_queue = audio_queue

        self.input_rate = input_rate
        self.target_rate = target_rate
        self.channels = channels

        # 每帧采样数（默认 100ms）
        self.blocksize = blocksize or int(self.input_rate * 0.1)

        self.stream = None

    def _callback(self, indata, frames, time_info, status):

        if status:
            print(status)

        audio = np.copy(indata)

        # stereo -> mono
        if audio.ndim == 2:
            audio = audio.mean(axis=1)

        # float32
        audio = audio.astype(np.float32)

        # 48k -> 16k
        if self.input_rate != self.target_rate:
            audio = resample_poly(
                audio,
                self.target_rate,
                self.input_rate
            )

        frame = AudioFrame(
            samples=audio,
            sample_rate=self.target_rate,
            timestamp=time.time()
        )

        try:
            self.audio_queue.put_nowait(frame)

        except queue.Full:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                pass

            self.audio_queue.put_nowait(frame)

    def start(self):

        self.stream = sd.InputStream(
            device=self.device_index,
            samplerate=self.input_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=self.blocksize,
            callback=self._callback,
        )

        self.stream.start()

    def stop(self):

        if self.stream:

            self.stream.stop()

            self.stream.close()