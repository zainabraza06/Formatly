"""
Multi-provider AI router for Formatly.

Priority order: Mistral -> Groq -> Gemini -> OpenRouter -> HuggingFace
On rate-limit  -> cool down that provider for 60 s, try next
On timeout     -> cool down for 30 s, try next
On other error -> cool down for 10 s, try next

The module exposes a singleton `get_router()` so cooldown state
is shared across all requests within a server process.
"""
from __future__ import annotations

import os
import time
from typing import Any

# ── Provider IDs ──────────────────────────────────────────────────────────────
MISTRAL     = "mistral"
GROQ        = "groq"
GEMINI      = "gemini"
OPENROUTER  = "openrouter"
HUGGINGFACE = "huggingface"

DEFAULT_ORDER: list[str] = [MISTRAL, GROQ, GEMINI, OPENROUTER, HUGGINGFACE]

# ── Default models ────────────────────────────────────────────────────────────
_DEFAULT_MODELS: dict[str, str] = {
    MISTRAL:     "mistral-large-latest",
    GROQ:        "llama-3.3-70b-versatile",
    GEMINI:      "gemini-1.5-flash",
    OPENROUTER:  "meta-llama/llama-3.3-70b-instruct:free",
    HUGGINGFACE: "mistralai/Mistral-7B-Instruct-v0.3",
}

# ── Cooldown durations (seconds) ─────────────────────────────────────────────
_COOLDOWN_RATE_LIMIT = 60
_COOLDOWN_TIMEOUT    = 30
_COOLDOWN_ERROR      = 10

# ── Request timeout ───────────────────────────────────────────────────────────
# Writing a whole document is a long generation: a large model emitting a few
# thousand tokens routinely runs past a minute. Too short a timeout burns the
# provider and cools it down for no reason. Override with LLM_TIMEOUT.
_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "120"))


# ── Custom exceptions ─────────────────────────────────────────────────────────
class RateLimitExceeded(Exception):
    def __init__(self, provider: str):
        super().__init__(f"{provider}: rate limit / quota exceeded")
        self.provider = provider


class ProviderTimeout(Exception):
    def __init__(self, provider: str):
        super().__init__(f"{provider}: request timed out")
        self.provider = provider


class AllProvidersFailed(Exception):
    def __init__(self, errors: dict[str, str]):
        details = " | ".join(f"{k}: {v}" for k, v in errors.items())
        super().__init__(f"All providers failed — {details}")
        self.errors = errors


def _is_placeholder(key: str) -> bool:
    """`.env.example` ships values like `your_gemini_api_key_here`. Those are
    truthy, so without this the router would 'try' the provider, fail on a bad
    key and waste a fallback rung — and `/providers/status` would claim ready."""
    if not key:
        return True
    low = key.lower()
    return (low.startswith(("your_", "<", "changeme", "replace_"))
            or low.endswith(("_here", "_key_here"))
            or low in {"none", "null", "todo"})


