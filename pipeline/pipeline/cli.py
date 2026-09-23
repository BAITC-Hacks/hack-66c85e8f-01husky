"""python -m pipeline.cli <audio> --date 2026-09-23 [--participants p.json] [--directions a,b] [--lang ru|kk]"""

import argparse
import json
from datetime import date
from pathlib import Path

from pipeline import process
from pipeline.models import Participant

DEFAULT_DIRECTIONS = ["Финансы", "Кадры", "ИТ", "Юридическое", "Закупки", "Производство", "Другое"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--date", required=True)
    ap.add_argument("--participants", help="JSON list of {id, name, role?, voice_embedding?}")
    ap.add_argument("--directions", default=",".join(DEFAULT_DIRECTIONS))
    ap.add_argument("--lang", default="ru", choices=["ru", "kk"])
    args = ap.parse_args()

    participants: list[Participant] = []
    if args.participants:
        participants = [Participant(**p) for p in json.loads(Path(args.participants).read_text())]

    def progress(stage: str, pct: float) -> None:
        print(f"[{stage}] {pct:.0%}", flush=True)

    result = process(
        args.audio,
        date.fromisoformat(args.date),
        participants,
        args.directions.split(","),
        args.lang,
        progress,
    )
    print(result.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
