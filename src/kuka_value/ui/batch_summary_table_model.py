"""Table model presenting a batch's per-backup summary."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPersistentModelIndex, Qt
from PySide6.QtGui import QColor

from kuka_value.models.batch_result import BatchItemResult

_HEADERS = ["Backup Name", "Model", "Payloads", "Warnings", "Status"]
_STATUS_COLUMN = 4


class BatchSummaryTableModel(QAbstractTableModel):
    """Read-only table model over a list of BatchItemResult.

    Supports incremental append (add_result) so the table can fill in
    as a batch streams results, rather than waiting for all of them.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._results: list[BatchItemResult] = []

    def set_results(self, results: list[BatchItemResult]) -> None:
        self.beginResetModel()
        self._results = results
        self.endResetModel()

    def add_result(self, result: BatchItemResult) -> None:
        row = len(self._results)
        self.beginInsertRows(QModelIndex(), row, row)
        self._results.append(result)
        self.endInsertRows()

    def result_at(self, row: int) -> BatchItemResult:
        return self._results[row]

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),  # noqa: B008
    ) -> int:
        if parent.isValid():
            return 0
        return len(self._results)

    def columnCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),  # noqa: B008
    ) -> int:
        if parent.isValid():
            return 0
        return len(_HEADERS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return _HEADERS[section]
        return section + 1

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None
        result = self._results[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return self._column_value(result, index.column())
        if role == Qt.ItemDataRole.ForegroundRole and index.column() == _STATUS_COLUMN:
            return QColor("red") if result.robot is None else QColor("darkGreen")
        return None

    @staticmethod
    def _column_value(result: BatchItemResult, column: int) -> Any:
        if result.robot is None:
            columns: dict[int, Any] = {
                0: result.display_name,
                1: "-",
                2: 0,
                3: 0,
                4: f"FAILED: {result.error}",
            }
        else:
            columns = {
                0: result.display_name,
                1: result.robot.model,
                2: len(result.robot.payloads),
                3: len(result.robot.warnings),
                4: "OK",
            }
        return columns.get(column)
