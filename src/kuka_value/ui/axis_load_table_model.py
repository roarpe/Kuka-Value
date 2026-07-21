"""Table model presenting supplementary axis loads in a QTableView."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPersistentModelIndex, Qt

from kuka_value.models.axis_load import AxisLoad

_HEADERS = [
    "Axis",
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


class AxisLoadTableModel(QAbstractTableModel):
    """Read-only table model over a list of supplementary axis loads.

    Column layout matches the exporters (CsvExporter/ExcelExporter) so
    what the user sees on screen matches what gets exported.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._axis_loads: list[AxisLoad] = []

    def set_axis_loads(self, axis_loads: list[AxisLoad]) -> None:
        """Replace the displayed axis loads and refresh the view."""
        self.beginResetModel()
        self._axis_loads = axis_loads
        self.endResetModel()

    def axis_load_at(self, row: int) -> AxisLoad:
        """Return the domain object backing a given row."""
        return self._axis_loads[row]

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),  # noqa: B008
    ) -> int:
        if parent.isValid():
            return 0
        return len(self._axis_loads)

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
        return self._column_value(self._axis_loads[index.row()], index.column())

    @staticmethod
    def _column_value(axis_load: AxisLoad, column: int) -> Any:
        inertia = axis_load.inertia
        orientation = axis_load.orientation
        columns: dict[int, Any] = {
            0: axis_load.axis,
            1: axis_load.mass,
            2: axis_load.center_of_gravity.x,
            3: axis_load.center_of_gravity.y,
            4: axis_load.center_of_gravity.z,
            5: orientation.a if orientation else "",
            6: orientation.b if orientation else "",
            7: orientation.c if orientation else "",
            8: inertia.x if inertia else "",
            9: inertia.y if inertia else "",
            10: inertia.z if inertia else "",
            11: axis_load.source_file or "",
        }
        return columns.get(column)
