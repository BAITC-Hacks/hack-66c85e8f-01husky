"""Explicit network-enabled preparation, separate from offline transcription."""

from pipeline.settings import PipelineSettings


def main() -> None:
    from faster_whisper.utils import download_model

    settings = PipelineSettings()
    path = download_model(settings.stt_model, cache_dir=str(settings.stt_model_dir))
    print(f"Model available at: {path}")


if __name__ == "__main__":
    main()
