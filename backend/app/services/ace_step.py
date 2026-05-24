import os
import json
import time
import asyncio
import shutil
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse, parse_qs

import httpx

from backend.app.core.config import settings

logger = logging.getLogger("spotigem.ace_step")

POLL_INTERVAL = 3.0
GEN_TIMEOUT = 600.0


class ACEStepService:
    """Client for the ACE Step API server (acestep-api on port 8001).

    Uses the /release_task + /query_result + /v1/audio workflow documented at:
    https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/API.md
    """

    def __init__(self):
        self.ace_api_url = os.getenv("ACESTEP_API_URL", "http://localhost:8001")
        self._loaded = False
        self._models_initialized = False

    def is_loaded(self) -> bool:
        return self._loaded

    async def check_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.ace_api_url}/health")
                if resp.status_code == 200:
                    self._loaded = True
                    body = resp.json()
                    data = body.get("data", body)
                    self._models_initialized = data.get("models_initialized", False)
                    return True
        except Exception:
            pass
        self._loaded = False
        return False

    async def load(self) -> bool:
        available = await self.check_available()
        if not available:
            logger.warning("ACE Step API not available. Start with: uv run acestep-api")
            return False
        if not self._models_initialized:
            logger.info("Initializing ACE Step models via /v1/init...")
            try:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    init_resp = await client.post(
                        f"{self.ace_api_url}/v1/init",
                        json={
                            "model": "acestep-v15-turbo",
                            "init_llm": True,
                            "lm_model_path": os.getenv(
                                "ACESTEP_LM_MODEL_PATH", "acestep-5Hz-lm-0.6B"
                            ),
                        },
                    )
                    init_resp.raise_for_status()
                    init_data = init_resp.json().get("data", {})
                    loaded = init_data.get("loaded_model")
                    loaded_lm = init_data.get("loaded_lm_model")
                    logger.info(f"ACE Step models initialized: DiT={loaded}, LM={loaded_lm}")
                    self._models_initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize ACE Step models: {e}")
                return False
        logger.info("ACE Step API is available and models are loaded")
        return True

    async def unload(self):
        self._loaded = False

    async def _submit_and_wait(
        self,
        client: httpx.AsyncClient,
        payload: dict,
        timeout: float = GEN_TIMEOUT,
        poll_interval: float = POLL_INTERVAL,
    ) -> dict:
        resp = await client.post(f"{self.ace_api_url}/release_task", json=payload)
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data", body)
        task_id = data.get("task_id")
        if not task_id:
            raise RuntimeError(f"No task_id in release_task response: {body}")

        logger.info(f"ACE Step task submitted: {task_id}")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            await asyncio.sleep(poll_interval)
            qr = await client.post(
                f"{self.ace_api_url}/query_result",
                json={"task_id_list": [task_id]},
            )
            qr.raise_for_status()
            qr_body = qr.json()
            results = qr_body.get("data", qr_body)
            if isinstance(results, list) and results:
                item = results[0]
                status = item.get("status", 0)
                if status == 1:
                    result_raw = item.get("result", "[]")
                    if isinstance(result_raw, str):
                        result_list = json.loads(result_raw)
                    else:
                        result_list = result_raw
                    if isinstance(result_list, list) and result_list:
                        return result_list[0]
                elif status == 2:
                    result_raw = item.get("result", "[]")
                    raise RuntimeError(f"ACE Step generation failed: {result_raw}")

        raise RuntimeError(f"ACE Step generation timed out after {timeout}s")

    @staticmethod
    def _resolve_audio_path(file_url: str) -> str:
        if not file_url:
            return ""
        if file_url.startswith("/v1/audio"):
            parsed = urlparse(file_url)
            qs = parse_qs(parsed.query)
            paths = qs.get("path", [])
            if paths:
                return unquote(paths[0])
        return unquote(file_url)

    async def _download_audio(
        self,
        client: httpx.AsyncClient,
        file_url: str,
        output_path: Path,
    ) -> str:
        local_path = self._resolve_audio_path(file_url)
        if local_path and os.path.isfile(local_path):
            shutil.copy2(local_path, str(output_path))
            logger.info(f"Generation complete (local copy): {output_path.name}")
            return str(output_path)

        if file_url.startswith("/v1/audio") or file_url.startswith("http"):
            url = file_url if file_url.startswith("http") else f"{self.ace_api_url}{file_url}"
            audio_resp = await client.get(url, follow_redirects=True)
            audio_resp.raise_for_status()
            with open(str(output_path), "wb") as f:
                f.write(audio_resp.content)
            logger.info(f"Generation complete (downloaded): {output_path.name}")
            return str(output_path)

        if local_path:
            try:
                audio_resp = await client.get(
                    f"{self.ace_api_url}/v1/audio",
                    params={"path": local_path},
                    follow_redirects=True,
                )
                audio_resp.raise_for_status()
                with open(str(output_path), "wb") as f:
                    f.write(audio_resp.content)
                logger.info(f"Generation complete (via /v1/audio): {output_path.name}")
                return str(output_path)
            except Exception as e:
                logger.warning(f"Failed to download via /v1/audio: {e}")

        raise RuntimeError(f"Cannot resolve audio file from: {file_url}")

    async def generate(
        self,
        prompt: str,
        lyrics: Optional[str] = None,
        audio_duration: float = 30.0,
        record_id: Optional[int] = None,
        seed: int = -1,
        genre: Optional[str] = None,
        bpm: Optional[int] = None,
        key_scale: str = "",
        time_signature: str = "",
        vocal_language: str = "en",
        inference_steps: int = 8,
        guidance_scale: float = 7.0,
        audio_format: str = "mp3",
        batch_size: int = 1,
        **kwargs,
    ) -> str:
        if not self._loaded:
            success = await self.load()
            if not success:
                raise RuntimeError("ACE Step API not available. Start with: uv run acestep-api")

        payload = {
            "prompt": prompt,
            "lyrics": lyrics or "",
            "audio_duration": audio_duration,
            "use_random_seed": seed < 0,
            "seed": seed if seed >= 0 else -1,
            "inference_steps": inference_steps,
            "guidance_scale": guidance_scale,
            "audio_format": audio_format,
            "vocal_language": vocal_language,
            "task_type": "text2music",
            "batch_size": batch_size,
        }
        if bpm:
            payload["bpm"] = bpm
        if key_scale:
            payload["key_scale"] = key_scale
        if time_signature:
            payload["time_signature"] = time_signature

        output_dir = Path(settings.OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = audio_format if audio_format in ("wav", "flac") else "mp3"
        filename = f"track_{record_id}.{ext}" if record_id else f"track_{int(time.time() * 1000)}.{ext}"
        output_path = output_dir / filename

        async with httpx.AsyncClient(timeout=GEN_TIMEOUT + 60) as client:
            result = await self._submit_and_wait(client, payload)
            file_url = result.get("file", "")
            return await self._download_audio(client, file_url, output_path)

    async def generate_with_hit_profile(
        self,
        prompt: str,
        hit_profile: dict,
        lyrics: Optional[str] = None,
        audio_duration: float = 30.0,
    ) -> str:
        enhanced_prompt = prompt
        bpm = None
        key_scale = ""

        if hit_profile:
            profile_parts = []
            if hit_profile.get("avg_danceability", 0) > 0.65:
                profile_parts.append("danceable groove")
            if hit_profile.get("avg_energy", 0) > 0.65:
                profile_parts.append("high-energy")
            if hit_profile.get("avg_valence", 0) > 0.6:
                profile_parts.append("uplifting positive mood")
            elif hit_profile.get("avg_valence", 0) < 0.4:
                profile_parts.append("melancholic emotional mood")

            avg_tempo = hit_profile.get("avg_tempo")
            if avg_tempo:
                bpm = int(round(avg_tempo))
                if avg_tempo > 140:
                    profile_parts.append("fast-paced")
                elif avg_tempo > 110:
                    profile_parts.append("mid-upbeat")
                elif avg_tempo > 85:
                    profile_parts.append("mid-tempo")
                else:
                    profile_parts.append("slow ballad tempo")

            if profile_parts:
                enhanced_prompt = f"{', '.join(profile_parts)}, {prompt}"

        return await self.generate(
            prompt=enhanced_prompt,
            lyrics=lyrics,
            audio_duration=audio_duration,
            bpm=bpm,
            key_scale=key_scale,
        )
