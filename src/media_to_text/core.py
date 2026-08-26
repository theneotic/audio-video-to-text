"""Core transcription and output formatting logic."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Word:
    """A word-level timestamp returned by Whisper when requested."""

    start: float
    end: float
    word: str
    probability: float | None = None


@dataclass(frozen=True)
class Segment:
    """A timestamped transcription segment."""

    id: int
    start: float
    end: float
    text: str
    words: tuple[Word, ...] = ()


@dataclass(frozen=True)
class TranscriptionResult:
    """A complete transcription and model metadata."""

    source: str
    language: str | None
    language_probability: float | None
    duration: float | None
    segments: tuple[Segment, ...]

    @property
    def text(self) -> str:
        """Return the full transcript as normalized paragraphs."""
        return "\n".join(segment.text.strip() for segment in self.segments if segment.text.strip())


def _word_from_whisper(word: Any) -> Word:
    return Word(
        start=float(word.start),
        end=float(word.end),
        word=str(word.word),
        probability=(float(word.probability) if word.probability is not None else None),
    )


def _segment_from_whisper(index: int, segment: Any) -> Segment:
    raw_words = getattr(segment, "words", None) or []
    return Segment(
        id=index,
        start=float(segment.start),
        end=float(segment.end),
        text=str(segment.text).strip(),
        words=tuple(_word_from_whisper(word) for word in raw_words),
    )


def _configure_model_cache() -> None:
    """Keep Hugging Face model/cache writes off read-only serverless homes."""
    if not (os.getenv("VERCEL") or Path.cwd().name.startswith("sbx_")):
        return

    cache_root = Path("/tmp/media_to_text_hf_cache")
    cache_root.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(cache_root)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(cache_root / "hub")
    os.environ["TRANSFORMERS_CACHE"] = str(cache_root / "transformers")
    os.environ["XDG_CACHE_HOME"] = str(cache_root / "xdg")


def transcribe_file(
    input_path: str | Path,
    *,
    model_name: str = "small",
    device: str = "auto",
    compute_type: str = "default",
    language: str | None = None,
    task: str = "transcribe",
    beam_size: int = 5,
    vad_filter: bool = True,
    word_timestamps: bool = False,
) -> TranscriptionResult:
    """Transcribe an audio or video file with Faster-Whisper.

    The model is loaded inside this function so importing the package does not
    download model files or require the optional runtime dependency immediately.
    """
    path = Path(input_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {path}")
    if task not in {"transcribe", "translate"}:
        raise ValueError("task must be either 'transcribe' or 'translate'")
    if beam_size < 1:
        raise ValueError("beam_size must be at least 1")

    _configure_model_cache()
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - exercised by users without deps
        raise RuntimeError(
            "faster-whisper is not installed. Run 'python -m pip install -e .'."
        ) from exc

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, info = model.transcribe(
        str(path),
        beam_size=beam_size,
        language=language,
        task=task,
        vad_filter=vad_filter,
        word_timestamps=word_timestamps,
    )
    collected = tuple(_segment_from_whisper(index, segment) for index, segment in enumerate(segments, 1))
    return TranscriptionResult(
        source=str(path),
        language=getattr(info, "language", None),
        language_probability=(
            float(info.language_probability)
            if getattr(info, "language_probability", None) is not None
            else None
        ),
        duration=(float(info.duration) if getattr(info, "duration", None) is not None else None),
        segments=collected,
    )


def _timestamp(seconds: float, separator: str = ",") -> str:
    """Format seconds as an SRT/VTT timestamp."""
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def to_txt(result: TranscriptionResult) -> str:
    return result.text + ("\n" if result.text else "")


def to_srt(result: TranscriptionResult) -> str:
    blocks = []
    for index, segment in enumerate(result.segments, 1):
        blocks.append(
            f"{index}\n{_timestamp(segment.start)} --> {_timestamp(segment.end)}\n{segment.text}\n"
        )
    return "\n".join(blocks)


def to_vtt(result: TranscriptionResult) -> str:
    blocks = ["WEBVTT\n"]
    for segment in result.segments:
        blocks.append(
            f"{_timestamp(segment.start, '.') } --> {_timestamp(segment.end, '.')}\n{segment.text}\n"
        )
    return "\n".join(blocks)


def to_json(result: TranscriptionResult) -> str:
    payload = asdict(result)
    payload["text"] = result.text
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def serialize(result: TranscriptionResult, output_format: str) -> str:
    """Serialize a result as txt, json, srt, or vtt."""
    serializers = {"txt": to_txt, "json": to_json, "srt": to_srt, "vtt": to_vtt}
    try:
        return serializers[output_format](result)
    except KeyError as exc:
        supported = ", ".join(serializers)
        raise ValueError(f"Unsupported format '{output_format}'. Choose from: {supported}") from exc


def write_outputs(
    result: TranscriptionResult,
    output_dir: str | Path,
    output_stem: str,
    output_format: str,
) -> list[Path]:
    """Write one or all supported formats and return created paths."""
    formats = ("txt", "json", "srt", "vtt") if output_format == "all" else (output_format,)
    target_dir = Path(output_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for file_format in formats:
        path = target_dir / f"{output_stem}.{file_format}"
        path.write_text(serialize(result, file_format), encoding="utf-8")
        paths.append(path)
    return paths
