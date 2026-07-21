"""Table model presenting unique payloads in a QTableView."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPersistentModelIndex, Qt

from kuka_value.models.payload import Payload

_HEADERS = [
    "Index(es)",
    "Mass (kg)",
    "CoG X (mm)",
    "CoG Y (mm)",
    "CoG Z (mm)",
    "Orientation A (deg)",
    "Orientation B (deg)",
    "Orientation C (deg)",
    "Inertia X (kgm2)",
    "Inertia Y (kgm2)",
    "Inertia Z (kgm2)",
    "Source File",
]


class PayloadTableModel(QAbstractTableModel):
    """Read-only table model over a list of deduplicated payloads.

    Column layout matches the exporters (CsvExporter/ExcelExporter) so
    what the user sees on screen matches what gets exported.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._payloads: list[Payload] = []

    def set_payloads(self, payloads: list[Payload]) -> None:
        """Replace the displayed payloads and refresh the view."""
        self.beginResetModel()
        self._payloads = payloads
        self.endResetModel()

    def payload_at(self, row: int) -> Payload:
        """Return the domain object backing a given row."""
        return self._payloads[row]

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),  # noqa: B008
    ) -> int:
        if parent.isValid():
            return 0
        return len(self._payloads)

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
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        return self._column_value(self._payloads[index.row()], index.column())

    @staticmethod
    def _column_value(payload: Payload, column: int) -> Any:
        inertia = payload.inertia
        orientation = payload.orientation
        columns: dict[int, Any] = {
            0: ", ".join(str(i) for i in payload.indices),
            1: payload.mass,
            2: payload.center_of_gravity.x,
            3: payload.center_of_gravity.y,
            4: payload.center_of_gravity.z,
            5: orientation.a if orientation else "",
            6: orientation.b if orientation else "",
            7: orientation.c if orientation else "",
            8: inertia.x if inertia else "",
            9: inertia.y if inertia else "",
            10: inertia.z if inertia else "",
            11: payload.source_file or "",
        }
        return columns.get(column)
