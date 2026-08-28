# Media to Text

> **A local audio and video transcription toolkit built around Faster-Whisper, with command-line and browser-oriented workflows.**

| Project lens | Details |
| --- | --- |
| **Type** | Local media utility |
| **Stack** | Python · Faster-Whisper |
| **Status** | Actively maintained |

## Overview

A local audio and video transcription toolkit built around Faster-Whisper, with command-line and browser-oriented workflows. This README keeps the project’s verified setup, usage, privacy, and implementation notes together in one place.

## Repository Snapshot

The top-level workspace currently includes `Dockerfile`, `LICENSE`, `README.md`, `pyproject.toml`, `render.yaml`, `requirements.txt`, `src/`, `tests/`, `vercel.json`. Review the project-specific sections below before installing dependencies, supplying configuration values, or running a build.


---

A local-first Python application for turning audio and video recordings into searchable text and subtitle files. It provides both a command-line interface and a browser interface built with FastAPI, Tailwind CSS, and HTMX. Transcription is performed locally with [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper), so the project does not require a hosted transcription API.

> **Status:** The project is intentionally small and self-hostable. It is a practical starting point for personal transcription, internal tools, and experiments with local speech recognition.

## What it does

| Capability | Details |
|---|---|
| Audio and video input | Accepts common media files including MP3, WAV, M4A, MP4, MKV, MOV, WEBM, OGG, AAC, FLAC, and WMA |
| Local transcription | Runs the selected Whisper model on the machine running the application |
| Language detection | Automatically detects the spoken language, or accepts a language code such as `en` or `hi` |
| Translation | Can translate speech to English with the `translate` task |
| Output formats | Plain text, structured JSON, SRT subtitles, WebVTT captions, or all formats at once |
| Private speech downloads | Browser-local eSpeak NG WebAssembly with WAV downloads; Docker deployments also support server-side MP3 |
| Interfaces | `media-to-text` CLI, Python API, and `media-to-text-web` FastAPI server |
| Hardware options | CPU, automatic device selection, or CUDA with a configurable compute type |
| Word timestamps | Optional word-level timing data in JSON output |

## How it works

The workflow is deliberately straightforward:

1. A media file is selected through the CLI, Python API, or browser form.
2. Faster-Whisper decodes the media and produces timestamped transcription segments.
3. The application serializes those segments as text, JSON, SRT, or WebVTT.
4. The CLI writes files to a local directory. The web app presents a preview and download links.
5. The web app can synthesize pasted text locally in the browser with eSpeak NG WebAssembly and return a WAV download; Docker deployments can also synthesize server-side MP3.

The first use of a model may download model files from the model registry used by Faster-Whisper. After that, the model can be reused from the local cache or supplied as a local model path.[1]

## Requirements

| Requirement | Notes |
|---|---|
| Python | 3.10 or newer |
| Operating system | Linux, macOS, or Windows with a working Python installation |
| Memory and storage | Depends on the selected Whisper model; larger models require more resources |
| Internet access | Needed the first time a model is downloaded, unless a local model path is supplied |
| GPU | Optional; CUDA can accelerate inference on supported NVIDIA systems |

Faster-Whisper uses PyAV for media decoding, and the package normally provides the FFmpeg libraries it needs. If a particular media container cannot be decoded, installing a system FFmpeg package can still help with preprocessing or conversion.[1]

## Installation

Clone the public repository and create a virtual environment:

```bash
git clone https://github.com/theneotic/audio-video-to-text.git
cd audio-video-to-text
python -m venv .venv
```

