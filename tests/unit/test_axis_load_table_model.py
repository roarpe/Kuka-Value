"""Unit tests for AxisLoadTableModel."""

from PySide6.QtCore import QModelIndex, Qt

from kuka_value.models.axis_load import AxisLoad
from kuka_value.models.payload import Orientation, Vector3D
from kuka_value.ui.axis_load_table_model import AxisLoadTableModel


def _axis_loads() -> list[AxisLoad]:
    return [
        AxisLoad(
            axis=3,
            mass=12.5,
            center_of_gravity=Vector3D(x=50.0, y=0.0, z=0.0),
            inertia=Vector3D(x=0.1, y=0.2, z=0.3),
            orientation=Orientation(a=10.0, b=20.0, c=30.0),
            source_file="$config.dat",
        ),
        AxisLoad(
            axis=1,
            mass=8.0,
            center_of_gravity=Vector3D(x=0.0, y=0.0, z=0.0),
            inertia=None,
            orientation=None,
            source_file=None,
        ),
    ]


class TestRowsAndColumns:
    def test_empty_model_has_no_rows(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        assert model.rowCount() == 0

    def test_row_count_matches_axis_load_count(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.rowCount() == 2

    def test_column_count(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        assert model.columnCount() == 12

    def test_row_count_with_invalid_parent_index_is_zero(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        parent = model.index(0, 0)
        assert model.rowCount(parent) == 0

    def test_column_count_with_invalid_parent_index_is_zero(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        parent = model.index(0, 0)
        assert model.columnCount(parent) == 0


class TestHeaderData:
    def test_horizontal_header_labels(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        assert model.headerData(0, Qt.Orientation.Horizontal) == "Axis"
        assert model.headerData(1, Qt.Orientation.Horizontal) == "Mass (kg)"

    def test_vertical_header_is_one_based_row_number(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.headerData(0, Qt.Orientation.Vertical) == 1
        assert model.headerData(1, Qt.Orientation.Vertical) == 2

    def test_header_data_ignores_other_roles(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        result = model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole)
        assert result is None


class TestCellData:
    def test_data_returns_none_for_invalid_index(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.data(QModelIndex()) is None

    def test_data_returns_none_for_non_display_role(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        index = model.index(0, 0)
        assert model.data(index, Qt.ItemDataRole.ToolTipRole) is None

    def test_data_axis_column(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.data(model.index(0, 0)) == 3
        assert model.data(model.index(1, 0)) == 1

    def test_data_mass_column(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.data(model.index(0, 1)) == 12.5

    def test_data_center_of_gravity_columns(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.data(model.index(0, 2)) == 50.0
        assert model.data(model.index(0, 3)) == 0.0
        assert model.data(model.index(0, 4)) == 0.0

    def test_data_orientation_columns(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.data(model.index(0, 5)) == 10.0
        assert model.data(model.index(0, 6)) == 20.0
        assert model.data(model.index(0, 7)) == 30.0

    def test_data_missing_orientation_is_blank(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.data(model.index(1, 5)) == ""
        assert model.data(model.index(1, 6)) == ""
        assert model.data(model.index(1, 7)) == ""

    def test_data_inertia_columns(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.data(model.index(0, 8)) == 0.1
        assert model.data(model.index(0, 9)) == 0.2
        assert model.data(model.index(0, 10)) == 0.3

    def test_data_missing_inertia_is_blank(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.data(model.index(1, 8)) == ""
        assert model.data(model.index(1, 9)) == ""
        assert model.data(model.index(1, 10)) == ""

    def test_data_source_file_column(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.data(model.index(0, 11)) == "$config.dat"

    def test_data_missing_source_file_is_blank(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.data(model.index(1, 11)) == ""


class TestAxisLoadAt:
    def test_axis_load_at_returns_backing_object(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        axis_loads = _axis_loads()
        model.set_axis_loads(axis_loads)
        assert model.axis_load_at(0) is axis_loads[0]
        assert model.axis_load_at(1) is axis_loads[1]


class TestSetAxisLoads:
    def test_set_axis_loads_replaces_content(self, qapp: object) -> None:
        model = AxisLoadTableModel()
        model.set_axis_loads(_axis_loads())
        assert model.rowCount() == 2

        model.set_axis_loads([])
        assert model.rowCount() == 0
