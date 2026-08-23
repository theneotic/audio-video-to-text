"""Command-line interface for media-to-text transcription."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import transcribe_file, write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="media-to-text",
        description="Transcribe an audio or video file locally with Faster-Whisper.",
    )
    parser.add_argument("input", type=Path, help="Path to an audio or video file")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("transcripts"),
        help="Directory for generated files (default: transcripts)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("txt", "json", "srt", "vtt", "all"),
        default="txt",
        help="Output format (default: txt; use all for every format)",
    )
    parser.add_argument(
        "-m",
        "--model",
        dest="model_name",
        default="small",
        help="Whisper model name or local model path (default: small)",
    )
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda"),
        default="auto",
        help="Inference device (default: auto)",
    )
    parser.add_argument(
        "--compute-type",
        default="default",
        help="Faster-Whisper compute type, such as default, int8, or float16",
    )
    parser.add_argument(
        "--language",
        help="Language code such as en or hi; omit to detect automatically",
    )
    parser.add_argument(
        "--task",
        choices=("transcribe", "translate"),
        default="transcribe",
        help="Transcribe in the source language or translate to English",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam search size (default: 5)",
    )
    parser.add_argument(
        "--no-vad-filter",
        action="store_true",
        help="Disable voice activity detection filtering",
    )
    parser.add_argument(
        "--word-timestamps",
        action="store_true",
        help="Include word-level timestamps in JSON output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input.expanduser().resolve()
    output_stem = input_path.stem

    try:
        print(f"Loading model '{args.model_name}'...")
        result = transcribe_file(
            input_path,
            model_name=args.model_name,
            device=args.device,
            compute_type=args.compute_type,
            language=args.language,
            task=args.task,
            beam_size=args.beam_size,
            vad_filter=not args.no_vad_filter,
            word_timestamps=args.word_timestamps,
        )
        paths = write_outputs(result, args.output_dir, output_stem, args.format)
    except (FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Detected language: {result.language or 'unknown'}")
    for path in paths:
        print(f"Wrote: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
