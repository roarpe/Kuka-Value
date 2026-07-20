"""Unit tests for BatchSummaryTableModel."""

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QColor

from kuka_value.models.batch_result import BatchItemResult
from kuka_value.ui.batch_summary_table_model import BatchSummaryTableModel


class TestRowsAndColumns:
    def test_empty_model_has_no_rows(self, qapp: object) -> None:
        model = BatchSummaryTableModel()
        assert model.rowCount() == 0

    def test_row_count_matches_results(
        self, qapp: object, sample_batch_results: list[BatchItemResult]
    ) -> None:
        model = BatchSummaryTableModel()
        model.set_results(sample_batch_results)
        assert model.rowCount() == 3

    def test_column_count(self, qapp: object) -> None:
        model = BatchSummaryTableModel()
        assert model.columnCount() == 5

    def test_row_count_with_invalid_parent_index_is_zero(
        self, qapp: object, sample_batch_results: list[BatchItemResult]
    ) -> None:
        model = BatchSummaryTableModel()
        model.set_results(sample_batch_results)
        parent = model.index(0, 0)
        assert model.rowCount(parent) == 0

    def test_column_count_with_invalid_parent_index_is_zero(
        self, qapp: object, sample_batch_results: list[BatchItemResult]
    ) -> None:
        model = BatchSummaryTableModel()
        model.set_results(sample_batch_results)
        parent = model.index(0, 0)
        assert model.columnCount(parent) == 0


class TestHeaderData:
    def test_horizontal_headers(self, qapp: object) -> None:
        model = BatchSummaryTableModel()
        assert model.headerData(0, Qt.Orientation.Horizontal) == "Backup Name"
        assert model.headerData(4, Qt.Orientation.Horizontal) == "Status"


class TestCellData:
    def test_successful_row_values(
        self, qapp: object, sample_batch_results: list[BatchItemResult]
    ) -> None:
        model = BatchSummaryTableModel()
        model.set_results(sample_batch_results)

        assert model.data(model.index(0, 0)) == "TestBackup"
        assert model.data(model.index(0, 1)) == "KR 240 R2900"
        assert model.data(model.index(0, 2)) == 2
        assert model.data(model.index(0, 3)) == 1
        assert model.data(model.index(0, 4)) == "OK"

    def test_failed_row_values(
        self, qapp: object, sample_batch_results: list[BatchItemResult]
    ) -> None:
        model = BatchSummaryTableModel()
        model.set_results(sample_batch_results)

        assert model.data(model.index(2, 0)) == "BrokenBackup"
        assert model.data(model.index(2, 1)) == "-"
        assert model.data(model.index(2, 2)) == 0
        assert model.data(model.index(2, 3)) == 0
        assert "FAILED" in model.data(model.index(2, 4))

    def test_data_returns_none_for_invalid_index(self, qapp: object) -> None:
        model = BatchSummaryTableModel()
        assert model.data(QModelIndex()) is None


class TestForegroundColor:
    def test_success_status_is_dark_green(
        self, qapp: object, sample_batch_results: list[BatchItemResult]
    ) -> None:
        model = BatchSummaryTableModel()
        model.set_results(sample_batch_results)

        color = model.data(model.index(0, 4), Qt.ItemDataRole.ForegroundRole)
        assert color == QColor("darkGreen")

    def test_failure_status_is_red(
        self, qapp: object, sample_batch_results: list[BatchItemResult]
    ) -> None:
        model = BatchSummaryTableModel()
        model.set_results(sample_batch_results)

        color = model.data(model.index(2, 4), Qt.ItemDataRole.ForegroundRole)
        assert color == QColor("red")

    def test_other_columns_have_no_foreground_override(
        self, qapp: object, sample_batch_results: list[BatchItemResult]
    ) -> None:
        model = BatchSummaryTableModel()
        model.set_results(sample_batch_results)

        color = model.data(model.index(0, 0), Qt.ItemDataRole.ForegroundRole)
        assert color is None


class TestIncrementalUpdates:
    def test_add_result_appends_row(
        self, qapp: object, sample_batch_results: list[BatchItemResult]
    ) -> None:
        model = BatchSummaryTableModel()
        for result in sample_batch_results:
            model.add_result(result)

        assert model.rowCount() == 3
        assert model.data(model.index(0, 0)) == "TestBackup"
        assert model.data(model.index(2, 0)) == "BrokenBackup"


class TestResultAt:
    def test_result_at_returns_backing_object(
        self, qapp: object, sample_batch_results: list[BatchItemResult]
    ) -> None:
        model = BatchSummaryTableModel()
        model.set_results(sample_batch_results)

        assert model.result_at(0) is sample_batch_results[0]
        assert model.result_at(2) is sample_batch_results[2]
