"""Background worker: runs Engine.parse() off the UI thread."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from kuka_value.engine.engine import Engine
from kuka_value.models.robot_info import RobotInfo


class AnalysisWorker(QObject):
    """Runs a single backup analysis and reports the result via signals.

    Meant to be moved to a QThread by the caller: `run()` blocks on
    Engine.parse(), so it must never execute on the UI thread.
    """

    finished = Signal(object)  # emits RobotInfo
    failed = Signal(str)

    def __init__(self, engine: Engine, path: Path) -> None:
        super().__init__()
        self._engine = engine
        self._path = path

    def run(self) -> None:
        """Execute the analysis, emitting `finished` or `failed`.

        Never lets an exception propagate out of the worker thread:
        analysis errors (missing path, corrupt ZIP) are translated
        into the `failed` signal instead.
        """
        try:
            robot: RobotInfo = self._engine.parse(self._path)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(robot)
