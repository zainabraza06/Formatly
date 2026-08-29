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
import threading
import time
from typing import Any, Optional

import httpx

# ── Provider IDs ──────────────────────────────────────────────────────────────
MISTRAL = "mistral"

DEFAULT_ORDER: list[str] = [MISTRAL]

# ── Default models ────────────────────────────────────────────────────────────
_DEFAULT_MODELS: dict[str, str] = {
    MISTRAL: "mistral-large-latest",
}

# What to ask when the model above will not answer — busy, or not included in
# the account's plan. Tried in order, largest first, because the reason to leave
# a model is rarely a reason to leave its whole family. Set the matching
# MISTRAL_LIGHT_MODEL to override with a comma-separated list, or "" to turn the
# ladder off.
_LIGHT_MODELS: dict[str, tuple[str, ...]] = {
    MISTRAL: ("mistral-medium-latest", "mistral-small-latest"),
}

# ── Cooldown durations (seconds) ─────────────────────────────────────────────
_COOLDOWN_RATE_LIMIT = 60
_COOLDOWN_TIMEOUT    = 30
_COOLDOWN_ERROR      = 10

# "Service temporarily unavailable due to high load, please retry" is what the
# API says when it is busy, and it often means it: a request that fails this way
# frequently succeeds a second later. Spending the whole attempt on it — and
# then cooling the provider off for ten seconds — turned a blip into two
# commands planned by the heuristic.
_RETRY_STATUSES = (500, 502, 503, 504)
_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF  = 0.7

# How long to wait out a rate limit when the caller can afford to. Free tiers
# meter by the second, and a long rewrite fires a pass as fast as the last one
# finished, so this is usually all it takes.
_RATE_LIMIT_PAUSE = 2.5

# How many times a patient caller re-asks a provider that is rate limiting it.
# More than the busy-server ladder, because a limit measured per minute needs
# outwaiting rather than out-persisting.
_RATE_LIMIT_ATTEMPTS = 5

# The longest a patient caller will sit out a cooldown rather than give up on
# the pass. Long enough to cover the minute a rate limit costs.
_MAX_COOLDOWN_WAIT = 70

# "This model is not available in your subscription tier", and its cousin, a
# model name the account cannot see. Asking again changes nothing — the account
# will not have grown a subscription in seven tenths of a second — but asking a
# *different* model is exactly the right move, and the lighter one is usually
# the one a tier includes.
_WRONG_MODEL_STATUSES = (403, 404)

# ── Request timeout ───────────────────────────────────────────────────────────
# A fixed deadline cannot be right for both a 500-token edit and an 8000-token
# document: measured throughput is ~60 tok/s, so a full-length reply needs over
# two minutes and a flat 120 s aborted the request while the model was still
# writing. Derive the deadline from what we asked for instead, at a throughput
# floor well under what the API actually delivers. LLM_TIMEOUT overrides.
_TOKENS_PER_SEC_FLOOR = 40.0
_HANDSHAKE_SECONDS    = 30.0
_TIMEOUT_OVERRIDE     = float(os.environ.get("LLM_TIMEOUT", "0")) or None


def _timeout_for(max_tokens: int, requested: Optional[float] = None) -> float:
    """Seconds to allow for a request budgeted at `max_tokens` of output.

    A caller may ask for less. Deriving the deadline from the token budget is
    right for a long reply and wrong for a short interactive one: a plan is a
    few hundred bytes of JSON, and waiting the better part of a minute for it
    before falling back to a rule leaves someone watching a still screen.
    """
    if _TIMEOUT_OVERRIDE:
        return _TIMEOUT_OVERRIDE
    derived = _HANDSHAKE_SECONDS + max(0, max_tokens) / _TOKENS_PER_SEC_FLOOR
    return min(derived, requested) if requested else derived


# ── Custom exceptions ─────────────────────────────────────────────────────────
class RateLimitExceeded(Exception):
    def __init__(self, provider: str, retry_after: Optional[float] = None):
        super().__init__(f"{provider}: rate limit / quota exceeded")
        self.provider = provider
        # What the server said to wait, when it says. Guessing is worse than
        # being told.
        self.retry_after = retry_after


class ProviderTimeout(Exception):
    def __init__(self, provider: str):
        super().__init__(f"{provider}: request timed out")
        self.provider = provider


class GenerationCancelled(Exception):
    """The caller went away. Raised so the work unwinds instead of finishing a
    document nobody is waiting for — and so it is never mistaken for a failure."""

    def __init__(self) -> None:
        super().__init__("cancelled by the caller")


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


