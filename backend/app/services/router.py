"""
AI provider client for Formatly.

Mistral is the only provider. The router shape is kept — a provider list, a
cooldown table, `status()` — because the rest of the app talks to it that way
and because a second provider may return; but there is exactly one rung now,
so a failure is a failure rather than a silent downgrade to a weaker model.

On rate-limit  -> cool down for 60 s
On timeout     -> cool down for 30 s
On other error -> cool down for 10 s

The module exposes a singleton `get_router()` so cooldown state
is shared across all requests within a server process.
"""
from __future__ import annotations

import os
import time
from typing import Any

# ── Provider IDs ──────────────────────────────────────────────────────────────
MISTRAL = "mistral"

DEFAULT_ORDER: list[str] = [MISTRAL]

# ── Default models ────────────────────────────────────────────────────────────
_DEFAULT_MODELS: dict[str, str] = {
    MISTRAL: "mistral-large-latest",
}

# ── Cooldown durations (seconds) ─────────────────────────────────────────────
_COOLDOWN_RATE_LIMIT = 60
_COOLDOWN_TIMEOUT    = 30
_COOLDOWN_ERROR      = 10

# ── Request timeout ───────────────────────────────────────────────────────────
# A fixed deadline cannot be right for both a 500-token edit and an 8000-token
# document: measured throughput is ~60 tok/s, so a full-length reply needs over
# two minutes and a flat 120 s aborted the request while the model was still
# writing. Derive the deadline from what we asked for instead, at a throughput
# floor well under what the API actually delivers. LLM_TIMEOUT overrides.
_TOKENS_PER_SEC_FLOOR = 40.0
_HANDSHAKE_SECONDS    = 30.0
_TIMEOUT_OVERRIDE     = float(os.environ.get("LLM_TIMEOUT", "0")) or None


def _timeout_for(max_tokens: int) -> float:
    """Seconds to allow for a request budgeted at `max_tokens` of output."""
    if _TIMEOUT_OVERRIDE:
        return _TIMEOUT_OVERRIDE
    return _HANDSHAKE_SECONDS + max(0, max_tokens) / _TOKENS_PER_SEC_FLOOR


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
        details = " | ".join(f"{k}: {v}" for k, v in errors.items()) or "no provider configured"
        super().__init__(f"All providers failed — {details}")
        self.errors = errors


def _is_placeholder(key: str) -> bool:
    """`.env.example` ships values like `your_mistral_api_key_here`. Those are
    truthy, so without this the router would 'try' the provider, fail on a bad
    key — and `/providers/status` would claim ready."""
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
        raw = os.environ.get({MISTRAL: "MISTRAL_API_KEY"}[provider], "").strip()
        return "" if _is_placeholder(raw) else raw

    def _model(self, provider: str) -> str:
        return os.environ.get({MISTRAL: "MISTRAL_MODEL"}[provider],
                              _DEFAULT_MODELS[provider])

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
                timeout=_timeout_for(max_tokens),
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeout(MISTRAL) from exc

        if resp.status_code == 429:
            raise RateLimitExceeded(MISTRAL)
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
        Send `messages` to the configured provider.

        Returns
        -------
        (text, provider_used, elapsed_seconds)

        Raises
        ------
        AllProvidersFailed — when every configured provider fails.
        """
        _callers = {MISTRAL: self._call_mistral}
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
                errors[provider] = (
                    f"timed out after {_timeout_for(max_tokens):.0f}s "
                    "(30s cooldown)"
                )

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
