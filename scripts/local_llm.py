"""Foreground local-only Ollama: backend/.venv/bin/python scripts/local_llm.py.

Prepare weights once in another terminal: OLLAMA_HOST=127.0.0.1:11434 ollama pull qwen3:8b
No user audio/text is involved in downloading weights. Processing never downloads a model.
"""

import os
import shutil
from pathlib import Path


def main():
    executable = shutil.which("ollama")
    if not executable:
        raise SystemExit("Install Ollama first (macOS: brew install ollama)")
    root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "OLLAMA_HOST": "127.0.0.1:11434",
        "OLLAMA_NO_CLOUD": "1",
        "OLLAMA_MODELS": str(root / "pipeline" / ".models" / "ollama"),
        "OLLAMA_NUM_PARALLEL": "1",
        "OLLAMA_MAX_LOADED_MODELS": "1",
        "OLLAMA_FLASH_ATTENTION": "1",
        "OLLAMA_KV_CACHE_TYPE": "q8_0",
    }
    os.execve(executable, [executable, "serve"], env)


if __name__ == "__main__":
    main()
