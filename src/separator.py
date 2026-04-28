from __future__ import annotations

import time
from pathlib import Path
from typing import Optional, Callable

import torch
import torchaudio
from demucs.pretrained import get_model
from demucs.apply import apply_model

from .utils import get_logger


AVAILABLE_MODELS = {
    "htdemucs": "Default -- good quality, fast",
    "htdemucs_ft": "Fine-tuned -- better quality, moderate speed",
    "mdx_extra": "High quality -- slower",
    "mdx_extra_q": "Highest quality -- slowest",
}


class AudioStemSeparator:
    """Loads a Demucs model and splits audio files into stems."""

    def __init__(
        self,
        model_name: str = "htdemucs",
        device: Optional[str] = None,
        log_directory: str = "./logs",
        base_filename: str = "separator",
    ):
        self.model_name = model_name
        self.logger = get_logger(base_filename, log_dir=log_directory)
        self.device = self._detect_device(device)
        self._on_status: Optional[Callable[[str], None]] = None

        self.logger.info(f"Initializing with model={model_name}, device={self.device}")
        self._load_model()

    def _status(self, msg: str):
        self.logger.info(msg)
        if self._on_status:
            self._on_status(msg)

    def _detect_device(self, device: Optional[str]) -> str:
        if device is not None:
            return device
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_model(self):
        try:
            self.model = get_model(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            self.logger.info("Model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Could not load model {self.model_name}: {e}")

    def separate_audio_file(self, audio_path: str, output_dir: str) -> bool:
        """Separate a single audio file and save the stems to output_dir."""
        start_time = time.time()
        audio_name = Path(audio_path).name

        try:
            self._status(f"Loading audio: {audio_name}")
            waveform, sample_rate = torchaudio.load(audio_path)
            duration = waveform.shape[1] / sample_rate
            self._status(f"Loaded ({sample_rate}Hz, {waveform.shape[0]}ch, {duration:.1f}s)")

            waveform = self._prepare_audio(waveform)
            self._status("Running stem separation...")
            sources = self._apply_separation(waveform)

            self._status("Saving stems...")
            stem_names = self._save_stems(sources, audio_path, output_dir, sample_rate)

            elapsed = time.time() - start_time
            self._status(f"Done: {', '.join(stem_names)} ({elapsed:.1f}s)")
            return True

        except Exception as e:
            self.logger.error(f"Failed to process {audio_name}: {e}")
            if self._on_status:
                self._on_status(f"Error: {e}")
            return False

    def _prepare_audio(self, waveform: torch.Tensor) -> torch.Tensor:
        if waveform.shape[0] == 1:
            waveform = waveform.repeat(2, 1)
        elif waveform.shape[0] > 2:
            waveform = waveform[:2]
        return waveform.to(self.device)

    def _apply_separation(self, waveform: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return apply_model(
                self.model,
                waveform.unsqueeze(0),
                device=self.device,
                progress=True,
            )[0]

    def _save_stems(self, sources: torch.Tensor, original_path: str,
                    output_dir: str, sample_rate: int) -> list[str]:
        audio_name = Path(original_path).stem
        output_subdir = Path(output_dir) / audio_name
        output_subdir.mkdir(parents=True, exist_ok=True)

        stem_names = self.model.sources
        for i, stem_name in enumerate(stem_names):
            out_path = output_subdir / f"{stem_name}.wav"
            torchaudio.save(str(out_path), sources[i].cpu(), sample_rate)

        return list(stem_names)

