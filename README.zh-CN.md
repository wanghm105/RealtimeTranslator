# RealtimeTranslator

[中文主页](README.md) | [English](README.en.md)

RealtimeTranslator 是一个面向 Windows 课堂场景的字幕工具原型。它将英文语音转成文字，并在浏览器中显示英文字幕和中文翻译。项目使用现有的语音识别和语言模型，没有训练新模型。

```text
麦克风 / 支持的系统声音输入
  -> 语音活动检测 -> faster-whisper 语音识别
  -> 句子合并 -> Qwen 翻译 -> WebSocket -> 浏览器字幕
```

## 功能

- 显示实时英文字幕和流式中文字幕；刷新浏览器后可以恢复最近的字幕。
- 限制翻译队列长度。翻译跟不上时优先处理较新的字幕，积压严重时可能会丢掉部分字幕。
- 可以调整句子合并、术语、模型选择和本地字幕保存设置。
- 提供可选的 NLLB 翻译方式，需要另外准备模型文件。

## 环境与安装

原有环境使用 Windows、Python 3 和 NVIDIA CUDA 显卡。显存占用和速度取决于模型、驱动和使用情况，目前还没有在另一台干净的电脑上验证过安装过程。程序首次运行时会下载模型，请预留时间和磁盘空间。使用前请查看所选模型及依赖的许可证和使用条款。

1. 安装 Python 和兼容的 NVIDIA 驱动。`install.bat` 会创建虚拟环境，安装 CUDA 12.8 版本的 PyTorch 以及 `requirements.txt` 中的依赖。你的显卡和驱动可能需要其他版本，请参考 [PyTorch 安装说明](https://pytorch.org/get-started/locally/)。
2. 在项目目录中查看并运行 `install.bat`。
3. 运行 `start.bat`，选择可用的音频输入。如果浏览器没有自动打开，请访问 `http://127.0.0.1:18090`。关闭服务端和翻译端两个窗口即可停止程序。

你也可以在两个终端中分别运行 `.venv\Scripts\python.exe realtime_server.py` 和 `.venv\Scripts\python.exe main.py`。默认端口为 18090、8765 和 8766。网页目前固定使用 WebSocket 端口 8765；如果在 `config.py` 中更改该端口，也需要更新 `web/index.html`。

## 配置与隐私

在 `config.py` 中可以调整语音识别、翻译和音频设置。程序可以根据 GPU 的可用功耗和显存选择 Qwen 模型；资源不足时可能关闭翻译。术语可以添加到 `glossary.txt` 中。

字幕默认保存到 `subtitles/`。字幕可能包含私人信息或受版权保护的内容，录制或分享前请取得必要的许可。`.gitignore` 会将本地字幕、模型文件、虚拟环境和设备选择排除在 Git 之外。

服务端默认监听 `127.0.0.1`，只有本机可以访问。服务没有身份验证或加密。如果将 `HOST` 改成 `0.0.0.0`，能够连接到服务的设备就可以访问字幕和控制接口。即使在可信网络中，其他客户端仍可能读取、清空字幕或发送消息。请勿将服务暴露到公共互联网。

## 当前限制

- 默认配置主要用于英文翻译成中文。准确率和延迟取决于音频、模型和硬件，目前没有正式的基准测试结果。
- 队列溢出或程序中断时，流式处理可能遗漏字幕，不能保证得到完整的文字记录。
- 使用 NLLB 时，先运行 `python download_nllb.py` 和 `python convert_nllb.py`，在 `models/` 中准备文件。使用前请查看模型许可证。
- 代码通过 `trust_remote_code=True` 加载 Hugging Face 模型组件，下载或运行前请检查模型来源。
- 依赖版本尚未锁定，安装流程和 GPU 运行还需要在干净的电脑上测试。

## 项目结构

`main.py` 负责协调音频、识别和翻译；`realtime_server.py` 提供网页并转发字幕。处理流程的组件位于 `audio/`、`speech/`、`core/` 和 `translation/`，字幕页面为 `web/index.html`。

## 许可证

项目尚未选择许可证。第三方模型和依赖各有自己的许可证。
