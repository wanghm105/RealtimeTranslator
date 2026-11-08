import sounddevice as sd
from rich.console import Console

from config import ROOT

console = Console()

DEVICE_FILE = ROOT / "selected_device.txt"


class AudioDeviceManager:
    """音频设备管理"""

    def __init__(self):
        self.devices = sd.query_devices()
        self.hostapis = sd.query_hostapis()

    def _hostapi_name(self, index: int) -> str:
        return self.hostapis[index]["name"]

    @staticmethod
    def _is_loopback(name: str) -> bool:
        """判断是否为系统声音回录设备（网课/视频音源）。"""
        low = name.lower()
        return (
            "loopback" in low
            or "stereo mix" in low
            or "立体声混音" in name
            or "系统声音" in name
        )

    def list_input_devices(self):
        """返回所有输入设备"""
        result = []

        for idx, dev in enumerate(self.devices):
            if dev["max_input_channels"] > 0:
                result.append(
                    {
                        "index": idx,
                        "name": dev["name"],
                        "hostapi": self._hostapi_name(dev["hostapi"]),
                        "channels": dev["max_input_channels"],
                        "samplerate": int(dev["default_samplerate"]),
                        "loopback": self._is_loopback(dev["name"]),
                    }
                )

        return result

    def list_output_devices(self):
        """返回所有输出设备"""

        result = []

        for idx, dev in enumerate(self.devices):
            if dev["max_output_channels"] > 0:
                result.append(
                    {
                        "index": idx,
                        "name": dev["name"],
                        "hostapi": self._hostapi_name(dev["hostapi"]),
                        "channels": dev["max_output_channels"],
                        "samplerate": int(dev["default_samplerate"]),
                    }
                )

        return result

    def print_devices(self):

        console.rule("[bold green]Input Devices")

        for dev in self.list_input_devices():
            console.print(
                f"[cyan]{dev['index']:>2}[/cyan] "
                f"{dev['name']} "
                f"[yellow]{dev['hostapi']}[/yellow] "
                f"{dev['samplerate']}Hz"
            )

        console.rule("[bold blue]Output Devices")

        for dev in self.list_output_devices():
            console.print(
                f"[cyan]{dev['index']:>2}[/cyan] "
                f"{dev['name']} "
                f"[yellow]{dev['hostapi']}[/yellow] "
                f"{dev['samplerate']}Hz"
            )

    def find_wasapi_devices(self):
        """寻找 WASAPI 设备"""

        result = []

        for dev in self.devices:

            host = self._hostapi_name(dev["hostapi"])

            if "WASAPI" in host:

                result.append(dev)

        return result

    def select_input_device(self, timeout=None):
        """启动时列出麦克风让用户选择，并记住上次的选择。

        超时未输入时自动使用：上次选择 → 系统默认输入设备 → 第一个可用设备。
        """

        if timeout is None:

            from config import DEVICE_PROMPT_TIMEOUT

            timeout = DEVICE_PROMPT_TIMEOUT

        from core.prompt import input_with_timeout

        devices = self.list_input_devices()

        if not devices:
            raise RuntimeError("No input device found")

        console.rule("[bold green]Select Microphone")
        console.print(
            "[dim]线上课录系统声音请选带 "
            "[yellow][系统声音][/yellow] 标记的设备[/dim]"
        )

        for d in devices:
            tag = " [yellow][系统声音][/yellow]" if d["loopback"] else ""
            console.print(
                f"[cyan]{d['index']:>2}[/cyan] "
                f"{d['name']}{tag} "
                f"[yellow]{d['hostapi']}[/yellow] "
                f"{d['samplerate']}Hz"
            )

        # 默认值：上次选择 > 系统默认输入设备 > 第一个可用设备
        default = self._default_input_index(devices)

        if DEVICE_FILE.exists():

            saved = DEVICE_FILE.read_text().strip().split("\t")[0]

            if saved and any(
                d["index"] == int(saved)
                for d in devices
            ):
                default = saved

        hint = f" [{default}]"

        while True:

            raw = input_with_timeout(
                f"Device index{hint}: ",
                timeout,
                default,
            ).strip()

            # 直接回车 = 使用默认值
            if not raw:
                raw = default

            try:

                choice = int(raw)

                if any(
                    d["index"] == choice
                    for d in devices
                ):
                    break

                print(
                    f"Device {choice} not found, retry"
                )

            except ValueError:

                print("Please enter a number")

        name = next(
            d["name"] for d in devices if d["index"] == choice
        )

        DEVICE_FILE.write_text(f"{choice}\t{name}")

        return choice

    def _default_input_index(self, devices):

        try:

            default = sd.default.device

            if isinstance(default, (tuple, list)):
                default = default[0]

            if default is not None and any(
                d["index"] == default
                for d in devices
            ):
                return str(default)

        except Exception:

            pass

        return str(devices[0]["index"])