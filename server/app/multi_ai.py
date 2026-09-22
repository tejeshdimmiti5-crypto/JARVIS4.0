from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import httpx


@dataclass
class ModelResponse:
    provider: str
    model: str
    answer: str
    ok: bool
    error: str | None = None


def configured_models() -> list[dict[str, str]]:
    models: list[dict[str, str]] = []
    if os.getenv("GEMINI_API_KEY"):
        models.append({"provider": "gemini", "model": os.getenv("GEMINI_MODEL", "gemini-3.8-flash")})
    if os.getenv("OPENAI_API_KEY"):
        models.append({"provider": "openai", "model": os.getenv("OPENAI_MODEL", "gpt-5-mini")})
    if os.getenv("ANTHROPIC_API_KEY"):
        models.append({"provider": "anthropic", "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")})
    if os.getenv("OLLAMA_BASE_URL"):
        models.append({"provider": "ollama", "model": os.getenv("OLLAMA_MODEL", "llama3.2")})
    return models


async def _gemini(prompt: str, model: str, key: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            url,
            headers={"x-goog-api-key": key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        r.raise_for_status()
        parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
        answer = "".join(p.get("text", "") for p in parts).strip()
        if not answer:
            raise RuntimeError("Empty Gemini response")
        return answer


async def _openai(prompt: str, model: str, key: str) -> str:
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        )
        r.raise_for_status()
        answer = r.json()["choices"][0]["message"]["content"].strip()
        if not answer:
            raise RuntimeError("Empty OpenAI response")
        return answer


async def _anthropic(prompt: str, model: str, key: str) -> str:
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": model, "max_tokens": 2048, "messages": [{"role": "user", "content": prompt}]},
        )
        r.raise_for_status()
        answer = "".join(x.get("text", "") for x in r.json().get("content", []) if x.get("type") == "text").strip()
        if not answer:
            raise RuntimeError("Empty Anthropic response")
        return answer


async def _ollama(prompt: str, model: str, base_url: str) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"{base_url.rstrip('/')}/api/chat",
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False},
        )
        r.raise_for_status()
        answer = r.json().get("message", {}).get("content", "").strip()
        if not answer:
            raise RuntimeError("Empty Ollama response")
        return answer


async def ask_model(provider: str, model: str, prompt: str) -> ModelResponse:
    try:
        if provider == "gemini":
            answer = await _gemini(prompt, model, os.environ["GEMINI_API_KEY"])
        elif provider == "openai":
            answer = await _openai(prompt, model, os.environ["OPENAI_API_KEY"])
        elif provider == "anthropic":
            answer = await _anthropic(prompt, model, os.environ["ANTHROPIC_API_KEY"])
        elif provider == "ollama":
            answer = await _ollama(prompt, model, os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        else:
            raise RuntimeError(f"Unsupported provider: {provider}")
        return ModelResponse(provider, model, answer, True)
    except Exception as exc:
        return ModelResponse(provider, model, "", False, str(exc)[:240])


async def compare_models(prompt: str, selected: list[str] | None = None) -> list[ModelResponse]:
    available = configured_models()
    if selected:
        selected_set = set(selected)
        available = [m for m in available if f"{m['provider']}:{m['model']}" in selected_set or m["provider"] in selected_set]
    if not available:
        return []
    results = await asyncio.gather(*(ask_model(m["provider"], m["model"], prompt) for m in available))
    return list(results)


async def synthesize(question: str, responses: list[ModelResponse]) -> str:
    usable = [r for r in responses if r.ok and r.answer]
    if not usable:
        return "No configured AI provider returned a response."
    provider = next((r for r in usable if r.provider == "gemini"), usable[0])
    prompt = (
        "You are JARVIS synthesis engine. Compare the candidate AI answers below and produce one "
        "accurate, concise answer. Do not mention hidden reasoning. If candidates disagree, state the "
        "uncertainty instead of inventing a fact. Preserve useful code or examples.\n\n"
        f"QUESTION:\n{question}\n\n"
        + "\n\n".join(f"[{r.provider}/{r.model}]\n{r.answer}" for r in usable)
    )
    result = await ask_model(provider.provider, provider.model, prompt)
    return result.answer if result.ok else usable[0].answer