Activate the environment.

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\\Scripts\\Activate.ps1
```

Install the application:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Install the test dependencies as well when developing the project:

```bash
python -m pip install -e '.[dev]'
```

The editable install exposes two commands:

| Command | Purpose |
|---|---|
| `media-to-text` | Transcribe a file from the terminal |
| `media-to-text-web` | Start the local FastAPI browser application |

## Command-line usage

Transcribe an audio or video file to plain text:

```bash
media-to-text recording.mp4
```

By default, the command writes `transcripts/recording.txt`. Choose another output directory and format with:

```bash
media-to-text interview.wav --output-dir output --format json
media-to-text lecture.mp4 --output-dir subtitles --format all
```

Specify the language when it is known:

```bash
media-to-text interview.m4a --language en
media-to-text hindi-video.mp4 --language hi
```

Translate spoken content to English instead of preserving the source language:

```bash
media-to-text meeting.mp4 --task translate --model medium
```

Use a CUDA GPU when the local environment supports it:

```bash
media-to-text lecture.mp4 --device cuda --compute-type float16 --model large-v3
```

Generate word-level timestamps in JSON:

```bash
media-to-text podcast.mp3 --format json --word-timestamps
```

View all available options:

```bash
media-to-text --help
```

### CLI options

| Option | Default | Description |
|---|---:|---|
| `input` | — | Path to an audio or video file |
| `--output-dir`, `-o` | `transcripts` | Directory for generated output |
| `--format`, `-f` | `txt` | `txt`, `json`, `srt`, `vtt`, or `all` |
| `--model`, `-m` | `small` | Model name or local model path |
| `--device` | `auto` | `auto`, `cpu`, or `cuda` |
| `--compute-type` | `default` | For example `default`, `int8`, or `float16` |
| `--language` | auto-detect | Source language code |
| `--task` | `transcribe` | `transcribe` or `translate` |
| `--beam-size` | `5` | Beam search size |
| `--no-vad-filter` | disabled | Disable voice activity detection filtering |
| `--word-timestamps` | disabled | Include word timing data in JSON |

## Browser interface

Start the FastAPI application after installing the project:

```bash
media-to-text-web
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in a browser. You can upload a file, choose a Whisper model, select an output format, set the language or translation task, and optionally configure device settings. After transcription, the page shows a readable preview and download links.

For development with automatic reload:

```bash
uvicorn media_to_text.web:app --host 127.0.0.1 --port 8000 --reload
```

The browser UI is implemented as server-rendered HTML. Tailwind CSS handles the visual styling, while HTMX submits the multipart form and swaps the upload panel for a result or error fragment without requiring a client-side application bundle. The shared layout also includes clear ownership, primary navigation, About, Contact & support, Privacy, Terms, GitHub source, and transcription calls to action. The Tailwind and HTMX assets are referenced from CDN URLs in `src/media_to_text/templates/base.html`; vendor those assets locally if the deployment must work without external network access.

### Web application behavior

The web app accepts uploads up to 500 MB and validates the file extension before transcription. Temporary job files are written under `.media_to_text_jobs/` in the current working directory. That directory is ignored by Git and can be removed after use. The default server binds to `127.0.0.1`, which keeps it local to the machine; add authentication, HTTPS, and a reverse proxy before making it accessible to other users.

## Python API

The transcription engine can also be used directly from Python:

```python
from media_to_text import transcribe_file, write_outputs

result = transcribe_file(
    "interview.mp4",
    model_name="small",
    language="en",
    device="auto",
    word_timestamps=True,
)

print(result.text)
write_outputs(result, "transcripts", "interview", "all")
```

`transcribe_file` returns a `TranscriptionResult` containing detected-language metadata and timestamped `Segment` objects. `write_outputs` creates the destination directory when necessary and returns the generated paths.

## Output formats

| Format | Contents | Typical use |
|---|---|---|
| `.txt` | Normalized transcript text | Reading, search, and text analysis |
| `.json` | Source metadata, language, duration, segments, and optional words | Applications and data pipelines |
| `.srt` | Numbered timestamped subtitle cues | Video editors and subtitle tools |
| `.vtt` | WebVTT timestamped cues | HTML5 video players and web publishing |

Example JSON structure:

```json
{
  "source": "/path/to/interview.mp4",
  "language": "en",
  "language_probability": 0.98,
  "duration": 42.5,
  "text": "Hello and welcome.",
  "segments": [
    {
      "id": 1,
      "start": 0.0,
      "end": 2.4,
      "text": "Hello and welcome.",
      "words": []
    }
  ]
}
```

## Choosing a model

