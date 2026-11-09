# RealtimeTranslator

[English homepage](README.md) | [简体中文](README.zh-CN.md)

RealtimeTranslator is a Windows classroom captioning prototype. It transcribes English speech and displays the English text alongside a Chinese translation in your browser. The project uses existing speech recognition and language models; it does not train a new model.

```text
Microphone / supported loopback input
  -> voice activity detection -> faster-whisper transcription
  -> sentence merging -> Qwen translation -> WebSocket -> browser captions
```

## Classroom features

- Capture speech from a microphone or a supported system-audio loopback device.
- Show partial English transcription as speech arrives, then stream the Chinese translation alongside the completed sentence.
- Follow new captions automatically, pause following when you scroll up, and return to the latest sentence with one click.
- Restore recent caption history after a refresh and reconnect the browser when the connection drops.
- Use full-screen and focus modes, change the font size, and show or hide the English text. The page also includes keyboard shortcuts.
- Save session captions locally and use a glossary to guide translation of course terminology.

## How it works

1. **Capture and segment audio.** The application takes microphone or loopback audio and uses voice activity detection to identify speech and pauses.
2. **Transcribe speech.** faster-whisper produces a live English preview and transcribes completed speech segments. Recognition settings can be adjusted in `config.py`.
3. **Merge fragments.** A sentence merger holds incomplete fragments, including those ending in an ellipsis, and combines them with later speech within configurable word and time limits.
4. **Translate and display.** Qwen streams Chinese text while WebSocket messages deliver updates to the browser. Sentence sequence numbers keep translation updates matched with their English text.
5. **Keep the view responsive.** A bounded translation queue gives newer captions priority if translation falls behind. The server retains recent history for a refreshed browser, and the interface follows new content unless the reader has scrolled up.

## Design and development

The project grew out of using live captions in class, where a useful result needs to be readable during a lecture as well as reasonably responsive. The implementation separates audio capture, speech recognition, sentence merging, translation and display so each stage can be tuned independently.

- **Sentence boundaries:** Pauses in speech do not always mark the end of a sentence. The merger waits for more context when a fragment looks incomplete, with configurable limits to avoid waiting indefinitely.
- **Latency and workload:** English can appear while the translation model is loading. Once translation starts, the application streams updates and bounds the translation queue to limit how far captions fall behind.
- **Hardware-aware model selection:** The application can select a Qwen model using available GPU power and memory. The project also supports an optional NLLB translation path with separately prepared model files.
- **Model experiments:** During development, I compared Qwen 8-bit and FP16 inference on my Windows setup and chose FP16 for that environment. I also tried faster-whisper compute settings and adjusted decoding parameters to reduce repeated or hallucinated text. These observations depend on the hardware, models and workload.
- **Classroom interface:** I refined the scrolling behavior so users can read earlier captions without being pulled back to the bottom, while new and streaming text continues to follow when the viewer is at the latest caption.

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
