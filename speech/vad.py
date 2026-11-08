import torch
import numpy as np

from silero_vad import load_silero_vad


class StreamingVAD:

    def __init__(
        self,
        sample_rate=16000,
        threshold=0.5,
    ):

        self.sample_rate = sample_rate
        self.threshold = threshold

        print("Loading Silero VAD...")

        self.model = load_silero_vad()
        self.model.eval()

        self.buffer = np.array([], dtype=np.float32)

        print("VAD ready.")


    def is_speech(self, audio: np.ndarray):

        """
        输入:
            任意长度 float32 audio

        输出:
            True / False
        """

        self.buffer = np.concatenate(
            [
                self.buffer,
                audio
            ]
        )


        results = []


        while len(self.buffer) >= 512:

            chunk = self.buffer[:512]

            self.buffer = self.buffer[512:]


            tensor = torch.from_numpy(
                chunk
            ).unsqueeze(0)


            with torch.no_grad():

                probability = self.model(
                    tensor,
                    self.sample_rate
                ).item()


            results.append(
                probability
            )


        if not results:
            return False


        # 一个100ms frame里，
        # 只要检测到有人声，就算讲话

        return max(results) > self.threshold