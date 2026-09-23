"""Upload a real recording to the local API and verify Redis/Celery/STT persistence.

Run after local_dev.py start. Creates a meeting in the development database and retains it
for frontend inspection. Does not print transcript contents or credentials.
"""

import argparse
import time
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--date", default="2026-09-23")
    args = parser.parse_args()
    with httpx.Client(base_url="http://127.0.0.1:8000/api/v1", timeout=60) as client:
        response = client.post(
            "/auth/login",
            json={
                "email": "admin@example.com",
                "password": "admin123",
            },
        )
        response.raise_for_status()
        with args.audio.open("rb") as audio:
            response = client.post(
                "/meetings",
                data={
                    "title": f"{args.audio.stem} — локальная проверка STT",
                    "meeting_date": args.date,
                    "output_language": "ru",
                },
                files={"file": (args.audio.name, audio, "audio/mpeg")},
            )
        response.raise_for_status()
        meeting_id = response.json()["id"]
        print(f"Created meeting {meeting_id}", flush=True)
        previous = None
        deadline = time.monotonic() + 1200
        while time.monotonic() < deadline:
            response = client.get(f"/meetings/{meeting_id}")
            response.raise_for_status()
            detail = response.json()
            state = (detail["status"], detail["progress_stage"], detail["progress_pct"])
            if state != previous:
                print(state, flush=True)
                previous = state
            if detail["status"] == "failed":
                raise RuntimeError(detail["error"])
            if detail["status"] == "draft":
                assert detail["segments"], "Expected speech in the supplied recording"
                assert (
                    detail["model_info"]["processing_mode"] == "local_offline_stt_only"
                )
                assert detail["tasks"] == detail["speaker_map"] == []
                assert detail["summary"] == ""
                assert detail["progress_pct"] == 100
                print(
                    f"PASS: meeting {meeting_id}, {len(detail['segments'])} persisted segments"
                )
                return
            time.sleep(3)
        raise TimeoutError(f"Meeting {meeting_id} still processing after 20 minutes")


if __name__ == "__main__":
    main()