Model selection is a speed-versus-accuracy decision. A smaller model is useful for quick drafts and modest hardware; a larger model is more appropriate when accuracy is more important than latency and the machine has enough memory.

| Model | General starting point |
|---|---|
| `tiny` | Fastest initial test |
| `base` | Lightweight everyday transcription |
| `small` | Balanced default for this project |
| `medium` | Higher accuracy with greater resource use |
| `large-v3` | Highest accuracy option in the UI |

Actual speed and accuracy depend on the language, recording quality, background noise, hardware, device, and compute type. Start with `small`, then adjust after testing on representative files.

## Private text-to-speech

The web interface also includes a **Private audio** panel. Paste text, choose an eSpeak NG language voice, adjust speed and pitch, and download the result as WAV. On the free Vercel site, the bundled eSpeak NG WebAssembly worker synthesizes the downloadable audio in the browser, so the text stays on the device and no TTS server or API key is needed. The generated WAV also appears in an in-page audio player so it can be listened to before downloading again.

The panel includes a separate **Listen preview** control that can use the more natural voices exposed by the browser or operating system. The Web Speech API's available voices are device/browser dependent; this preview is not the guaranteed private download path and may use the platform's configured speech service. When JavaScript is unavailable, or when the app is deployed with the Docker image, the FastAPI `/speak` endpoint can synthesize WAV or MP3 on the server instead.

The Dockerfile installs both `espeak-ng` and `ffmpeg`. eSpeak NG produces the WAV source, and FFmpeg creates the MP3 download when requested. The application limits speech input to 10,000 characters and validates language, speed, pitch, and output format before invoking the binaries. The browser bundle is vendored under `static/vendor/espeakng/` and includes its GPLv3 notice. eSpeak NG is GPLv3-or-later; review its license and the license files included by your base distribution when redistributing the Docker image.[5] [6] [7] The device-voice preview follows the browser's Web Speech API behavior.[8] [9]

For local development on Debian/Ubuntu, install the runtime tools with:

```bash
sudo apt-get update
sudo apt-get install -y espeak-ng ffmpeg
```

## Vercel deployment

The repository includes a Vercel-compatible FastAPI entrypoint under `src/main.py`, a `vercel.json` function configuration, and a `requirements.txt` dependency manifest. These files let Vercel expose the existing server-rendered website through its Python function runtime while the source of truth remains the GitHub repository.

To connect the repository in Vercel, create a new project from `theneotic/audio-video-to-text`, keep the root directory at `.`, and deploy the `main` branch. Vercel will use the supported `src/main.py` FastAPI entrypoint and route the application’s HTML, static assets, About, Contact, Privacy, Terms, upload, and download paths through it. Every new push to `main` can then create a new deployment through Vercel’s Git integration.

The Vercel adapter stores job files under `/tmp/media_to_text_jobs`, because serverless functions should not be treated as permanent disk storage. Serverless execution, request-size, memory, and timeout limits vary by Vercel plan and can make long recordings or large Whisper models a poor fit. The free Vercel site uses the bundled browser-local eSpeak NG WebAssembly worker for private WAV downloads, so it does not require the `espeak-ng` or `ffmpeg` operating-system binaries. The server-side `/speak` route and MP3 generation require the Docker image; use that path on Render or Hugging Face Spaces for a server-hosted private speech service.

Vercel Functions impose a 4.5 MB request-body limit.[10] To keep the free website useful for larger recordings, the transcription form now detects files above 4 MB and uses the browser’s Web Audio API to decode the media locally, accelerate extraction, downsample it to compact 8 kHz mono PCM, and upload a small WAV proxy for transcription. The original video is not sent through the Vercel Function, and the original filename is retained on the result page. This fallback requires a browser with AudioContext support; browsers that cannot decode the media receive a clear message recommending a shorter file or the Docker deployment. Vercel remains suitable for the public website, browser-local speech, compressed short-to-medium recordings, or lightweight transcription demos, while sustained or high-accuracy workloads should use the Docker image.

## Automated CI/CD deployment

