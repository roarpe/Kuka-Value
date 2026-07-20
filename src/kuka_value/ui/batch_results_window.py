"""Batch results window: analyze and review multiple backups at once."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, Qt, QThread
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from kuka_value.engine.engine import Engine
from kuka_value.exporters.batch_base import BatchExporter
from kuka_value.exporters.batch_csv_exporter import BatchCsvExporter
from kuka_value.exporters.batch_excel_exporter import BatchExcelExporter
from kuka_value.exporters.batch_json_exporter import BatchJsonExporter
from kuka_value.models.batch_result import BatchItemResult
from kuka_value.ui.batch_analysis_worker import BatchAnalysisWorker
from kuka_value.ui.batch_summary_table_model import BatchSummaryTableModel
from kuka_value.ui.payload_table_model import PayloadTableModel


class BatchResultsWindow(QMainWindow):
    """Reviews the results of analyzing multiple backups at once.

    Only ever talks to Engine (via BatchAnalysisWorker) and the batch
    exporters - never reads backup files directly. Starts analyzing
    immediately on construction: this window exists for exactly one
    batch, given at creation time.
    """

    def __init__(self, engine: Engine, paths: list[Path], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Kuka-Value - Batch Analysis ({len(paths)} backups)")
        self.resize(1100, 700)

        self._engine = engine
        self._paths = paths
        self._results: list[BatchItemResult] = []
        self._thread: QThread | None = None
        self._worker: BatchAnalysisWorker | None = None

        self._summary_model = BatchSummaryTableModel(self)
        self._payload_model = PayloadTableModel(self)

        self._build_ui()
        self._start_batch()

    # -- UI construction -------------------------------------------------

    def _build_ui(self) -> None:
        self._build_toolbar()
        self._build_central_widget()
        self.statusBar().showMessage("Starting batch analysis...")

    def _make_action(self, text: str, slot: Callable[[], None]) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(slot)
        return action

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Batch", self)
        self.addToolBar(toolbar)

        self.action_export_csv = self._make_action("Export Summary CSV...", self._on_export_csv)
        self.action_export_excel = self._make_action(
            "Export Summary Excel...", self._on_export_excel
        )
        self.action_export_json = self._make_action("Export Summary JSON...", self._on_export_json)
        for action in (self.action_export_csv, self.action_export_excel, self.action_export_json):
            action.setEnabled(False)
            toolbar.addAction(action)

    def _build_central_widget(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(max(len(self._paths), 1))
        layout.addWidget(self.progress_bar)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._build_summary_table())
        splitter.addWidget(self._build_payload_panel())
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

        self.setCentralWidget(container)

    def _build_summary_table(self) -> QWidget:
        self.summary_table = QTableView()
        self.summary_table.setModel(self._summary_model)
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.summary_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.summary_table.clicked.connect(self._on_summary_row_clicked)
        return self.summary_table

    def _build_payload_panel(self) -> QWidget:
        group = QGroupBox("Payloads (selected backup)")
        layout = QVBoxLayout(group)
        self.payload_table = QTableView()
        self.payload_table.setModel(self._payload_model)
        self.payload_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.payload_table)
        return group

    # -- Batch execution --------------------------------------------------

    def _start_batch(self) -> None:
        thread = QThread(self)
        worker = BatchAnalysisWorker(self._engine, self._paths)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.item_ready.connect(self._on_item_ready)
        worker.progress.connect(self._on_progress)
        worker.fatal_error.connect(self._on_fatal_error)
        worker.all_finished.connect(thread.quit)
        worker.all_finished.connect(self._on_all_finished)
        thread.finished.connect(self._on_thread_finished)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None

    def _on_item_ready(self, result: BatchItemResult) -> None:
        self._results.append(result)
        self._summary_model.add_result(result)

    def _on_progress(self, completed: int, total: int) -> None:
        self.progress_bar.setValue(completed)
        self.statusBar().showMessage(f"Analyzing {completed}/{total}...")

    def _on_fatal_error(self, message: str) -> None:
        QMessageBox.critical(self, "Batch Analysis Failed", message)

    def _on_all_finished(self) -> None:
        succeeded = sum(1 for r in self._results if r.succeeded)
        failed = len(self._results) - succeeded
        self.statusBar().showMessage(f"Batch complete: {succeeded} succeeded, {failed} failed")
        self.summary_table.resizeColumnsToContents()

        has_results = len(self._results) > 0
        self.action_export_csv.setEnabled(has_results)
        self.action_export_excel.setEnabled(has_results)
        self.action_export_json.setEnabled(has_results)

    # -- Selection -----------------------------------------------------------

    def _on_summary_row_clicked(self, index: QModelIndex | QPersistentModelIndex) -> None:
        result = self._summary_model.result_at(index.row())
        payloads = result.robot.payloads if result.robot is not None else []
        self._payload_model.set_payloads(payloads)
        self.payload_table.resizeColumnsToContents()

    # -- Export --------------------------------------------------------------

    def _on_export_csv(self) -> None:
        self._export(BatchCsvExporter(), "CSV Files (*.csv)", ".csv")

    def _on_export_excel(self) -> None:
        self._export(BatchExcelExporter(), "Excel Files (*.xlsx)", ".xlsx")

    def _on_export_json(self) -> None:
        self._export(BatchJsonExporter(), "JSON Files (*.json)", ".json")

    def _export(self, exporter: BatchExporter, file_filter: str, suffix: str) -> None:
        if not self._results:
            return

        default_name = f"batch_results{suffix}"
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Export Batch Results", default_name, file_filter
        )
        if not path_str:
            return

        try:
            exporter.export_to_file(self._results, Path(path_str))
        except OSError as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
            return

        self.statusBar().showMessage(f"Exported to {path_str}")
