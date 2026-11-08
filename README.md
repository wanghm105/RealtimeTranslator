# RealtimeTranslator

A Windows-focused classroom captioning prototype that turns English speech into live English captions and Chinese translations in a browser. It combines existing speech recognition and language models; it does not train a new model.

```text
Microphone / supported loopback input
  -> voice activity detection -> faster-whisper transcription
  -> sentence merging -> Qwen translation -> WebSocket -> browser captions
```

## Features

- Partial English captions and streamed Chinese translation, with recent captions replayed after a browser refresh.
- Bounded translation queue to favor recent captions when translation falls behind; some captions can be dropped under load.
- Configurable sentence merging, terminology list, model selection, and local caption saving.
- An optional NLLB translation path, requiring separately prepared model files.

## Requirements and setup

The original setup targets Windows, Python 3 and an NVIDIA CUDA GPU. GPU memory requirements and speed depend on the models, drivers and workload. A clean installation on another computer has **not yet been verified**. The application downloads model files on first use; allow substantial disk space and time. Check the licenses and terms of the models and dependencies you use.

1. Install Python and a compatible NVIDIA driver. The provided `install.bat` creates a virtual environment and installs a CUDA 12.8 PyTorch build plus the packages in `requirements.txt`. Adjust the PyTorch installation for your GPU and driver if necessary; see [PyTorch installation](https://pytorch.org/get-started/locally/).
2. Run `install.bat` from the project directory. Review its commands before use.
3. Run `start.bat`, select an available audio input, and open `http://127.0.0.1:18090` if the browser does not open. Close the server and translator windows to stop.

The project also supports running `.venv\Scripts\python.exe realtime_server.py` and `.venv\Scripts\python.exe main.py` in separate terminals. Default ports are 18090, 8765 and 8766. The browser page currently assumes WebSocket port 8765, so changing the port in `config.py` also requires updating `web/index.html`.

## Configuration and privacy

Edit `config.py` to adjust speech recognition, translation and audio settings. The Qwen model may be selected according to available GPU power and memory; translation can be disabled when resources are limited. Add optional terminology to `glossary.txt`.

Caption saving is enabled by default and writes to `subtitles/`. Captions can contain private or copyrighted material; obtain any necessary permission before recording or sharing. Local caption files, model weights, the virtual environment and device preferences are excluded from Git via `.gitignore`.

The server defaults to `127.0.0.1` (this computer only). It has **no authentication or encryption**. Changing `HOST` to `0.0.0.0` exposes captions and control endpoints to devices that can reach it; only do so on a trusted network and understand that other clients may read or clear captions or send messages. Do not expose it to the public internet.

## Current limitations

- English-to-Chinese is the primary configured direction. Accuracy and latency depend on the audio, models and hardware; no formal benchmark is included.
- Streaming is a best-effort prototype, not a guaranteed complete transcript. Queue overflow and interruptions can result in missing captions.
- The NLLB path needs `python download_nllb.py` and `python convert_nllb.py` to create local files in `models/`. Check the model license before use.
- The code loads Hugging Face model components with `trust_remote_code=True`; review model sources before downloading or running them.
- Dependencies are not locked, and end-to-end installation and GPU operation need testing on a clean machine.

## Project layout

`main.py` coordinates audio, recognition and translation; `realtime_server.py` serves the page and relays captions; `audio/`, `speech/`, `core/`, and `translation/` contain the pipeline components; `web/index.html` is the caption interface.

## License

No project license has been selected yet. Third-party models and dependencies have their own licenses.
