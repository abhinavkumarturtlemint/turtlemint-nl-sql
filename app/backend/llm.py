"""LLM client for Google Gemini (OpenAI-compatible chat-completions endpoint).

The whole pipeline only depends on `chat()` and `chat_json()`, so swapping the
provider later means changing config (base URL / key / model), not code.
"""
from __future__ import annotations

import json
import re
import threading
import time
from typing import Dict, List

import requests

from app.backend import config

# Transient HTTP statuses worth retrying / falling back on.
_RETRYABLE = {429, 500, 502, 503, 504}

# Per-thread token-usage accounting (FastAPI runs sync endpoints in a threadpool).
_usage = threading.local()


class LLMError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(config.LLM_API_KEY)


def reset_usage() -> None:
    _usage.calls = 0
    _usage.prompt_tokens = 0
    _usage.completion_tokens = 0


def get_usage() -> Dict[str, int]:
    return {
        "calls": getattr(_usage, "calls", 0),
        "prompt_tokens": getattr(_usage, "prompt_tokens", 0),
        "completion_tokens": getattr(_usage, "completion_tokens", 0),
    }


def _record_usage(body: Dict) -> None:
    u = body.get("usage") or {}
    _usage.calls = getattr(_usage, "calls", 0) + 1
    _usage.prompt_tokens = getattr(_usage, "prompt_tokens", 0) + u.get("prompt_tokens", 0)
    _usage.completion_tokens = getattr(_usage, "completion_tokens", 0) + u.get("completion_tokens", 0)


def _models_to_try() -> List[str]:
    models = [config.LLM_MODEL]
    for m in config.LLM_FALLBACK_MODELS:
        if m and m not in models:
            models.append(m)
    return models


def _backoff(attempt: int) -> float:
    return min(0.5 * (2 ** attempt), 8.0)


def chat(messages: List[Dict[str, str]], *, temperature: float = 0.0,
         json_mode: bool = False) -> str:
    """Call the Gemini chat-completions endpoint and return the text content.

    Resilient to transient overload (503) and rate limits (429): retries with
    backoff, then falls back to the next configured model.
    """
    if not config.LLM_API_KEY:
        raise LLMError(
            "No LLM API key set. Put your Gemini key in .env as GEMINI_API_KEY=... "
            "(get one at https://aistudio.google.com/apikey)."
        )
    url = f"{config.LLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    last_err = "unknown error"
    for model in _models_to_try():
        payload: Dict = {"model": model, "messages": messages,
                         "temperature": temperature}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        for attempt in range(config.LLM_MAX_RETRIES):
            try:
                resp = requests.post(url, json=payload, headers=headers,
                                     timeout=config.LLM_TIMEOUT_S)
            except requests.RequestException as e:
                last_err = f"could not reach LLM endpoint: {e}"
                time.sleep(_backoff(attempt))
                continue
            if resp.status_code == 200:
                try:
                    body = resp.json()
                    content = body["choices"][0]["message"]["content"]
                except (KeyError, IndexError, ValueError) as e:
                    raise LLMError(f"Unexpected LLM response shape: {resp.text[:500]}") from e
                _record_usage(body)
                return content
            if resp.status_code in _RETRYABLE:
                last_err = f"{model} -> {resp.status_code}: {resp.text[:200]}"
                time.sleep(_backoff(attempt))
                continue
            # Non-retryable (e.g. 400/401/403): fail fast with a clear message.
            raise LLMError(f"LLM API error {resp.status_code}: {resp.text[:500]}")
        # Exhausted retries for this model -> try the next fallback model.
    raise LLMError(
        "The AI model is busy right now (transient overload). Please click "
        f"Generate again in a few seconds. Last error: {last_err}"
    )


def chat_json(messages: List[Dict[str, str]], *, temperature: float = 0.0) -> Dict:
    """Call the LLM expecting a JSON object back; parse it robustly."""
    content = chat(messages, temperature=temperature, json_mode=True)
    return _extract_json(content)


def _extract_json(content: str) -> Dict:
    content = content.strip()
    # Direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    # Fenced block ```json ... ``` or ``` ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    # First {...} span
    brace = re.search(r"\{.*\}", content, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass
    raise LLMError(f"LLM did not return valid JSON. Got: {content[:300]}")
