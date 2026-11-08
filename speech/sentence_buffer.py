import numpy as np
import time


class SentenceBuffer:

    def __init__(
        self,
        sample_rate=16000,
        silence_duration=0.8,
        max_duration=10,
    ):

        self.sample_rate = sample_rate

        self.silence_duration = silence_duration

        self.max_duration = max_duration


        self.audio_buffer = []

        self.speaking = False

        self.last_voice_time = 0

        self.start_time = 0

    @property
    def is_speaking(self) -> bool:
        """当前是否处于说话状态（供状态提示用）"""
        return self.speaking



    def add(
        self,
        audio: np.ndarray,
        has_voice: bool
    ):

        now = time.time()


        if has_voice:

            if not self.speaking:

                print("\nSpeech started")

                self.start_time = now


            self.speaking = True

            self.last_voice_time = now



        if self.speaking:

            self.audio_buffer.append(audio)



        if self.speaking:


            silence = (
                now - self.last_voice_time
            )


            duration = (
                now - self.start_time
            )


            if (
                silence > self.silence_duration
                or duration > self.max_duration
            ):


                result = np.concatenate(
                    self.audio_buffer
                )


                self.audio_buffer.clear()


                self.speaking = False



                print(
                    "Speech ended:",
                    round(
                        len(result)/self.sample_rate,
                        2
                    ),
                    "sec"
                )


                return result



        return None