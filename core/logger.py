import threading
from datetime import datetime

from config import SUBTITLE_DIR


class SubtitleLogger:
    """整节课字幕记录器，每条字幕实时追加写入文件"""

    def __init__(self, enabled: bool):

        self.enabled = enabled

        self.lock = threading.Lock()

        self.path = None

        self.file = None

        self.count = 0

        if enabled:

            SUBTITLE_DIR.mkdir(exist_ok=True)

            self.path = SUBTITLE_DIR / datetime.now().strftime(
                "subtitle_%Y%m%d_%H%M%S.txt"
            )

            self.file = self.path.open("a", encoding="utf-8")

            print(
                "Subtitle will be saved to:",
                self.path
            )

    def log(self, en: str, zh: str):

        if not self.enabled:
            return

        now = datetime.now().strftime("%H:%M:%S")

        with self.lock:

            self.file.write(
                f"[{now}] {en}\n"
                f"ZH: {zh}\n\n"
            )

            self.file.flush()

            self.count += 1

    def close(self):

        if not self.enabled:
            return

        with self.lock:

            self.file.close()

            print(
                f"Subtitle saved ({self.count} lines):",
                self.path
            )
