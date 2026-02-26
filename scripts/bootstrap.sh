#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
VENV_DIR="${ROOT_DIR}/.venv"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python interpreter not found: ${PYTHON_BIN}"
  echo "Set PYTHON_BIN to a valid interpreter, for example:"
  echo "  PYTHON_BIN=python3.11 ./scripts/bootstrap.sh"
  exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip "setuptools<81" wheel
python -m pip install -e "${ROOT_DIR}"

mkdir -p "${ROOT_DIR}/voices"

echo
echo "Bootstrap complete."
echo "Virtual environment: ${VENV_DIR}"
echo "Run the server with:"
echo "  ./scripts/run_server.sh"
