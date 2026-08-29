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
    def __init__(self, status: int, text: str = "ok", headers: dict | None = None):
        self.status_code = status
        self._text = text
        self.headers = headers or {}

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._text}}]}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code}", request=httpx.Request("POST", "https://x"),
                response=httpx.Response(self.status_code))


def _router(monkeypatch, responses: list, *, key: str = "k") -> tuple[ProviderRouter, list[dict]]:
    """A router whose HTTP calls return `responses` in turn, recording each one.

    The models are pinned here rather than inherited: a developer whose own .env
    names the small model as primary would otherwise see these tests fail for a
    reason that has nothing to do with the code.
    """
    monkeypatch.setenv("MISTRAL_MODEL", "mistral-large-latest")
    monkeypatch.setenv("MISTRAL_LIGHT_MODEL", "mistral-small-latest")
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


def test_a_cooling_provider_is_still_tried_when_it_is_the_only_one(monkeypatch):
    """A cooldown means "ask someone else first". With no one else to ask, it
    should not mean "answer with a rule instead of trying"."""
    router, sent = _router(monkeypatch, [FakeResponse(200, "planned")])
    router._cool("mistral", 30)

    text, provider, _elapsed = router.chat([{"role": "user", "content": "hi"}])

    assert text == "planned"
    assert provider == "mistral"
    assert len(sent) == 1, "one attempt, not the whole retry ladder"
    assert "mistral" not in router._cooldowns, "it answered, so it is no longer cooling"


def test_a_cooling_provider_that_is_still_broken_reports_both(monkeypatch):
    router, _sent = _router(monkeypatch, [FakeResponse(503)])
    router._cool("mistral", 30)

    with pytest.raises(Exception) as caught:
        router.chat([{"role": "user", "content": "hi"}])
    assert "cooldown" in str(caught.value)


def test_a_model_the_account_cannot_use_is_swapped_not_retried(monkeypatch):
    """403 "not available in your subscription tier" is permanent for that
    model and irrelevant to the next one. Retrying it wastes the request; the
    lighter model is usually the one a tier includes."""
    router, sent = _router(monkeypatch, [FakeResponse(403), FakeResponse(200, "planned")])

    text, _provider, _elapsed = router.chat([{"role": "user", "content": "hi"}])

    assert text == "planned"
    assert len(sent) == 2, "asked once, then asked a different model"
    assert sent[0]["model"] == "mistral-large-latest"
    assert sent[1]["model"] == "mistral-small-latest"


def test_the_ladder_walks_down_the_family(monkeypatch):
    """A tier that excludes the large model usually includes the medium one, so
    the next thing asked should be the next thing down — not the smallest."""
    router, sent = _router(monkeypatch, [FakeResponse(403), FakeResponse(200, "planned")])
    monkeypatch.setenv("MISTRAL_LIGHT_MODEL", "mistral-medium-latest,mistral-small-latest")

    text, _provider, _elapsed = router.chat([{"role": "user", "content": "hi"}])

    assert text == "planned"
    assert [s["model"] for s in sent] == ["mistral-large-latest", "mistral-medium-latest"]


def test_the_ladder_keeps_going_if_the_next_one_also_refuses(monkeypatch):
    router, sent = _router(monkeypatch, [FakeResponse(403), FakeResponse(403), FakeResponse(200, "planned")])
    monkeypatch.setenv("MISTRAL_LIGHT_MODEL", "mistral-medium-latest,mistral-small-latest")

    router.chat([{"role": "user", "content": "hi"}])

    assert [s["model"] for s in sent] == [
        "mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"]


def test_the_model_in_use_is_not_offered_back_to_itself(monkeypatch):
    monkeypatch.setenv("MISTRAL_MODEL", "mistral-medium-latest")
    monkeypatch.setenv("MISTRAL_LIGHT_MODEL", "mistral-medium-latest,mistral-small-latest")
    assert ProviderRouter()._lighter_models("mistral") == ["mistral-small-latest"]


def test_a_rate_limit_is_waited_out_when_the_caller_can_afford_to(monkeypatch):
    """A long rewrite fires a pass as fast as the last one finished, and a free
    tier meters by the second. Losing the passage is worse than pausing."""
    router, sent = _router(monkeypatch, [FakeResponse(429), FakeResponse(200, "rewritten")])

    text, _provider, _elapsed = router.chat(
        [{"role": "user", "content": "hi"}], wait_on_rate_limit=True)

    assert text == "rewritten"
    assert len(sent) == 2


def test_a_rate_limit_still_answers_at_once_for_a_caller_that_cannot_wait(monkeypatch):
    """Planning has a heuristic and a person watching it; it does not queue."""
    router, sent = _router(monkeypatch, [FakeResponse(429), FakeResponse(200, "planned")])

    with pytest.raises(Exception):
        router.chat([{"role": "user", "content": "hi"}])
    assert len(sent) == 1


def test_the_server_is_believed_about_how_long_to_wait(monkeypatch):
    waited: list[float] = []
    monkeypatch.setattr("app.services.router.time.sleep", waited.append)

    router, _sent = _router(
        monkeypatch,
        [FakeResponse(429, headers={"retry-after": "7"}), FakeResponse(200, "ok")])
    monkeypatch.setattr("app.services.router.time.sleep", waited.append)

    router.chat([{"role": "user", "content": "hi"}], wait_on_rate_limit=True)
    assert 7 in waited, "it waited what the server asked for, not a guess"
