from pathlib import Path

import pytest

from media_to_text.cli import build_parser
from media_to_text.core import Segment, TranscriptionResult, Word, serialize, write_outputs


@pytest.fixture
def result() -> TranscriptionResult:
    return TranscriptionResult(
        source="sample.mp4",
        language="en",
        language_probability=0.99,
        duration=3.5,
        segments=(
            Segment(
                id=1,
                start=0.0,
                end=1.25,
                text="Hello world.",
                words=(Word(0.0, 0.5, "Hello", 0.98), Word(0.5, 1.25, " world.", 0.97)),
            ),
            Segment(id=2, start=1.5, end=3.5, text="This is a test."),
        ),
    )


def test_result_text_joins_segments(result: TranscriptionResult) -> None:
    assert result.text == "Hello world.\nThis is a test."


def test_srt_serialization(result: TranscriptionResult) -> None:
    output = serialize(result, "srt")
    assert "1\n00:00:00,000 --> 00:00:01,250\nHello world." in output
    assert "2\n00:00:01,500 --> 00:00:03,500\nThis is a test." in output


def test_vtt_serialization(result: TranscriptionResult) -> None:
    output = serialize(result, "vtt")
    assert output.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:01.250" in output


def test_json_serialization_includes_metadata_and_words(result: TranscriptionResult) -> None:
    output = serialize(result, "json")
    assert '"language": "en"' in output
    assert '"word": "Hello"' in output
    assert '"text": "Hello world.\\nThis is a test."' in output


def test_write_all_formats(tmp_path: Path, result: TranscriptionResult) -> None:
    paths = write_outputs(result, tmp_path, "sample", "all")
    assert {path.suffix for path in paths} == {".txt", ".json", ".srt", ".vtt"}
    assert all(path.exists() for path in paths)


def test_invalid_format_is_rejected(result: TranscriptionResult) -> None:
    with pytest.raises(ValueError, match="Unsupported format"):
        serialize(result, "docx")


def test_cli_parser_accepts_common_options() -> None:
    args = build_parser().parse_args(
        ["video.mp4", "--format", "all", "--model", "tiny", "--language", "en", "--word-timestamps"]
    )
    assert args.input.name == "video.mp4"
    assert args.format == "all"
    assert args.model_name == "tiny"
    assert args.language == "en"
    assert args.word_timestamps is True
