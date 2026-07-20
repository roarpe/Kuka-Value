"""Unit tests for PayloadTableModel."""

from PySide6.QtCore import QModelIndex, Qt

from kuka_value.models.payload import Payload, Vector3D
from kuka_value.ui.payload_table_model import PayloadTableModel


def _payloads() -> list[Payload]:
    return [
        Payload(
            mass=10.5,
            center_of_gravity=Vector3D(x=100.0, y=0.0, z=50.0),
            inertia=Vector3D(x=0.5, y=0.5, z=0.3),
            indices=[1, 3],
            source_file="$config.dat",
        ),
        Payload(
            mass=25.0,
            center_of_gravity=Vector3D(x=0.0, y=0.0, z=0.0),
            inertia=None,
            indices=[2],
            source_file=None,
        ),
    ]


class TestRowsAndColumns:
    def test_empty_model_has_no_rows(self, qapp: object) -> None:
        model = PayloadTableModel()
        assert model.rowCount() == 0

    def test_row_count_matches_payload_count(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        assert model.rowCount() == 2

    def test_column_count(self, qapp: object) -> None:
        model = PayloadTableModel()
        assert model.columnCount() == 9

    def test_row_count_with_invalid_parent_index_is_zero(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        parent = model.index(0, 0)
        assert model.rowCount(parent) == 0


class TestHeaderData:
    def test_horizontal_header_labels(self, qapp: object) -> None:
        model = PayloadTableModel()
        assert model.headerData(0, Qt.Orientation.Horizontal) == "Index(es)"
        assert model.headerData(1, Qt.Orientation.Horizontal) == "Mass (kg)"

    def test_vertical_header_is_one_based_row_number(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        assert model.headerData(0, Qt.Orientation.Vertical) == 1
        assert model.headerData(1, Qt.Orientation.Vertical) == 2

    def test_header_data_ignores_other_roles(self, qapp: object) -> None:
        model = PayloadTableModel()
        result = model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole)
        assert result is None


class TestCellData:
    def test_data_returns_none_for_invalid_index(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        assert model.data(QModelIndex()) is None

    def test_data_returns_none_for_non_display_role(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        index = model.index(0, 0)
        assert model.data(index, Qt.ItemDataRole.ToolTipRole) is None

    def test_data_indices_are_joined(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        index = model.index(0, 0)
        assert model.data(index) == "1, 3"

    def test_data_mass_column(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        assert model.data(model.index(0, 1)) == 10.5

    def test_data_center_of_gravity_columns(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        assert model.data(model.index(0, 2)) == 100.0
        assert model.data(model.index(0, 3)) == 0.0
        assert model.data(model.index(0, 4)) == 50.0

    def test_data_inertia_columns(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        assert model.data(model.index(0, 5)) == 0.5
        assert model.data(model.index(0, 6)) == 0.5
        assert model.data(model.index(0, 7)) == 0.3

    def test_data_missing_inertia_is_blank(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        assert model.data(model.index(1, 5)) == ""
        assert model.data(model.index(1, 6)) == ""
        assert model.data(model.index(1, 7)) == ""

    def test_data_source_file_column(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        assert model.data(model.index(0, 8)) == "$config.dat"

    def test_data_missing_source_file_is_blank(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        assert model.data(model.index(1, 8)) == ""


class TestPayloadAt:
    def test_payload_at_returns_backing_object(self, qapp: object) -> None:
        model = PayloadTableModel()
        payloads = _payloads()
        model.set_payloads(payloads)
        assert model.payload_at(0) is payloads[0]
        assert model.payload_at(1) is payloads[1]


class TestSetPayloads:
    def test_set_payloads_replaces_content(self, qapp: object) -> None:
        model = PayloadTableModel()
        model.set_payloads(_payloads())
        assert model.rowCount() == 2

        model.set_payloads([])
        assert model.rowCount() == 0
