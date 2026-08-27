"""How the router behaves when a provider is having a bad day.

Written after an afternoon where every command in the app was planned by the
heuristic. The cause was upstream — "Service temporarily unavailable due to
high load, please retry" — but the handling made it worse than it had to be: a
single blip was spent as the whole attempt, and then cooled the provider off so
the *next* command fell back too.
"""
from __future__ import annotations

import httpx
import pytest

from app.services.router import ProviderRouter, ProviderTimeout, RateLimitExceeded


class FakeResponse:
    def __init__(self, status: int, text: str = "ok"):
        self.status_code = status
        self._text = text

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._text}}]}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code}", request=httpx.Request("POST", "https://x"),
                response=httpx.Response(self.status_code))


def _router(monkeypatch, responses: list, *, key: str = "k") -> tuple[ProviderRouter, list[dict]]:
    """A router whose HTTP calls return `responses` in turn, recording each one."""
    router = ProviderRouter()
    monkeypatch.setattr(router, "_key", lambda _p: key)
    monkeypatch.setattr("app.services.router.time.sleep", lambda _s: None)

    sent: list[dict] = []
    queue = list(responses)

    class FakeClient:
        def __init__(self, *_a, **_kw):
            pass

        def post(self, _url, headers=None, json=None):
            sent.append(json or {})
            nxt = queue.pop(0)
            if isinstance(nxt, Exception):
                raise nxt
            return nxt

        def close(self):
            pass

    monkeypatch.setattr("app.services.router.httpx.Client", FakeClient)
    return router, sent


def test_a_busy_provider_is_asked_again(monkeypatch):
    """503 means "please retry", and a second later it usually works."""
    router, sent = _router(monkeypatch, [FakeResponse(503), FakeResponse(200, "planned")])

    text, provider, _elapsed = router.chat([{"role": "user", "content": "hi"}])

    assert text == "planned"
    assert provider == "mistral"
    assert len(sent) == 2, "the first answer was not the last word"


def test_a_provider_that_stays_busy_tries_a_smaller_model(monkeypatch):
    """The large models are the ones that run out of capacity. A plan answered
    by a smaller one beats a plan answered by a rule."""
    router, sent = _router(monkeypatch, [FakeResponse(503)] * 3 + [FakeResponse(200, "planned")])

    text, _provider, _elapsed = router.chat([{"role": "user", "content": "hi"}])

    assert text == "planned"
    assert sent[0]["model"] == "mistral-large-latest"
    assert sent[-1]["model"] == "mistral-small-latest", "it asked the lighter model"


def test_a_bad_key_is_not_retried(monkeypatch):
    """Only the failures that mean "try again" are tried again."""
    router, sent = _router(monkeypatch, [FakeResponse(401)])

    with pytest.raises(Exception):
        router.chat([{"role": "user", "content": "hi"}])
    assert len(sent) == 1, "asking again with the same bad key is pointless"


def test_a_rate_limit_is_not_retried(monkeypatch):
    router, sent = _router(monkeypatch, [FakeResponse(429)])

    with pytest.raises(Exception):
        router.chat([{"role": "user", "content": "hi"}])
    assert len(sent) == 1


def test_a_timeout_is_not_retried(monkeypatch):
    """The deadline is the deadline: waiting again only spends more of it, and
    the caller has a heuristic that answers instantly."""
    router, sent = _router(monkeypatch, [httpx.ReadTimeout("too slow")])

    with pytest.raises(Exception):
        router.chat([{"role": "user", "content": "hi"}])
    assert len(sent) == 1


def test_a_caller_may_ask_for_a_shorter_deadline():
    """A plan is a few hundred bytes; it should not be allowed a minute."""
    from app.services.router import _timeout_for

    assert _timeout_for(900) == pytest.approx(52.5), "derived from the token budget"
    assert _timeout_for(900, 20) == 20, "a caller may ask for less"
    assert _timeout_for(200, 120) == pytest.approx(35.0), "but asking for more does not grant it"