class _CancelWatcher:
    """Runs `on_cancel` if `event` is set while the block is running.

    A plain `event.wait()` in a daemon thread would outlive short requests and
    pile up, so the watcher is always woken on exit.
    """

    def __init__(self, event: Optional[threading.Event], on_cancel: Any) -> None:
        self._event = event
        self._on_cancel = on_cancel
        self._done = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def __enter__(self) -> "_CancelWatcher":
        if self._event is None:
            return self
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()
        return self

    def _watch(self) -> None:
        while not self._done.wait(0.25):
            if self._event is not None and self._event.is_set():
                try:
                    self._on_cancel()
                except Exception:
                    pass    # the request is being abandoned either way
                return

    def __exit__(self, *_exc: Any) -> None:
        self._done.set()
        if self._thread is not None:
            self._thread.join(timeout=1)


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

    def _lighter_models(self, provider: str) -> list[str]:
        """Smaller models of the same family, largest first.

        The big models are the ones that run out of capacity under load, and
        the ones a cheaper plan leaves out. A smaller one is usually still
        answering, and for a short structured reply — a plan, a classification
        — it is a far better outcome than falling back to a rule. The model
        already in use is not offered back. MISTRAL_LIGHT_MODEL overrides the
        ladder with a comma-separated list; empty turns it off.
        """
        override = os.environ.get({MISTRAL: "MISTRAL_LIGHT_MODEL"}[provider])
        ladder = (tuple(m.strip() for m in override.split(",") if m.strip())
                  if override is not None else _LIGHT_MODELS.get(provider, ()))
        current = self._model(provider)
        return [m for m in ladder if m != current]

    def _in_cooldown(self, provider: str) -> tuple[bool, int]:
        exp = self._cooldowns.get(provider, 0)
        remaining = int(exp - time.time())
        return remaining > 0, max(remaining, 0)

    def _cool(self, provider: str, secs: float) -> None:
        self._cooldowns[provider] = time.time() + secs

    # ── per-provider callers ──────────────────────────────────────────────────
    def _call_mistral(self, messages: list[dict[str, str]], max_tokens: int,
                      cancel: Optional[threading.Event] = None,
                      timeout: Optional[float] = None,
                      model: Optional[str] = None) -> str:
        import httpx

        # The request is synchronous and most of its life is spent waiting for
        # the first byte, so there is no loop to check a flag in. Closing the
        # client from a watcher thread tears down the connection underneath it,
        # which is what actually stops the wait.
        client = httpx.Client(timeout=_timeout_for(max_tokens, timeout))
        watcher = _CancelWatcher(cancel, client.close)
        try:
            with watcher:
                resp = client.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._key(MISTRAL)}",
                        "Content-Type":  "application/json",
                        "Accept":        "application/json",
                    },
                    json={
                        "model":      model or self._model(MISTRAL),
                        "messages":   messages,
                        "max_tokens": max_tokens,
                    },
                )
        except httpx.TimeoutException as exc:
            if cancel is not None and cancel.is_set():
                raise GenerationCancelled() from exc
            raise ProviderTimeout(MISTRAL) from exc
        except Exception as exc:
            # A closed transport surfaces as a transport error, not a signal, so
            # the flag is what distinguishes "cancelled" from "genuinely broke".
            if cancel is not None and cancel.is_set():
                raise GenerationCancelled() from exc
            raise
        finally:
            client.close()

        if resp.status_code == 429:
            header = resp.headers.get("retry-after")
            try:
                after = float(header) if header else None
            except ValueError:
                after = None
            raise RateLimitExceeded(MISTRAL, after)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_mistral_with_retry(self, messages: list[dict[str, str]], max_tokens: int,
                                 cancel: Optional[threading.Event] = None,
                                 timeout: Optional[float] = None,
                                 wait_on_rate_limit: bool = False) -> str:
        """`_call_mistral`, but a struggling upstream is given another chance.

        Only the failures that another attempt could change are retried: a busy
        server, and — when the caller says it can wait — a rate limit. A bad key
        is answered once, because asking again with it is pointless.
        """
        last: Exception | None = None
        rate_limited = 0
        # A rate limit is waited out rather than counted against the busy-server
        # ladder, so a provider that is only throttling does not exhaust it.
        for attempt in range(_RETRY_ATTEMPTS + _RATE_LIMIT_ATTEMPTS):
            if attempt - rate_limited >= _RETRY_ATTEMPTS:
                break
            if cancel is not None and cancel.is_set():
                raise GenerationCancelled()
            try:
                return self._call_mistral(messages, max_tokens, cancel, timeout)
            except RateLimitExceeded as exc:
                # Whether to wait depends on what the caller would do instead.
                # A plan has a heuristic to fall back on and a person watching,
                # so it answers now; a rewrite pass has neither, and losing the
                # passage is worse for everyone than a few seconds' pause.
                if not wait_on_rate_limit or rate_limited + 1 >= _RATE_LIMIT_ATTEMPTS:
                    raise
                last = exc
                rate_limited += 1
                # Doubling, because a limit that is still refusing after two
                # seconds is measured over a longer window than two seconds.
                time.sleep(exc.retry_after or _RATE_LIMIT_PAUSE * (2 ** rate_limited))
                continue

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in _WRONG_MODEL_STATUSES:
                    last = exc
                    break          # not a wait; a different model is needed
                if status not in _RETRY_STATUSES:
                    raise
                last = exc
            except ProviderTimeout:
                # The deadline is the deadline; waiting again only spends more
                # of it. The heuristic is a better use of the remaining time.
                raise

            if attempt + 1 < _RETRY_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF * (attempt + 1))

        # The model would not answer. Work down the family rather than giving up
        # on the provider: a plan from a smaller model beats a plan from a rule.
        for lighter in self._lighter_models(MISTRAL):
            if cancel is not None and cancel.is_set():
                break
            try:
                return self._call_mistral(messages, max_tokens, cancel, timeout, lighter)
            except Exception:
                continue

        assert last is not None
        raise last

    # ── public interface ──────────────────────────────────────────────────────
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 1500,
        order: list[str] | None = None,
        cancel: Optional[threading.Event] = None,
        timeout: Optional[float] = None,
        wait_on_rate_limit: bool = False,
    ) -> tuple[str, str, float]:
        """
        Send `messages` to the configured provider.

        `cancel`, once set, abandons an in-flight request and raises
        GenerationCancelled — so a caller who has gone away stops costing tokens.

        Returns
        -------
        (text, provider_used, elapsed_seconds)

        Raises
        ------
        AllProvidersFailed — when every configured provider fails.
        GenerationCancelled — when `cancel` was set.
        """
        _callers = {MISTRAL: self._call_mistral_with_retry}
        errors: dict[str, str] = {}

        for provider in (order or DEFAULT_ORDER):
            if cancel is not None and cancel.is_set():
                raise GenerationCancelled()
            if not self._key(provider):
                continue

            in_cd, remaining = self._in_cooldown(provider)
            if in_cd:
                # A caller that can wait, waits. Skipping here is what turned
                # one rate-limited pass into four lost passages: the pass that
                # tripped the limit cooled the provider for a minute, and every
                # pass behind it was refused without being tried. A rewrite has
                # nothing to fall back on, so a minute is a price worth paying.
                if wait_on_rate_limit and remaining <= _MAX_COOLDOWN_WAIT:
                    if cancel is not None and cancel.is_set():
                        raise GenerationCancelled()
                    time.sleep(remaining)
                    self._cooldowns.pop(provider, None)
                else:
                    errors[provider] = f"cooldown {remaining}s"
                    continue

            try:
                t0 = time.time()
                text = _callers[provider](messages, max_tokens, cancel, timeout,
                                          wait_on_rate_limit)
                return text, provider, round(time.time() - t0, 3)

            except GenerationCancelled:
                raise    # the caller left; not a provider fault, so no cooldown

            except RateLimitExceeded:
                self._cool(provider, _COOLDOWN_RATE_LIMIT)
                errors[provider] = "rate_limited (60s cooldown)"

            except ProviderTimeout:
                self._cool(provider, _COOLDOWN_TIMEOUT)
                errors[provider] = (
                    f"timed out after {_timeout_for(max_tokens, timeout):.0f}s "
                    "(30s cooldown)"
                )

            except Exception as exc:
                self._cool(provider, _COOLDOWN_ERROR)
                errors[provider] = str(exc)[:120]

        # Everything is cooling and nothing was tried. A cooldown exists to stop
        # a failing provider being hammered, which is the right instinct when
        # there is another provider to ask — and the wrong one when the only
        # alternative is answering with a rule. The provider that recovers
        # soonest gets one attempt, no retries, before that happens.
        if errors and all(reason.startswith("cooldown") for reason in errors.values()):
            soonest = min(errors, key=lambda name: self._cooldowns.get(name, 0))
            if cancel is None or not cancel.is_set():
                try:
                    t0 = time.time()
                    text = self._call_mistral(messages, max_tokens, cancel, timeout)
                    self._cooldowns.pop(soonest, None)     # it answered; it is well
                    return text, soonest, round(time.time() - t0, 3)
                except GenerationCancelled:
                    raise
                except Exception as exc:
                    errors[soonest] = f"{errors[soonest]}, then {str(exc)[:60]}"

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
