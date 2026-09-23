import io
import math
import struct
import wave


def wav_bytes(seconds: float = 1.0, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        n = int(seconds * rate)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 20))) for i in range(n)))
    return buf.getvalue()


def create_meeting(
    client, title="Планёрка", meeting_date="2026-09-23", participant_ids=(), **extra
):
    data = {"title": title, "meeting_date": meeting_date, **extra}
    if participant_ids:
        data["participant_ids"] = [str(i) for i in participant_ids]
    return client.post(
        "/api/v1/meetings",
        data=data,
        files={"file": ("rec.wav", io.BytesIO(wav_bytes()), "audio/wav")},
    )
