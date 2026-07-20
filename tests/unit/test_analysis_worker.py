"""Unit tests for AnalysisWorker.

The worker's only responsibility is: call Engine.parse() and translate
the outcome into a Qt signal. Engine itself is already covered by
tests/integration/test_engine.py, so it's mocked here to keep these
tests focused and fast.
"""

from pathlib import Path
from unittest.mock import Mock

from kuka_value.models.robot_info import RobotInfo
from kuka_value.ui.analysis_worker import AnalysisWorker


class TestAnalysisWorkerSuccess:
    def test_run_emits_finished_with_robot_info(self, qapp: object) -> None:
        fake_robot = Mock(spec=RobotInfo)
        engine = Mock()
        engine.parse.return_value = fake_robot

        worker = AnalysisWorker(engine, Path("/fake/backup"))

        received = []
        worker.finished.connect(received.append)
        worker.run()

        assert received == [fake_robot]
        engine.parse.assert_called_once_with(Path("/fake/backup"))

    def test_run_does_not_emit_failed_on_success(self, qapp: object) -> None:
        engine = Mock()
        engine.parse.return_value = Mock(spec=RobotInfo)

        worker = AnalysisWorker(engine, Path("/fake/backup"))

        failed_calls = []
        worker.failed.connect(failed_calls.append)
        worker.run()

        assert failed_calls == []


class TestAnalysisWorkerFailure:
    def test_run_emits_failed_on_file_not_found(self, qapp: object) -> None:
        engine = Mock()
        engine.parse.side_effect = FileNotFoundError("backup not found")

        worker = AnalysisWorker(engine, Path("/missing"))

        failed_messages = []
        worker.failed.connect(failed_messages.append)
        worker.run()

        assert len(failed_messages) == 1
        assert "backup not found" in failed_messages[0]

    def test_run_emits_failed_on_invalid_zip(self, qapp: object) -> None:
        engine = Mock()
        engine.parse.side_effect = ValueError("Invalid ZIP file")

        worker = AnalysisWorker(engine, Path("/bad.zip"))

        failed_messages = []
        worker.failed.connect(failed_messages.append)
        worker.run()

        assert len(failed_messages) == 1
        assert "Invalid ZIP" in failed_messages[0]

    def test_run_does_not_emit_finished_on_failure(self, qapp: object) -> None:
        engine = Mock()
        engine.parse.side_effect = RuntimeError("boom")

        worker = AnalysisWorker(engine, Path("/fake"))

        finished_calls = []
        worker.finished.connect(finished_calls.append)
        worker.run()

        assert finished_calls == []

    def test_run_never_raises(self, qapp: object) -> None:
        engine = Mock()
        engine.parse.side_effect = RuntimeError("unexpected failure")

        worker = AnalysisWorker(engine, Path("/fake"))

        worker.run()  # must not raise
