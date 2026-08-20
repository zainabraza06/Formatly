"""Abandoning a run has to stop the work, not just stop waiting for it.

Generation costs money for as long as it runs, so a browser that pressed Stop
must not leave the server talking to the model for another two minutes.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import anyio
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.paper.api import _run_cancellable  # noqa: E402
from app.services.router import (  # noqa: E402
    MISTRAL, GenerationCancelled, ProviderRouter, RateLimitExceeded, _CancelWatcher,
)


# ── the watcher ─────────────────────────────────────────────────────────────

def test_watcher_fires_when_the_event_is_set():
    fired = threading.Event()
    event = threading.Event()
    with _CancelWatcher(event, fired.set):
        event.set()
        assert fired.wait(2), "the watcher should have torn the request down"


def test_watcher_stays_quiet_when_nothing_is_cancelled():
    fired = threading.Event()
    with _CancelWatcher(threading.Event(), fired.set):
        time.sleep(0.6)
    assert not fired.is_set()


def test_watcher_without_an_event_starts_no_thread():
    before = threading.active_count()
    with _CancelWatcher(None, lambda: None):
        assert threading.active_count() == before


def test_watcher_thread_does_not_outlive_the_block():
    before = threading.active_count()
    with _CancelWatcher(threading.Event(), lambda: None):
        pass
    time.sleep(0.1)
    assert threading.active_count() <= before, "watcher threads must not pile up"


# ── the router ──────────────────────────────────────────────────────────────

def test_chat_refuses_to_start_when_already_cancelled(monkeypatch):
    router = ProviderRouter()
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-real-looking-key")
    called = False

    def _never(*_a, **_k):
        nonlocal called
        called = True
        return ""

    monkeypatch.setattr(router, "_call_mistral", _never)
    cancel = threading.Event()
    cancel.set()

    with pytest.raises(GenerationCancelled):
        router.chat([{"role": "user", "content": "x"}], cancel=cancel)
    assert not called, "a cancelled run should not spend a request"


def test_cancelling_does_not_cool_the_provider(monkeypatch):
    """A caller leaving is not the provider's fault; the next run must not wait."""
    router = ProviderRouter()
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-real-looking-key")
    monkeypatch.setattr(router, "_call_mistral",
                        lambda *_a, **_k: (_ for _ in ()).throw(GenerationCancelled()))

    with pytest.raises(GenerationCancelled):
        router.chat([{"role": "user", "content": "x"}], cancel=threading.Event())
    assert not router._in_cooldown(MISTRAL)[0]


def test_a_real_failure_still_cools_the_provider(monkeypatch):
    router = ProviderRouter()
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-real-looking-key")
    monkeypatch.setattr(router, "_call_mistral",
                        lambda *_a, **_k: (_ for _ in ()).throw(RateLimitExceeded(MISTRAL)))

    with pytest.raises(Exception):
        router.chat([{"role": "user", "content": "x"}])
    assert router._in_cooldown(MISTRAL)[0]


# ── the endpoint helper ─────────────────────────────────────────────────────

class FakeRequest:
    """Reports the client as gone after `after` calls to is_disconnected()."""

    def __init__(self, after: int | None = None):
        self.after = after
        self.calls = 0

    async def is_disconnected(self) -> bool:
        self.calls += 1
        return self.after is not None and self.calls >= self.after


def test_returns_the_result_when_the_client_stays():
    async def go():
        return await _run_cancellable(FakeRequest(), lambda cancel: "written")
    assert anyio.run(go) == "written"


def test_propagates_a_real_failure_unwrapped():
    """anyio wraps anything escaping a task group; the endpoint needs the original."""
    def boom(_cancel):
        raise ValueError("provider exploded")

    async def go():
        return await _run_cancellable(FakeRequest(), boom)

    with pytest.raises(ValueError, match="provider exploded"):
        anyio.run(go)


def test_the_worker_is_told_when_the_client_disconnects():
    seen = threading.Event()

    def work(cancel: threading.Event):
        if cancel.wait(10):
            seen.set()
            raise GenerationCancelled()
        return "finished anyway"

    async def go():
        return await _run_cancellable(FakeRequest(after=1), work)

    with pytest.raises(GenerationCancelled):
        anyio.run(go)
    assert seen.is_set(), "the cancel event should have reached the worker"


def test_the_watcher_stops_once_the_work_is_done():
    req = FakeRequest()

    async def go():
        return await _run_cancellable(req, lambda cancel: "done")

    assert anyio.run(go) == "done"
    before = req.calls
    time.sleep(0.8)
    assert req.calls == before, "the watcher should not keep polling after the work ends"
