from datetime import datetime

from src.screening.calls.domain.events import CallFinished
from src.screening.calls.infrastructure.subscribers import call_finished
from src.screening.shared.domain import ApplicationId, CallId


def _event() -> CallFinished:
    return CallFinished(
        application_id=ApplicationId("00000000-0000-0000-0000-000000000042"),
        call_id=CallId("00000000-0000-0000-0000-000000000099"),
        occurred_at=datetime.utcnow(),
    )


def test_on_call_finished_schedules_task_when_loop_is_running(monkeypatch):
    class FakeLoop:
        def __init__(self) -> None:
            self.created = False

        def create_task(self, coro):
            self.created = True
            coro.close()

    loop = FakeLoop()

    monkeypatch.setattr(call_finished.asyncio, "get_running_loop", lambda: loop)

    call_finished.on_call_finished(_event())

    assert loop.created is True


def test_on_call_finished_runs_coroutine_when_no_running_loop(monkeypatch):
    run_called = False

    def fake_run(coro):
        nonlocal run_called
        run_called = True
        coro.close()

    def raise_no_loop():
        raise RuntimeError("no running event loop")

    monkeypatch.setattr(call_finished.asyncio, "get_running_loop", raise_no_loop)
    monkeypatch.setattr(call_finished.asyncio, "run", fake_run)

    call_finished.on_call_finished(_event())

    assert run_called is True
