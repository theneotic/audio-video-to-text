# Media to Text

A small, local-first Python command-line application for transcribing audio and video files with [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper). It accepts common media containers that the underlying decoder can read and produces plain text, JSON, SRT, or WebVTT subtitles.

> **Privacy note:** The application runs inference locally after the selected model has been downloaded. Your media is not sent to a hosted transcription API by this project.

## Features

| Capability | Details |
|---|---|
| Audio and video | Pass files such as MP3, WAV, M4A, MP4, MKV, and other formats supported by the decoder |
| Model selection | Use `tiny`, `base`, `small`, `medium`, `large-v3`, or a local model path |
| Language handling | Detect the language automatically or provide an ISO-style language code |
| Translation | Optionally translate spoken content to English with `--task translate` |
| Output formats | `txt`, `json`, `srt`, `vtt`, or all four with `--format all` |
| Hardware | CPU and CUDA execution options, with configurable compute type |
| Timestamps | Segment timestamps in subtitle formats and optional word timestamps in JSON |

## Requirements

Python 3.10 or newer is required. A CUDA-enabled installation can be used when an appropriate NVIDIA runtime is available; otherwise, CPU inference works with the default settings. On the first run, Faster-Whisper downloads the selected model, so internet access is needed once for each model unless you supply a local model path.

The project uses Faster-Whisper, an MIT-licensed implementation built on CTranslate2. Its documented installation path includes PyAV for decoding media, so a separate system FFmpeg installation is normally not required for supported files.[1]

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/audio-video-to-text.git
cd audio-video-to-text
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
# .venv\\Scripts\\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e .
```

For development and tests:

```bash
python -m pip install -e '.[dev]'
```

## Usage

Transcribe a file to plain text:

```bash
media-to-text recording.mp4
```

The default output is written to `transcripts/recording.txt`. Select another directory and format with:

```bash
media-to-text interview.wav --output-dir output --format json
media-to-text lecture.mp4 --output-dir subtitles --format all
```

For a known language, a smaller model, or translation to English:

```bash
media-to-text hindi-video.mp4 --language hi --model small
media-to-text meeting.m4a --task translate --model medium
```

On a CUDA-capable machine, use GPU inference as follows:

```bash
media-to-text lecture.mp4 --device cuda --compute-type float16 --model large-v3
```

To include word-level timestamps in JSON output:

```bash
media-to-text podcast.mp3 --format json --word-timestamps
```

Run `media-to-text --help` to see every option.

## Browser interface

Install the web dependencies and start the local FastAPI server:

```bash
python -m pip install -e .
media-to-text-web
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in a browser. Upload a media file, select a model and output format, then submit the form. The browser interface keeps the uploaded file and generated transcript under `.media_to_text_jobs/` in the working directory. These temporary job files are ignored by Git and can be deleted after use.

For development, the server can also be started with Uvicorn:

```bash
uvicorn media_to_text.web:app --host 127.0.0.1 --port 8000 --reload
```

The interface supports the same model, language, translation, device, compute type, and timestamp options as the CLI. The UI is built with Tailwind CSS and uses HTMX to submit the multipart form and replace the upload panel with a result or error fragment without a full-page navigation. Tailwind CSS and HTMX are loaded from their pinned CDN URLs in `templates/base.html`; vendor these assets locally if the deployment must work without external network access. The web server is intentionally local by default; place it behind authentication and a reverse proxy before exposing it to a network.

## Python API

The same functionality is available from Python:

```python
from media_to_text import transcribe_file, write_outputs

result = transcribe_file(
    "interview.mp4",
    model_name="small",
    language="en",
    word_timestamps=True,
)
print(result.text)
write_outputs(result, "transcripts", "interview", "all")
```

The first call loads the model and returns timestamped segments together with detected-language metadata. `write_outputs` creates the requested output directory when it does not exist.

## Output formats

| Format | Intended use |
|---|---|
| `txt` | Reading, search, and downstream text processing |
| `json` | Applications that need metadata, segments, and optional word timestamps |
| `srt` | Standard subtitle workflows |
| `vtt` | Web video players and HTML5 subtitle tracks |
| `all` | Generate every format in one run |

## Model guidance

Smaller models are faster and need less memory, while larger models generally provide better accuracy. Start with `tiny` or `base` for a quick test, use `small` for a balanced default, and select `medium` or `large-v3` when accuracy is more important than speed and the hardware can support it. Actual performance depends on language, audio quality, model, CPU/GPU, and compute type.

## Development

Run the test suite without downloading a Whisper model:

```bash
python -m pytest
```

The tests cover timestamp formatting, JSON/SRT/WebVTT serialization, file creation, parser behavior, validation, browser page rendering, upload validation, mocked transcription, and download routing. They do not download a Whisper model.

## Troubleshooting

If the program reports that `faster-whisper` is missing, activate the virtual environment and run `python -m pip install -e .` again. If a model download fails, check internet access and disk space, then retry. If CPU inference is too slow, try a smaller model or an integer compute type such as `--compute-type int8`; if a CUDA configuration fails, remove the CUDA options and verify the CPU path first.

## License

This project is released under the MIT License. The transcription engine is provided by the separate [Faster-Whisper project](https://github.com/SYSTRAN/faster-whisper), whose license and terms should be reviewed independently.

## References

[1]: https://github.com/SYSTRAN/faster-whisper "SYSTRAN/faster-whisper — Faster Whisper transcription with CTranslate2"
