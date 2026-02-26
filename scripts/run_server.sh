#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Virtual environment not found at ${ROOT_DIR}/.venv"
  echo "Run ./scripts/bootstrap.sh first."
  exit 1
fi

cd "${ROOT_DIR}"

if [[ -f ".env" ]]; then
  # shellcheck disable=SC1091
  source ".env"
fi

exec "${VENV_PYTHON}" -m uvicorn local_tts.app:app \
  --host "${LOCAL_TTS_HOST:-127.0.0.1}" \
  --port "${LOCAL_TTS_PORT:-8000}"