The repository includes `.github/workflows/deploy.yml`, which runs the test suite on every push to `main` and can deploy to Render or a Hugging Face Docker Space after the tests pass. Deployment targets are optional: if the relevant secret or repository variable is not configured, that target is skipped. Pull requests run through the normal test workflow but never deploy.

The workflow supports two deployment paths:

| Target | Best fit | GitHub configuration | Deployment mechanism |
|---|---|---|---|
| Render | A conventional web service with a linked Git repository | Secret `RENDER_DEPLOY_HOOK_URL` | Calls the service’s secret deploy hook after CI succeeds |
| Hugging Face Spaces | A model-oriented demo or Docker-based ML application | Secret `HF_TOKEN` and variable `HF_SPACE_REPO` | Uses the official `huggingface/hub-sync` action to mirror the repository |
| Vercel | The public website or a lightweight serverless demo | Link the GitHub repository in Vercel | Uses Vercel’s Git integration to deploy `src/main.py`; offline speech requires the Docker target |

### Option A: Render

1. Create a new Render service from this repository, or create it from the included `render.yaml` Blueprint.
2. Confirm the service uses the repository’s `Dockerfile` and the `main` branch.
3. Leave automatic deploys disabled in Render if you want GitHub Actions to be the deployment gate. The included Blueprint sets `autoDeployTrigger: off`.
4. In the Render service Settings page, create or copy the service’s Deploy Hook URL.
5. In GitHub, open **Settings → Secrets and variables → Actions → New repository secret** and add `RENDER_DEPLOY_HOOK_URL` with the Deploy Hook URL as its value.
6. Push to `main` or manually run **Deploy transcription app** from the Actions tab.

Render’s Deploy Hook URL is a secret. The workflow sends a POST request only after all three Python test jobs pass. Render may return `202` when another deployment is already in progress; the hook request is still considered accepted by the platform.[2]

### Option B: Hugging Face Spaces

1. Create a new Hugging Face Space using the **Docker** SDK. The Space should be owned by the account represented in `HF_SPACE_REPO`, and its repository name should look like `username/space-name`.
2. Create a Hugging Face access token with write access to the Space.
3. Add the token as the GitHub repository secret `HF_TOKEN`.
4. Add a GitHub repository variable named `HF_SPACE_REPO` with the value `username/space-name`.
5. Push to `main` or manually run **Deploy transcription app** from the Actions tab.

The workflow uses the official `huggingface/hub-sync` action with `repo_type: space` and `space_sdk: docker`. The included Dockerfile listens on port `7860` by default, which is the port expected by a Docker Space. Docker Space disk contents are not durable across restarts unless persistent storage is configured, so treat generated job files as temporary.[3] [4]

### Deployment secrets and variables

| Name | Type | Required for | Description |
|---|---|---|---|
| `RENDER_DEPLOY_HOOK_URL` | GitHub Actions secret | Render | The secret Deploy Hook URL from the Render service Settings page |
| `HF_TOKEN` | GitHub Actions secret | Hugging Face | A Hugging Face token with write access to the target Space |
| `HF_SPACE_REPO` | GitHub Actions repository variable | Hugging Face | Target Space ID, for example `username/space-name` |

Never commit tokens, deploy hook URLs, local model files, uploaded media, or generated transcripts. GitHub Actions masks configured secrets in logs, but a deploy hook should still be treated as a credential and regenerated if exposed.[2]

### Manual workflow runs

Both deployment targets can be triggered without a code change from the repository’s **Actions** tab. Select **Deploy transcription app**, choose **Run workflow**, and select the `main` branch. The target is deployed only when its configuration is present; the other target remains skipped.

## Development

Run the full test suite:

```bash
python -m pytest
```

The tests exercise the transcription serializers, CLI argument parsing, FastAPI page rendering, upload validation, HTMX fragment responses, mocked transcription, private speech download responses, file downloads, and path validation. Tests intentionally mock the Whisper and speech-engine calls, so they do not download a model or require a media fixture.

The repository uses GitHub Actions to run the test suite on Python 3.10, 3.11, and 3.12 for pushes and pull requests.

