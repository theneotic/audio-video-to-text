"""FastAPI web interface for the media-to-text package."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.staticfiles import StaticFiles

from .core import transcribe_file, write_outputs

SUPPORTED_EXTENSIONS = {
    ".aac",
    ".flac",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".wav",
    ".webm",
    ".wma",
}
OUTPUT_FORMATS = ("txt", "json", "srt", "vtt")
MODEL_OPTIONS = ("tiny", "base", "small", "medium", "large-v3")
MAX_UPLOAD_BYTES = 500 * 1024 * 1024


def _error_response(request: Request, message: str) -> HTMLResponse:
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
    template_name = "error_fragment.html" if request.headers.get("HX-Request") == "true" else "error.html"
    return HTMLResponse(
        templates.get_template(template_name).render(request=request, message=message),
        status_code=400,
    )


async def _save_upload(upload: UploadFile, destination: Path) -> int:
    """Stream an upload to disk and reject files over the configured limit."""
    size = 0
    with destination.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise ValueError("The upload is larger than the 500 MB limit.")
            output.write(chunk)
    return size


def create_app(job_root: str | Path | None = None) -> FastAPI:
    """Create a configured FastAPI application.

    ``job_root`` is injectable for tests and can be used by deployments that
    want temporary jobs on a dedicated volume.
    """
    package_dir = Path(__file__).parent
    root = Path(job_root or Path.cwd() / ".media_to_text_jobs").expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    templates = Jinja2Templates(directory=str(package_dir / "templates"))

    app = FastAPI(title="Media to Text", version="0.1.0")
    app.state.job_root = root
    app.mount("/static", StaticFiles(directory=str(package_dir / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "models": MODEL_OPTIONS,
                "formats": OUTPUT_FORMATS,
                "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
            },
        )

    @app.post("/transcribe", response_class=HTMLResponse)
    async def transcribe_endpoint(
        request: Request,
        file: UploadFile = File(...),
        model: str = Form("small"),
        output_format: str = Form("txt"),
        language: str = Form(""),
        task: str = Form("transcribe"),
        device: str = Form("auto"),
        compute_type: str = Form("default"),
        word_timestamps: bool = Form(False),
    ) -> HTMLResponse:
        filename = Path(file.filename or "").name
        extension = Path(filename).suffix.lower()
        if not filename or extension not in SUPPORTED_EXTENSIONS:
            return _error_response(
                request,
                "Please upload a supported audio or video file. Supported extensions include MP3, WAV, M4A, MP4, MKV, MOV, WEBM, and FLAC.",
            )
        if model not in MODEL_OPTIONS:
            return _error_response(request, "Please choose a supported Whisper model.")
        if output_format not in (*OUTPUT_FORMATS, "all"):
            return _error_response(request, "Please choose a supported output format.")
        if task not in {"transcribe", "translate"}:
            return _error_response(request, "Please choose a supported transcription task.")
        if device not in {"auto", "cpu", "cuda"}:
            return _error_response(request, "Please choose auto, CPU, or CUDA device mode.")

        job_id = uuid.uuid4().hex
        job_dir = root / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        source_path = job_dir / f"source{extension}"
        try:
            await _save_upload(file, source_path)
            result = await run_in_threadpool(
                transcribe_file,
                source_path,
                model_name=model,
                device=device,
                compute_type=compute_type,
                language=language.strip() or None,
                task=task,
                word_timestamps=word_timestamps,
            )
            await run_in_threadpool(write_outputs, result, job_dir, "transcript", output_format)
        except (ValueError, FileNotFoundError, RuntimeError, OSError) as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            return _error_response(request, str(exc))
        finally:
            await file.close()

        output_files = []
        formats = OUTPUT_FORMATS if output_format == "all" else (output_format,)
        for item in formats:
            output_files.append(
                {
                    "format": item.upper(),
                    "href": f"/download/{job_id}/transcript.{item}",
                }
            )
        return templates.TemplateResponse(
            request=request,
            name=("result_fragment.html" if request.headers.get("HX-Request") == "true" else "result.html"),
            context={
                "filename": filename,
                "result": result,
                "files": output_files,
                "model": model,
                "task": task,
            },
        )

    @app.get("/download/{job_id}/{filename}")
    async def download(job_id: str, filename: str) -> FileResponse:
        if len(job_id) != 32 or any(character not in "0123456789abcdef" for character in job_id):
            return Response(status_code=404)
        safe_filename = Path(filename).name
        if safe_filename != filename or not safe_filename.startswith("transcript."):
            return Response(status_code=404)
        target = (root / job_id / safe_filename).resolve()
        if target.parent != (root / job_id).resolve() or not target.is_file():
            return Response(status_code=404)
        media_types = {
            ".txt": "text/plain",
            ".json": "application/json",
            ".srt": "application/x-subrip",
            ".vtt": "text/vtt",
        }
        return FileResponse(
            target,
            media_type=media_types.get(target.suffix, "application/octet-stream"),
            filename=safe_filename,
        )

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("media_to_text.web:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":  # pragma: no cover
    main()
