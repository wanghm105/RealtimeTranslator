"""RealtimeTranslator 服务端

三个角色：
- HTTP  {HTTP_PORT}：字幕网页 + 健康检查
- WS    {BROWSER_WS_PORT}：浏览器字幕显示端（可局域网多设备观看）
- WS    {CAPTION_WS_PORT}：翻译客户端推送字幕/状态

服务端缓存最近 HISTORY_MAX 条字幕，浏览器刷新后历史不丢。
"""

import asyncio
import json
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from aiohttp import web
import websockets

from config import (
    HOST,
    HTTP_PORT,
    BROWSER_WS_PORT,
    CAPTION_WS_PORT,
    HISTORY_MAX,
)

ROOT = Path(__file__).parent
INDEX_FILE = ROOT / "web" / "index.html"

browsers = set()
translator_clients = set()

# 最近字幕历史（刷新页面时重放）
history = deque(maxlen=HISTORY_MAX)

# 当前流水线状态（listening / translating / idle）
last_status = {"type": "status", "status": "idle", "ts": time.time()}


def log(*args):
    print(f"[{datetime.now():%H:%M:%S}]", *args, flush=True)


# =========================
# HTTP 网页服务器
# =========================

async def index(request):
    return web.FileResponse(
        str(INDEX_FILE),
        headers={"Cache-Control": "no-store"},
    )


async def health(request):
    return web.json_response(
        {
            "status": "ok",
            "browsers": len(browsers),
            "translator": len(translator_clients),
            "history": len(history),
        }
    )


async def start_http():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, HTTP_PORT)
    await site.start()

    log(f"Web: http://localhost:{HTTP_PORT}")


# =========================
# 广播
# =========================

async def broadcast(message: str):
    dead = []
    for ws in list(browsers):
        try:
            await ws.send(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        browsers.discard(ws)


# =========================
# 浏览器端（8765）
# =========================

async def browser_handler(ws):
    browsers.add(ws)
    log(f"Browser connected ({len(browsers)} online)")

    try:
        # 刷新页面后重放历史 + 当前状态
        if history:
            await ws.send(json.dumps(
                {"type": "history", "items": list(history)},
                ensure_ascii=False,
            ))
        await ws.send(json.dumps(last_status, ensure_ascii=False))

        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            # 浏览器请求清空字幕：清空服务端历史并广播给所有浏览器
            if msg.get("type") == "clear":
                history.clear()
                await broadcast(json.dumps(
                    {"type": "clear"}, ensure_ascii=False
                ))
                log("History cleared by browser")

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        browsers.discard(ws)
        log(f"Browser disconnected ({len(browsers)} online)")


# =========================
# 翻译客户端（8766）
# =========================

async def caption_handler(ws):
    global last_status

    # 只保留一个翻译客户端：新连接顶掉旧的，避免字幕重复
    for old in list(translator_clients):
        if old is not ws:
            try:
                await old.close()
            except Exception:
                pass
    translator_clients.add(ws)
    log("Translator connected")

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except Exception:
                continue

            t = data.get("type")

            if t == "final":
                # 记录历史
                history.append(
                    {
                        "en": data.get("en", ""),
                        "zh": data.get("zh", ""),
                        "ts": data.get("ts") or time.time(),
                    }
                )
            elif t == "status":
                last_status = data

            await broadcast(raw)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        translator_clients.discard(ws)
        log("Translator disconnected")


# =========================
# 启动
# =========================

async def main():
    await start_http()

    async with (
        websockets.serve(browser_handler, HOST, BROWSER_WS_PORT),
        websockets.serve(caption_handler, HOST, CAPTION_WS_PORT),
    ):
        log(f"Browser WS: ws://localhost:{BROWSER_WS_PORT}")
        log(f"Caption WS: ws://localhost:{CAPTION_WS_PORT}")
        log("Server ready.")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Server stopped")
