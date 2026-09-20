from __future__ import annotations

import os

import httpx
from fastapi import HTTPException


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
    if engine == "gemini":
        if not GEMINI_API_KEY:
            return "", "offline"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                url,
                params={"key": GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
        if response.status_code >= 400:
            raise HTTPException(502, "Gemini request failed")
        parts = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
        answer = "".join(part.get("text", "") for part in parts).strip()
        if not answer:
            raise HTTPException(502, "Gemini returned an empty response")
        return answer, GEMINI_MODEL

    if engine == "ollama":
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
                    json={"model": OLLAMA_MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False},
                )
            if response.status_code >= 400:
                raise HTTPException(502, "Ollama request failed")
            answer = response.json().get("message", {}).get("content", "").strip()
            if answer:
                return answer, OLLAMA_MODEL
        except HTTPException:
            raise
        except httpx.HTTPError:
            pass
        return "", "offline"

    return "", "offline"
