from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from local_tts.backends.chatterbox_backend import ChatterboxBackend
from local_tts.config import Settings

settings = Settings.from_env()
app = FastAPI(title="Local-TTS", version="0.1.0")

_backend_cache: dict[str, ChatterboxBackend] = {}


class SpeechRequest(BaseModel):
    model: str = Field(default_factory=lambda: settings.model)
    input: str = Field(min_length=1)
    voice: str = Field(default="default")
    response_format: str = Field(default="wav")
    temperature: float | None = Field(default=None)
    top_p: float | None = Field(default=None)
    min_p: float | None = Field(default=None)
    repetition_penalty: float | None = Field(default=None)
    cfg_weight: float | None = Field(default=None)
    exaggeration: float | None = Field(default=None)


def _voice_prompt_path(voice: str) -> Path | None:
    normalized = voice.strip()
    if not normalized:
        return None

    path_candidate = Path(normalized)
    if path_candidate.suffix:
        prompt_path = settings.voices_dir / path_candidate.name
    else:
        prompt_path = settings.voices_dir / f"{path_candidate.name}.wav"

    if prompt_path.exists():
        return prompt_path
    return None


def _get_backend(model_name: str) -> ChatterboxBackend:
    key = model_name.strip().lower()
    backend = _backend_cache.get(key)
    if backend is None:
        backend = ChatterboxBackend(
            model_name=key,
            device=settings.device,
            output_rms_db=settings.output_rms_db,
            output_peak_db=settings.output_peak_db,
        )
        _backend_cache[key] = backend
    return backend


@app.on_event("startup")
def _startup() -> None:
    settings.voices_dir.mkdir(parents=True, exist_ok=True)
    if settings.preload:
        backend = _get_backend(settings.model)
        backend.load()


@app.get("/health")
def health() -> dict[str, Any]:
    loaded = {name: backend.sample_rate for name, backend in _backend_cache.items() if backend.is_loaded}
    return {
        "status": "ok",
        "model_default": settings.model,
        "device": settings.device,
        "voices_dir": str(settings.voices_dir),
        "loaded_models": loaded,
    }


@app.post("/v1/audio/speech")
def synthesize_speech(payload: SpeechRequest) -> Response:
    if payload.response_format.lower() != "wav":
        raise HTTPException(status_code=400, detail="Only response_format='wav' is currently supported.")

    prompt_path = _voice_prompt_path(payload.voice)
    if payload.voice not in {"", "default"} and prompt_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Voice prompt not found for '{payload.voice}'. Expected file in {settings.voices_dir}.",
        )

    backend = _get_backend(payload.model)
    generation_kwargs = settings.generation_defaults()
    per_request_overrides = {
        "temperature": payload.temperature,
        "top_p": payload.top_p,
        "min_p": payload.min_p,
        "repetition_penalty": payload.repetition_penalty,
        "cfg_weight": payload.cfg_weight,
        "exaggeration": payload.exaggeration,
    }
    generation_kwargs.update({k: v for k, v in per_request_overrides.items() if v is not None})

    try:
        audio_bytes = backend.synthesize(
            text=payload.input,
            voice_prompt_path=prompt_path,
            generation_kwargs=generation_kwargs,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {exc}") from exc

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"x-local-tts-model": payload.model.lower()},
    )


def main() -> None:
    import uvicorn

    uvicorn.run(
        "local_tts.app:app",
        host=os.getenv("LOCAL_TTS_HOST", settings.host),
        port=int(os.getenv("LOCAL_TTS_PORT", str(settings.port))),
        reload=False,
    )


if __name__ == "__main__":
    main()
