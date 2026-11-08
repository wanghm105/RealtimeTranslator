# RealtimeTranslator

[简体中文](README.md) | English

RealtimeTranslator is a Windows classroom captioning prototype. It transcribes English speech and displays the English text alongside a Chinese translation in your browser. The project uses existing speech recognition and language models; it does not train a new model.

```text
Microphone / supported loopback input
  -> voice activity detection -> faster-whisper transcription
  -> sentence merging -> Qwen translation -> WebSocket -> browser captions
```

## Features

- Shows partial English captions and streams the Chinese translation. Recent captions reappear after a browser refresh.
- Keeps the translation queue bounded so newer captions take priority when translation falls behind. Some captions may be dropped under load.
- Lets you adjust sentence merging, terminology, model selection and local caption saving.
- Includes an optional NLLB translation path that requires separately prepared model files.

## Requirements and setup

The original setup uses Windows, Python 3 and an NVIDIA CUDA GPU. Memory use and speed depend on the models, drivers and workload. A clean installation on another computer has not yet been verified. The application downloads model files on first use, so allow time and disk space. Check the licenses and terms of the models and dependencies you use.

1. Install Python and a compatible NVIDIA driver. `install.bat` creates a virtual environment and installs a CUDA 12.8 PyTorch build and the packages in `requirements.txt`. You may need a different PyTorch build for your GPU and driver; see [PyTorch installation](https://pytorch.org/get-started/locally/).
2. Review and run `install.bat` from the project directory.
3. Run `start.bat` and select an available audio input. If the browser does not open, go to `http://127.0.0.1:18090`. Close both the server and translator windows to stop the application.

You can also run `.venv\Scripts\python.exe realtime_server.py` and `.venv\Scripts\python.exe main.py` in separate terminals. The default ports are 18090, 8765 and 8766. The browser page currently assumes WebSocket port 8765, so if you change that port in `config.py`, also update `web/index.html`.

## Configuration and privacy

Edit `config.py` to change the speech recognition, translation or audio settings. The application can choose a Qwen model based on available GPU power and memory, and it may disable translation when resources are limited. You can add terminology to `glossary.txt`.

Caption saving is enabled by default. Files are written to `subtitles/` and may contain private or copyrighted material. Obtain any necessary permission before recording or sharing them. `.gitignore` excludes local captions, model weights, the virtual environment and device preferences from Git.

The server listens on `127.0.0.1` by default, so it is accessible only from the same computer. It has no authentication or encryption. Changing `HOST` to `0.0.0.0` makes captions and control endpoints accessible to devices that can reach it. On a trusted network, other clients may still read or clear captions and send messages. Do not expose the server to the public internet.

## Current limitations

- The configured translation direction is primarily English to Chinese. Accuracy and latency depend on the audio, models and hardware; no formal benchmark is included.
- Streaming may miss captions if a queue overflows or the application is interrupted. It is not guaranteed to produce a complete transcript.
- To use NLLB, run `python download_nllb.py` and `python convert_nllb.py` to prepare files in `models/`. Check the model license before use.
- The code loads Hugging Face model components with `trust_remote_code=True`. Review model sources before downloading or running them.
- Dependency versions are not locked. Installation and GPU operation still need testing on a clean machine.

## Project layout

`main.py` coordinates audio, recognition and translation. `realtime_server.py` serves the page and relays captions. The pipeline components are in `audio/`, `speech/`, `core/` and `translation/`; the caption interface is `web/index.html`.

## License

No project license has been selected yet. Third-party models and dependencies have their own licenses.
