# Local-TTS

Local, free text-to-speech service built around Chatterbox.

Quality-first defaults are enabled:
- default model: `chatterbox` (full model, better quality than turbo)
- quality-oriented generation parameters from `.env`

## What this repo provides

- A local API server (`FastAPI`) with an OpenAI-style endpoint:
  - `POST /v1/audio/speech`
- Chatterbox backend with automatic device selection:
  - `mps` (Apple Silicon) -> `cuda` -> `cpu`
- Voice prompt management from local files:
  - `voices/<voice>.wav`

## Quick start (macOS)

1. Create and activate environment (uses `python3.11` by default):

```bash
cd /Users/nhunt/Documents/GitHub/Local-TTS
./scripts/bootstrap.sh
cp .env.example .env
```

If `python3.11` is not installed:

```bash
brew install python@3.11
```

2. Add a voice prompt file:

- Put a reference voice clip at:
  - `voices/default.wav`
- Recommended: 10-30 seconds, single speaker, clean audio.

3. Run the server:

```bash
./scripts/run_server.sh
```

4. Generate speech:

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chatterbox",
    "input": "Hello from a fully local Chatterbox TTS server.",
    "voice": "default",
    "response_format": "wav"
  }' \
  --output output.wav
```

You should get `output.wav` in the repo root.

## Configuration

You can set environment variables (copy from `.env.example`):

- `LOCAL_TTS_MODEL`:
  - `chatterbox` (default, quality-first)
  - `chatterbox-turbo` (faster, usually lower quality)
- `LOCAL_TTS_DEVICE`:
  - `auto` (default), `mps`, `cuda`, or `cpu`
- `LOCAL_TTS_HOST` (default `127.0.0.1`)
- `LOCAL_TTS_PORT` (default `8000`)
- `LOCAL_TTS_VOICES_DIR` (default `voices`)
- `LOCAL_TTS_PRELOAD`:
  - `true` to load model at startup
  - `false` (default) to load lazily on first request
- `LOCAL_TTS_TEMPERATURE` (default `0.65`)
- `LOCAL_TTS_TOP_P` (default `0.9`)
- `LOCAL_TTS_MIN_P` (default `0.05`)
- `LOCAL_TTS_REPETITION_PENALTY` (default `1.15`)
- `LOCAL_TTS_CFG_WEIGHT` (default `0.6`)
- `LOCAL_TTS_EXAGGERATION` (default `0.5`)
- `LOCAL_TTS_OUTPUT_RMS_DB` (default `-16.0`)
- `LOCAL_TTS_OUTPUT_PEAK_DB` (default `-1.0`)

You can also override quality per request by including any of:
`temperature`, `top_p`, `min_p`, `repetition_penalty`, `cfg_weight`, `exaggeration`.

For louder output:
- raise `LOCAL_TTS_OUTPUT_RMS_DB` (for example from `-16.0` to `-14.0`)
- keep `LOCAL_TTS_OUTPUT_PEAK_DB` near `-1.0` to avoid clipping

## Health check

```bash
curl -sS "http://127.0.0.1:8000/health"
```

## Notes

- First generation request downloads model weights and can take a while.
- If `mps` fails on your system, set `LOCAL_TTS_DEVICE=cpu`.
- Server currently returns WAV only (`response_format: "wav"`).
