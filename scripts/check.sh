#!/usr/bin/env bash
# Local CI. GitHub Actions is off for this repo (hackathon org), so this script is the gate before any PR.
#
#   ./scripts/check.sh            lint + unit tests + HTTP smoke (needs PostgreSQL, ffmpeg, soffice)
#   ./scripts/check.sh --compose  additionally builds and exercises the full docker compose stack
#   ./scripts/check.sh --compose-only   only the docker compose stack (no host PostgreSQL needed)
#
# Host ports busy (local PostgreSQL on 5432)? Put a docker-compose.override.yml next to
# docker-compose.yml with other host ports; it is gitignored and picked up automatically.
#
# Exit code 0 = green. Every failing step is printed at the end.
set -uo pipefail
cd "$(dirname "$0")/.."

failed=()
step() {  # step <name> <command...>
  local name=$1; shift
  echo; echo "=== $name"
  if "$@"; then echo "--- ok: $name"; else echo "--- FAIL: $name"; failed+=("$name"); fi
}

need() { command -v "$1" >/dev/null || { echo "missing: $1 ($2)"; return 1; }; }
need uv "https://docs.astral.sh/uv/" || exit 1
need ffmpeg "brew install ffmpeg" || exit 1
need soffice "brew install --cask libreoffice (needed for PDF export tests)" || echo "PDF tests will be skipped"

mode="${1:-}"
if [[ "$mode" != "--compose-only" ]]; then
step "backend ruff"        bash -c "cd backend && uv run ruff check . && uv run ruff format --check ."
step "backend pytest"      bash -c "cd backend && uv run pytest -q"
step "pipeline pytest"     bash -c "cd pipeline && uv run ruff check . && uv run pytest -q"
step "bots pytest"         bash -c "cd bots && uv run ruff check . && uv run pytest -q"
step "backend http smoke"  bash -c "cd backend && uv run python scripts/smoke_backend.py"
fi

if [[ "$mode" == "--compose" || "$mode" == "--compose-only" ]]; then
  need docker "Docker Desktop" || exit 1
  [[ -f .env ]] || cp .env.example .env
  step "compose config" docker compose config --quiet
  step "compose up"     docker compose up -d --build --wait --wait-timeout 240
  step "compose api health" bash -c "curl --fail --silent --retry 10 --retry-delay 2 http://localhost:8000/api/v1/health"
  step "compose test db" docker compose exec -T postgres psql -U protocol -d protocol -v ON_ERROR_STOP=1 -c "CREATE DATABASE protocol_test OWNER protocol"
  step "compose dev deps" docker compose exec -T api uv sync --locked --dev
  step "compose pytest"  docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg://protocol:protocol@postgres:5432/protocol_test api uv run --no-sync pytest -q
  step "compose smoke via redis+celery" docker compose exec -T api uv run --no-sync python scripts/smoke_backend.py --api-url http://api:8000/api/v1
  docker compose ps
  step "compose down"    docker compose down --volumes
fi

echo
if ((${#failed[@]})); then
  printf 'FAILED: %s\n' "${failed[@]}"; exit 1
fi
echo "ALL GREEN"