## Troubleshooting

### `faster-whisper` is missing

Make sure the virtual environment is active, then reinstall the project:

```bash
python -m pip install -e .
```

### The first run is slow

The selected model may be downloading or being initialized. Try `tiny`, `base`, or `small` first. Subsequent runs can reuse the local model cache.

### CPU inference is too slow

Use a smaller model and try an integer compute type:

```bash
media-to-text recording.mp4 --model small --device cpu --compute-type int8
```

### CUDA inference fails

Verify the NVIDIA driver and CUDA runtime expected by the installed CTranslate2 build. To confirm that the application itself works, remove the CUDA arguments and run the CPU path first.

### A file cannot be decoded

Try converting the source to a common WAV or MP4 file with FFmpeg, then transcribe the converted file. Also confirm that the file is not truncated or password-protected.

### The browser page cannot be opened

Confirm that `media-to-text-web` is running and that port 8000 is available. For a development server, use:

```bash
uvicorn media_to_text.web:app --host 127.0.0.1 --port 8000 --reload
```

### CDN assets are unavailable

The interface references Tailwind CSS and HTMX from CDNs. If the page loads without styling or interactions, vendor those assets locally and update `templates/base.html` to use local paths.

## Security and deployment notes

This project is designed for local use and does not include user authentication, quotas, multi-user job isolation, or persistent job management. Uploaded media, generated transcripts, and temporary speech files are processed by the configured server. Before deploying it beyond a trusted machine, add authentication and authorization, enforce resource quotas, use a dedicated temporary storage volume, configure cleanup, restrict upload types and sizes, and put the application behind HTTPS and a reverse proxy. The private speech feature is local to the server only when the deployment uses the supplied Docker image with eSpeak NG and FFmpeg; the current Vercel function deployment does not provide those OS packages.

Do not expose the development server directly to the public internet. If multiple users will submit long recordings, consider moving transcription into a background worker and adding a job queue rather than holding an HTTP request open for the entire model run.

## Project layout

```text
.
├── .github/workflows/ci.yml
├── .github/workflows/deploy.yml
├── Dockerfile
├── render.yaml
├── vercel.json
├── requirements.txt
├── src/main.py                 # Vercel FastAPI entrypoint
├── src/media_to_text/
│   ├── cli.py                 # Command-line interface
│   ├── core.py                # Transcription and output serialization
│   ├── speech.py              # Offline eSpeak NG speech synthesis
│   ├── web.py                 # FastAPI routes and upload/speech workflow
│   ├── static/style.css       # Small companion stylesheet
│   ├── static/transcribe.js   # Browser-local large-file audio fallback
│   └── templates/             # Tailwind/HTMX server-rendered pages
├── tests/
│   ├── test_core.py
│   └── test_web.py
├── pyproject.toml
├── LICENSE
└── README.md
```

## License and attribution

This project is released under the [MIT License](LICENSE). Transcription is powered by the separate [Faster-Whisper project](https://github.com/SYSTRAN/faster-whisper), which is also MIT-licensed. Please review the upstream project for model, runtime, and dependency details.[1]

## References

real

[1]: https://github.com/SYSTRAN/faster-whisper "SYSTRAN/faster-whisper — Faster Whisper transcription with CTranslate2"
[2]: https://render.com/docs/deploy-hooks "Render Deploy Hooks"
[3]: https://huggingface.co/docs/hub/en/spaces-github-actions "Hugging Face Spaces with GitHub Actions"
[4]: https://huggingface.co/docs/hub/en/spaces-sdks-docker "Hugging Face Docker Spaces"
[5]: https://github.com/espeak-ng/espeak-ng "eSpeak NG project and license"
[6]: https://espeak.sourceforge.net/commands.html "eSpeak command-line options"
[7]: https://github.com/pettarin/espeakng.js-cdn "Browser eSpeak NG WebAssembly bundle"
[8]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API "MDN Web Speech API overview"
[9]: https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis "MDN SpeechSynthesis voice and playback API"

[10]: https://vercel.com/docs/functions/limitations "Vercel Functions Limits"
