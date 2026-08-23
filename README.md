# Media to Text

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
| Interfaces | `media-to-text` CLI, Python API, and `media-to-text-web` FastAPI server |
| Hardware options | CPU, automatic device selection, or CUDA with a configurable compute type |
| Word timestamps | Optional word-level timing data in JSON output |

## How it works

The workflow is deliberately straightforward:

1. A media file is selected through the CLI, Python API, or browser form.
2. Faster-Whisper decodes the media and produces timestamped transcription segments.
3. The application serializes those segments as text, JSON, SRT, or WebVTT.
4. The CLI writes files to a local directory. The web app presents a preview and download links.

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

## Automated CI/CD deployment

The repository includes `.github/workflows/deploy.yml`, which runs the test suite on every push to `main` and can deploy to either Render or a Hugging Face Docker Space after the tests pass. Deployment targets are optional: if the relevant secret or repository variable is not configured, that target is skipped. Pull requests run through the normal test workflow but never deploy.

The workflow supports two deployment paths:

| Target | Best fit | GitHub configuration | Deployment mechanism |
|---|---|---|---|
| Render | A conventional web service with a linked Git repository | Secret `RENDER_DEPLOY_HOOK_URL` | Calls the service’s secret deploy hook after CI succeeds |
| Hugging Face Spaces | A model-oriented demo or Docker-based ML application | Secret `HF_TOKEN` and variable `HF_SPACE_REPO` | Uses the official `huggingface/hub-sync` action to mirror the repository |

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

The tests exercise the transcription serializers, CLI argument parsing, FastAPI page rendering, upload validation, HTMX fragment responses, mocked transcription, file downloads, and path validation. Tests intentionally mock the model call, so they do not download a Whisper model or require a media fixture.

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

This project is designed for local use and does not include user authentication, quotas, multi-user job isolation, or persistent job management. Uploaded media and generated files are stored on disk under the configured job directory. Before deploying it beyond a trusted machine, add authentication and authorization, enforce resource quotas, use a dedicated temporary storage volume, configure cleanup, restrict upload types and sizes, and put the application behind HTTPS and a reverse proxy.

Do not expose the development server directly to the public internet. If multiple users will submit long recordings, consider moving transcription into a background worker and adding a job queue rather than holding an HTTP request open for the entire model run.

## Project layout

```text
.
├── .github/workflows/ci.yml
├── .github/workflows/deploy.yml
├── Dockerfile
├── render.yaml
├── src/media_to_text/
│   ├── cli.py                 # Command-line interface
│   ├── core.py                # Transcription and output serialization
│   ├── web.py                 # FastAPI routes and upload workflow
│   ├── static/style.css       # Small companion stylesheet
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

[1]: https://github.com/SYSTRAN/faster-whisper "SYSTRAN/faster-whisper — Faster Whisper transcription with CTranslate2"
[2]: https://render.com/docs/deploy-hooks "Render Deploy Hooks"
[3]: https://huggingface.co/docs/hub/en/spaces-github-actions "Hugging Face Spaces with GitHub Actions"
[4]: https://huggingface.co/docs/hub/en/spaces-sdks-docker "Hugging Face Docker Spaces"
