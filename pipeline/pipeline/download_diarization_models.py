"""Explicit model preparation. No audio/text is accepted or uploaded by this command."""

import hashlib
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen

from pipeline.settings import PipelineSettings

BASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
SEGMENTATION = "sherpa-onnx-pyannote-segmentation-3-0"
EMBEDDING = "nemo_en_titanet_large.onnx"
SHA256 = {
    "model.onnx": "220ad67ca923bef2fa91f2390c786097bf305bceb5e261d4af67b38e938e1079",
    EMBEDDING: "d51abcf31717ef28162f26acb9d44dd4127c3d44c9b8624f699f3425daca8e77",
}


def verify(path: Path) -> None:
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256[path.name]:
        raise RuntimeError("Model checksum mismatch; downloaded weights were not installed")


def download(url: str, destination: Path) -> None:
    with urlopen(url, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def main() -> None:
    directory = PipelineSettings().diarization_model_dir
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="prepare-", dir=directory) as temp:
        root = Path(temp)
        archive = root / "segmentation.tar.bz2"
        download(f"{BASE}/speaker-segmentation-models/{SEGMENTATION}.tar.bz2", archive)
        with tarfile.open(archive, "r:bz2") as tar:
            target = directory / SEGMENTATION
            target.mkdir(exist_ok=True)
            # Extract only these regular files: no paths, links, executable scripts or traversal.
            for name in ("model.onnx", "LICENSE", "README.md"):
                member = tar.getmember(f"{SEGMENTATION}/{name}")
                if not member.isfile():
                    raise RuntimeError("Unexpected archive member")
                with tar.extractfile(member) as source, (root / name).open("wb") as output:
                    shutil.copyfileobj(source, output)
                if name in SHA256:
                    verify(root / name)
                (root / name).replace(target / name)
        embedding = root / EMBEDDING
        download(f"{BASE}/speaker-recongition-models/{EMBEDDING}", embedding)
        verify(embedding)
        embedding.replace(directory / EMBEDDING)
    for path in (directory / SEGMENTATION / "model.onnx", directory / EMBEDDING):
        print(f"Prepared {path.name}: sha256={hashlib.sha256(path.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
