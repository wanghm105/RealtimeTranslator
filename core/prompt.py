import sys
import time

try:
    import msvcrt

    _HAS_MSVCRT = True

except ImportError:

    _HAS_MSVCRT = False


def input_with_timeout(prompt, timeout, default):
    """带超时的控制台输入。

    超时未输入则返回 default。
    非交互环境（管道/重定向输入）自动退化为普通 input()。
    """

    if not sys.stdin.isatty() or not _HAS_MSVCRT:

        try:

            return input(prompt) or default

        except EOFError:

            return default

    print(prompt, end="", flush=True)

    chars = []

    start = time.time()

    while True:

        if msvcrt.kbhit():

            ch = msvcrt.getwch()

            if ch in ("\r", "\n"):

                print()

                return "".join(chars)

            if ch == "\x03":  # Ctrl+C

                raise KeyboardInterrupt

            if ch == "\b":

                if chars:

                    chars.pop()

                    print("\b \b", end="", flush=True)

            elif ch != "\xe0":  # 忽略方向键等扩展键

                chars.append(ch)

                print(ch, end="", flush=True)

        elif time.time() - start > timeout:

            print(f" [timeout -> {default}]")

            return default

        time.sleep(0.05)
