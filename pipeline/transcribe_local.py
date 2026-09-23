#!/usr/bin/env python3
"""CLI using the same offline STT provider as the backend."""

import argparse
import json
from pathlib import Path

from pipeline.settings import PipelineSettings
from pipeline.stt.local_whisper import transcribe


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--language", choices=("ru", "kk", "auto"))
    parser.add_argument(
        "--offline", action="store_true", help="Always enabled; kept for compatibility"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    settings = PipelineSettings()
    if args.model:
        settings.stt_model = args.model
    if args.language:
        settings.stt_language = args.language
    try:
        result = transcribe(str(args.audio), settings)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"{exc}\n")
    output = args.output or args.audio.with_suffix(args.audio.suffix + ".transcript.json")
    payload = {
        "model": result.model,
        "language_requested": settings.stt_language,
        "language_detected": result.detected_language,
        "language_probability": result.language_probability,
        "duration_sec": result.duration,
        "privacy": "phone_iin_patterns_v1",
        "segments": [
            {"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text}
            for s in result.segments
        ],
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved local transcript: {output}")


if __name__ == "__main__":
    main()
