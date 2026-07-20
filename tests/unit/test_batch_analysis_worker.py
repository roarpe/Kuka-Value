"""Unit tests for BatchAnalysisWorker.

Engine.parse_many() is already covered by tests/integration/test_engine.py,
so it's mocked here to keep these tests focused on the worker's own
responsibility: streaming results and progress via Qt signals.
"""

from pathlib import Path
from unittest.mock import Mock

from kuka_value.models.batch_result import BatchItemResult
from kuka_value.ui.batch_analysis_worker import BatchAnalysisWorker


def _result(name: str, succeeded: bool = True) -> BatchItemResult:
    robot = Mock(spec=object) if succeeded else None
    return BatchItemResult(
        source_path=Path(name),
        robot=robot,
        error=None if succeeded else "boom",
    )


class TestBatchAnalysisWorkerStreaming:
    def test_emits_item_ready_per_result(self, qapp: object) -> None:
        results = [_result("a"), _result("b"), _result("c")]
        engine = Mock()
        engine.parse_many.return_value = iter(results)

        worker = BatchAnalysisWorker(engine, [Path("a"), Path("b"), Path("c")])

        received = []
        worker.item_ready.connect(received.append)
        worker.run()

        assert received == results

    def test_emits_progress_with_running_count_and_total(self, qapp: object) -> None:
        results = [_result("a"), _result("b")]
        engine = Mock()
        engine.parse_many.return_value = iter(results)

        worker = BatchAnalysisWorker(engine, [Path("a"), Path("b")])

        progress_calls = []
        worker.progress.connect(lambda completed, total: progress_calls.append((completed, total)))
        worker.run()

        assert progress_calls == [(1, 2), (2, 2)]

    def test_emits_all_finished_after_streaming(self, qapp: object) -> None:
        engine = Mock()
        engine.parse_many.return_value = iter([_result("a")])

        worker = BatchAnalysisWorker(engine, [Path("a")])

        events = []
        worker.item_ready.connect(lambda _r: events.append("item"))
        worker.all_finished.connect(lambda: events.append("finished"))
        worker.run()

        assert events == ["item", "finished"]

    def test_empty_paths_emits_only_all_finished(self, qapp: object) -> None:
        engine = Mock()
        engine.parse_many.return_value = iter([])

        worker = BatchAnalysisWorker(engine, [])

        events = []
        worker.item_ready.connect(lambda _r: events.append("item"))
        worker.all_finished.connect(lambda: events.append("finished"))
        worker.run()

        assert events == ["finished"]

    def test_calls_parse_many_with_given_paths(self, qapp: object) -> None:
        paths = [Path("a"), Path("b")]
        engine = Mock()
        engine.parse_many.return_value = iter([])

        worker = BatchAnalysisWorker(engine, paths)
        worker.run()

        engine.parse_many.assert_called_once_with(paths)


class TestBatchAnalysisWorkerFatalError:
    def test_unexpected_exception_emits_fatal_error(self, qapp: object) -> None:
        engine = Mock()

        def boom() -> None:
            raise RuntimeError("unexpected failure")
            yield  # pragma: no cover - makes this a generator function

        engine.parse_many.return_value = boom()

        worker = BatchAnalysisWorker(engine, [Path("a")])

        fatal_messages = []
        worker.fatal_error.connect(fatal_messages.append)
        worker.run()

        assert len(fatal_messages) == 1
        assert "unexpected failure" in fatal_messages[0]

    def test_all_finished_still_emitted_after_fatal_error(self, qapp: object) -> None:
        engine = Mock()

        def boom() -> None:
            raise RuntimeError("boom")
            yield  # pragma: no cover

        engine.parse_many.return_value = boom()

        worker = BatchAnalysisWorker(engine, [Path("a")])

        finished_calls = []
        worker.all_finished.connect(lambda: finished_calls.append(True))
        worker.run()

        assert finished_calls == [True]

    def test_fatal_error_does_not_raise(self, qapp: object) -> None:
        engine = Mock()

        def boom() -> None:
            raise RuntimeError("boom")
            yield  # pragma: no cover

        engine.parse_many.return_value = boom()

        worker = BatchAnalysisWorker(engine, [Path("a")])
        worker.run()  # must not raise
