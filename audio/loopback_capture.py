import numpy as np
import sounddevice as sd


class LoopbackCapture:
    def __init__(self):
        self.stream = None

    def callback(self, indata, frames, time, status):
        if status:
            print(status)

        volume = np.sqrt(np.mean(indata.astype(np.float32) ** 2))

        print(f"\rVolume: {volume:.5f}", end="")

    def start(self, device):
        self.stream = sd.InputStream(
            device=device,
            samplerate=48000,
            channels=2,
            dtype="float32",
            callback=self.callback,
        )

        self.stream.start()

        print("Listening... Press Ctrl+C to stop.")

        try:
            while True:
                sd.sleep(100)
        except KeyboardInterrupt:
            self.stream.stop()
            self.stream.close()