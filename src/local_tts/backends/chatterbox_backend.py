from __future__ import annotations

import inspect
import io
import wave
from pathlib import Path
from typing import Any

import torch


def _select_device(requested: str) -> str:
    requested = requested.strip().lower()
    if requested != "auto":
        return requested
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _filter_kwargs(func: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return kwargs
    accepted = set(signature.parameters.keys())
    return {key: value for key, value in kwargs.items() if key in accepted}


def _is_signature_type_error(exc: TypeError) -> bool:
    message = str(exc).lower()
    signatures = (
        "missing 1 required positional argument",
        "missing required positional argument",
        "got an unexpected keyword argument",
        "takes",
        "positional argument",
        "positional arguments",
    )
    return any(fragment in message for fragment in signatures)


def _db_to_amp(db: float) -> float:
    return 10.0 ** (db / 20.0)


def _normalize_output_levels(audio: torch.Tensor, target_rms_db: float, target_peak_db: float) -> torch.Tensor:
    # Boost quiet clips toward a speech-friendly RMS while never exceeding target peak.
    peak = float(audio.abs().max().item())
    if peak <= 1e-8:
        return audio

    peak_gain = _db_to_amp(target_peak_db) / peak
    rms = float(torch.sqrt(torch.mean(audio.pow(2))).item())
    rms_gain = max(1.0, _db_to_amp(target_rms_db) / max(rms, 1e-8))

    gain = min(peak_gain, rms_gain)
    if gain <= 0.0:
        return audio
    return audio * gain


def _to_wav_bytes(audio: Any, sample_rate: int, target_rms_db: float, target_peak_db: float) -> bytes:
    if isinstance(audio, tuple):
        audio = audio[0]
    if isinstance(audio, dict):
        audio = audio.get("audio", audio.get("wav", audio))

    if isinstance(audio, torch.Tensor):
        tensor = audio.detach().float().cpu().squeeze()
    else:
        tensor = torch.as_tensor(audio).float().cpu().squeeze()

    if tensor.ndim == 0:
        raise ValueError("Model returned an empty audio tensor.")
    if tensor.ndim > 1:
        tensor = tensor[0]

    tensor = _normalize_output_levels(tensor, target_rms_db=target_rms_db, target_peak_db=target_peak_db)
    pcm = torch.clamp(tensor, -1.0, 1.0)
    pcm = (pcm * 32767.0).short().numpy()

    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())
        return buffer.getvalue()


class ChatterboxBackend:
    def __init__(self, model_name: str, device: str, output_rms_db: float, output_peak_db: float) -> None:
        self.model_name = model_name.strip().lower()
        self.device = _select_device(device)
        self.output_rms_db = output_rms_db
        self.output_peak_db = output_peak_db
        self._model: Any | None = None
        self._sample_rate = 24_000

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self._model is not None:
            return

        from chatterbox import tts as chatterbox_tts

        requested_turbo = self.model_name in {"chatterbox-turbo", "turbo"}
        class_order = (
            ["ChatterboxTurboTTS", "ChatterboxTTS"] if requested_turbo else ["ChatterboxTTS", "ChatterboxTurboTTS"]
        )

        model = None
        for class_name in class_order:
            model_cls = getattr(chatterbox_tts, class_name, None)
            if model_cls is None:
                continue
            from_pretrained = getattr(model_cls, "from_pretrained", None)
            if from_pretrained is None:
                continue

            model = self._load_pretrained_instance(from_pretrained)
            if model is None:
                continue
            break

        if model is None:
            raise RuntimeError("Unable to load a Chatterbox model from chatterbox-tts.")

        for attr in ("sample_rate", "sampling_rate", "sr"):
            value = getattr(model, attr, None)
            if isinstance(value, int) and value > 0:
                self._sample_rate = value
                break

        self._model = model

    def _load_pretrained_instance(self, from_pretrained: Any) -> Any | None:
        attempts = (
            lambda: from_pretrained(device=self.device),
            lambda: from_pretrained(self.device),
            lambda: from_pretrained(),
        )

        last_error: Exception | None = None
        for attempt in attempts:
            try:
                model = attempt()
                move_to = getattr(model, "to", None)
                if callable(move_to):
                    model = move_to(self.device)
                return model
            except TypeError as exc:
                if not _is_signature_type_error(exc):
                    raise
                last_error = exc

        if last_error is not None:
            raise last_error
        return None

    def synthesize(
        self,
        text: str,
        voice_prompt_path: Path | None = None,
        generation_kwargs: dict[str, Any] | None = None,
    ) -> bytes:
        if self._model is None:
            self.load()
        assert self._model is not None

        generate = getattr(self._model, "generate", None)
        if not callable(generate):
            raise RuntimeError("Loaded Chatterbox model does not expose a callable generate() method.")

        kwargs: dict[str, Any] = dict(generation_kwargs or {})
        if voice_prompt_path is not None:
            kwargs["audio_prompt_path"] = str(voice_prompt_path)

        filtered_kwargs = _filter_kwargs(generate, kwargs)
        result = generate(text, **filtered_kwargs)

        result_sample_rate = self._sample_rate
        if isinstance(result, tuple) and len(result) > 1 and isinstance(result[1], int):
            result_sample_rate = result[1]
        elif isinstance(result, dict):
            dict_sample_rate = result.get("sample_rate")
            if isinstance(dict_sample_rate, int):
                result_sample_rate = dict_sample_rate

        return _to_wav_bytes(
            result,
            sample_rate=result_sample_rate,
            target_rms_db=self.output_rms_db,
            target_peak_db=self.output_peak_db,
        )
