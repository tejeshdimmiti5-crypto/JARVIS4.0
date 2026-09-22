from __future__ import annotations

import logging
import os
import asyncio

import httpx
from fastapi import HTTPException


logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
AI_ENGINE = os.getenv("AI_ENGINE", "auto").lower()


def selected_engine() -> str:
    engine = os.getenv("AI_ENGINE", AI_ENGINE).lower()
    gemini_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
    if engine in {"gemini", "ollama", "offline"}:
        return engine
    if gemini_key:
        return "gemini"
    return "offline"


async def generate_text(prompt: str) -> tuple[str, str]:
    engine = selected_engine()
    gemini_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
    gemini_model = os.getenv("GEMINI_MODEL", GEMINI_MODEL)
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL)
    ollama_model = os.getenv("OLLAMA_MODEL", OLLAMA_MODEL)

    if engine == "gemini":
        if not gemini_key:
            return "", "offline"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent"

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=15.0)) as client:
                response = None
                for attempt in range(3):
                    try:
                        response = await client.post(
                            url,
                            headers={"x-goog-api-key": gemini_key},
                            json={"contents": [{"parts": [{"text": prompt}]}]},
                        )
                    except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                        if attempt == 2:
                            logger.error("Gemini transient connection failure after retries: %s", exc)
                            raise HTTPException(503, "AI provider is temporarily unavailable. Please try again.") from exc
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                        retry_after = response.headers.get("retry-after")
                        delay = float(retry_after) if retry_after and retry_after.replace('.', '', 1).isdigit() else 1.5 * (attempt + 1)
                        await asyncio.sleep(min(delay, 5))
                        continue
                    break
        except httpx.HTTPError as exc:
            logger.error("Gemini connection error: %s", exc)
            raise HTTPException(502, "Gemini connection failed") from exc

        if response is None:
            raise HTTPException(503, "AI provider is temporarily unavailable. Please try again.")

        if response.status_code >= 400:
            safe_body = response.text[:1000].replace(gemini_key, "[REDACTED]")
            logger.error(
                "Gemini request failed: status=%s model=%s body=%s",
                response.status_code,
                gemini_model,
                safe_body,
            )
            raise HTTPException(502, "Gemini request failed")

        try:
            parts = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
        except ValueError as exc:
            logger.error("Gemini returned invalid JSON: status=%s", response.status_code)
            raise HTTPException(502, "Gemini returned invalid response") from exc

        answer = "".join(part.get("text", "") for part in parts).strip()
        if not answer:
            logger.error("Gemini returned an empty response: model=%s", gemini_model)
            raise HTTPException(502, "Gemini returned an empty response")

        return answer, gemini_model

    if engine == "ollama":
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{ollama_base_url.rstrip('/')}/api/chat",
                    json={
                        "model": ollama_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                )
            if response.status_code >= 400:
                raise HTTPException(502, "Ollama request failed")
            answer = response.json().get("message", {}).get("content", "").strip()
            if answer:
                return answer, ollama_model
        except HTTPException:
            raise
        except httpx.HTTPError:
            pass
        return "", "offline"

    return "", "offline"
