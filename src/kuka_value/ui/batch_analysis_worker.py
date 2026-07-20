"""Background worker: runs Engine.parse_many() off the UI thread."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from kuka_value.engine.engine import Engine


class BatchAnalysisWorker(QObject):
    """Runs a batch analysis and reports results incrementally.

    Meant to be moved to a QThread by the caller: `run()` blocks on
    Engine.parse_many(), so it must never execute on the UI thread.
    Engine.parse_many() already isolates per-backup failures into
    BatchItemResult, so this worker only needs a defensive catch for
    something truly unexpected - to guarantee `all_finished` always
    fires and the UI never hangs waiting for it.
    """

    item_ready = Signal(object)  # emits BatchItemResult per backup
    progress = Signal(int, int)  # (completed, total)
    all_finished = Signal()
    fatal_error = Signal(str)

    def __init__(self, engine: Engine, paths: list[Path]) -> None:
        super().__init__()
        self._engine = engine
        self._paths = paths

    def run(self) -> None:
        total = len(self._paths)
        try:
            for completed, result in enumerate(self._engine.parse_many(self._paths), start=1):
                self.item_ready.emit(result)
                self.progress.emit(completed, total)
        except Exception as exc:
            self.fatal_error.emit(str(exc))
        finally:
            self.all_finished.emit()