# ── Router ────────────────────────────────────────────────────────────────────
class ProviderRouter:
    def __init__(self) -> None:
        self._cooldowns: dict[str, float] = {}

    # ── config helpers ────────────────────────────────────────────────────────
    def _key(self, provider: str) -> str:
        raw = os.environ.get(
            {
                MISTRAL:     "MISTRAL_API_KEY",
                GROQ:        "GROQ_API_KEY",
                GEMINI:      "GEMINI_API_KEY",
                OPENROUTER:  "OPENROUTER_API_KEY",
                HUGGINGFACE: "HUGGINGFACE_API_KEY",
            }[provider],
            "",
        ).strip()
        return "" if _is_placeholder(raw) else raw

    def _model(self, provider: str) -> str:
        return os.environ.get(
            {
                MISTRAL:     "MISTRAL_MODEL",
                GROQ:        "GROQ_MODEL",
                GEMINI:      "GEMINI_MODEL",
                OPENROUTER:  "OPENROUTER_MODEL",
                HUGGINGFACE: "HUGGINGFACE_MODEL",
            }[provider],
            _DEFAULT_MODELS[provider],
        )

    def _in_cooldown(self, provider: str) -> tuple[bool, int]:
        exp = self._cooldowns.get(provider, 0)
        remaining = int(exp - time.time())
        return remaining > 0, max(remaining, 0)

    def _cool(self, provider: str, secs: float) -> None:
        self._cooldowns[provider] = time.time() + secs

    # ── per-provider callers ──────────────────────────────────────────────────
    def _call_mistral(self, messages: list[dict[str, str]], max_tokens: int) -> str:
        import httpx

        try:
            resp = httpx.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._key(MISTRAL)}",
                    "Content-Type":  "application/json",
                    "Accept":        "application/json",
                },
                json={
                    "model":      self._model(MISTRAL),
                    "messages":   messages,
                    "max_tokens": max_tokens,
                },
                timeout=_TIMEOUT,
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeout(MISTRAL) from exc

        if resp.status_code == 429:
            raise RateLimitExceeded(MISTRAL)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_groq(self, messages: list[dict[str, str]], max_tokens: int) -> str:
        from groq import Groq

        try:
            from groq import RateLimitError as _GroqRL
        except ImportError:
            _GroqRL = None  # type: ignore[assignment]

        try:
            client = Groq(api_key=self._key(GROQ))
            resp = client.chat.completions.create(
                model=self._model(GROQ),
                messages=messages,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                timeout=_TIMEOUT,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            if _GroqRL and isinstance(exc, _GroqRL):
                raise RateLimitExceeded(GROQ) from exc
            if "429" in str(exc) or "rate" in str(exc).lower():
                raise RateLimitExceeded(GROQ) from exc
            raise

    def _call_gemini(self, messages: list[dict[str, str]], max_tokens: int) -> str:
        from google import genai  # type: ignore[import]
        from google.genai import types  # type: ignore[import]

        client = genai.Client(api_key=self._key(GEMINI))

        system_msg = next(
            (m["content"] for m in messages if m["role"] == "system"), None
        )
        user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )

        try:
            resp = client.models.generate_content(
                model=self._model(GEMINI),
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=system_msg,
                    max_output_tokens=max_tokens,
                ),
            )
            return resp.text or ""
        except Exception as exc:
            s = str(exc).lower()
            if "quota" in s or "429" in s or "resource exhausted" in s or "rate" in s:
                raise RateLimitExceeded(GEMINI) from exc
            raise

    def _call_openrouter(self, messages: list[dict[str, str]], max_tokens: int) -> str:
        import httpx

        try:
            resp = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._key(OPENROUTER)}",
                    "Content-Type":  "application/json",
                    "HTTP-Referer":  "https://formatly.app",
                    "X-Title":       "Formatly",
                },
                json={
                    "model":      self._model(OPENROUTER),
                    "messages":   messages,
                    "max_tokens": max_tokens,
                },
                timeout=_TIMEOUT,
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeout(OPENROUTER) from exc

        if resp.status_code == 429:
            raise RateLimitExceeded(OPENROUTER)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_huggingface(self, messages: list[dict[str, str]], max_tokens: int) -> str:
        import httpx

        model = self._model(HUGGINGFACE)
        try:
            resp = httpx.post(
                "https://router.huggingface.co/hf-inference/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._key(HUGGINGFACE)}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":      model,
                    "messages":   messages,
                    "max_tokens": max_tokens,
                },
                timeout=_TIMEOUT,
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeout(HUGGINGFACE) from exc

        if resp.status_code == 429:
            raise RateLimitExceeded(HUGGINGFACE)
        if resp.status_code == 503:
            raise ProviderTimeout(HUGGINGFACE)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    # ── public interface ──────────────────────────────────────────────────────
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 1500,
        order: list[str] | None = None,
    ) -> tuple[str, str, float]:
        """
        Try providers in priority order until one succeeds.

        Returns
        -------
        (text, provider_used, elapsed_seconds)

        Raises
        ------
        AllProvidersFailed — when every configured provider fails.
        """
        _callers = {
            MISTRAL:     self._call_mistral,
            GROQ:        self._call_groq,
            GEMINI:      self._call_gemini,
            OPENROUTER:  self._call_openrouter,
            HUGGINGFACE: self._call_huggingface,
        }
        errors: dict[str, str] = {}

        for provider in (order or DEFAULT_ORDER):
            if not self._key(provider):
                continue

            in_cd, remaining = self._in_cooldown(provider)
            if in_cd:
                errors[provider] = f"cooldown {remaining}s"
                continue

            try:
                t0 = time.time()
                text = _callers[provider](messages, max_tokens)
                return text, provider, round(time.time() - t0, 3)

            except RateLimitExceeded:
                self._cool(provider, _COOLDOWN_RATE_LIMIT)
                errors[provider] = "rate_limited (60s cooldown)"

            except ProviderTimeout:
                self._cool(provider, _COOLDOWN_TIMEOUT)
                errors[provider] = "timeout (30s cooldown)"

            except Exception as exc:
                self._cool(provider, _COOLDOWN_ERROR)
                errors[provider] = str(exc)[:120]

        raise AllProvidersFailed(errors)

    def status(self) -> dict[str, Any]:
        """Return health snapshot for every provider."""
        now = time.time()
        out: dict[str, Any] = {}
        for p in DEFAULT_ORDER:
            exp = self._cooldowns.get(p, 0)
            remaining = int(exp - now)
            has_key = bool(self._key(p))
            if not has_key:
                state = "no_key"
            elif remaining > 0:
                state = f"cooldown_{remaining}s"
            else:
                state = "ready"
            out[p] = {
                "state":   state,
                "model":   self._model(p),
                "has_key": has_key,
            }
        return out

    def reset_cooldowns(self) -> None:
        """Clear all cooldowns (useful in tests)."""
        self._cooldowns.clear()


# ── Module-level singleton ────────────────────────────────────────────────────
_router: ProviderRouter | None = None


def get_router() -> ProviderRouter:
    global _router
    if _router is None:
        _router = ProviderRouter()
    return _router
