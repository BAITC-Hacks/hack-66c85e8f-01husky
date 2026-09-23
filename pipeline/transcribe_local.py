#!/usr/bin/env python3
"""Offline transcription with a locally cached faster-whisper model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / ".models"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe audio locally with faster-whisper. No audio is uploaded."
    )
    parser.add_argument("audio", type=Path, help="Path to an audio or video file")
    parser.add_argument(
        "--model",
        default="large-v3-turbo",
        help="Whisper model to use (default: large-v3-turbo)",
    )
    parser.add_argument(
        "--language",
        choices=("ru", "kk"),
        help="Force a language; omit to detect it automatically.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Refuse model downloads and use only a model already cached locally.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON path (default: <audio>.transcript.json)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.audio.is_file():
        print(f"Audio file not found: {args.audio}", file=sys.stderr)
        return 2

    MODELS_DIR.mkdir(exist_ok=True)
    output = args.output or args.audio.with_suffix(args.audio.suffix + ".transcript.json")
    model = WhisperModel(
        args.model,
        device="cpu",
        compute_type="int8",
        download_root=str(MODELS_DIR),
        local_files_only=args.offline,
    )
    segments, info = model.transcribe(
        str(args.audio),
        language=args.language,
        vad_filter=True,
        beam_size=5,
        word_timestamps=True,
    )

    payload = {
        "model": args.model,
        "language_requested": args.language,
        "language_detected": info.language,
        "language_probability": info.language_probability,
        "segments": [
            {
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "text": segment.text.strip(),
                "words": [
                    {"start": round(word.start, 3), "end": round(word.end, 3), "word": word.word}
                    for word in (segment.words or [])
                ],
            }
            for segment in segments
        ],
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved local transcript: {output}")
    print(f"Detected language: {info.language} ({info.language_probability:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
