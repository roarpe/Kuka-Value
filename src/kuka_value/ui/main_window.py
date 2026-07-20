"""Main application window: load a backup, review results, export."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from kuka_value.engine.engine import Engine
from kuka_value.exporters.base import Exporter
from kuka_value.exporters.csv_exporter import CsvExporter
from kuka_value.exporters.excel_exporter import ExcelExporter
from kuka_value.exporters.json_exporter import JsonExporter
from kuka_value.models.robot_info import RobotInfo
from kuka_value.models.warnings import WarningLevel
from kuka_value.ui.analysis_worker import AnalysisWorker
from kuka_value.ui.batch_results_window import BatchResultsWindow
from kuka_value.ui.payload_table_model import PayloadTableModel


def discover_batch_paths(folder: Path) -> list[Path]:
    """Find backups directly inside a folder selected for batch analysis.

    Each immediate child that is a .zip file or a subdirectory counts
    as one backup (a folder-based backup's own internal subdirectories
    are not treated as separate backups - only the folder the user
    selected is scanned, non-recursively).
    """
    return sorted(
        child for child in folder.iterdir() if child.is_dir() or child.suffix.lower() == ".zip"
    )


class MainWindow(QMainWindow):
    """Kuka-Value main window.

    Only ever talks to Engine and the exporters - never reads backup
    files directly.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Kuka-Value")
        self.resize(1000, 650)

        self._engine = Engine()
        self._current_robot: RobotInfo | None = None
        self._thread: QThread | None = None
        self._worker: AnalysisWorker | None = None
        self._payload_model = PayloadTableModel(self)
        self._batch_windows: list[BatchResultsWindow] = []

        self._build_ui()
        self._set_robot_loaded(False)

    # -- UI construction -----------------------------------------------

    def _build_ui(self) -> None:
        self._build_toolbar()
        self._build_central_widget()
        self.statusBar().showMessage("No backup loaded")

    def _make_action(self, text: str, slot: Callable[[], None]) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(slot)
        return action

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main", self)
        self.addToolBar(toolbar)

        self.action_open_zip = self._make_action("Open ZIP...", self._on_open_zip)
        self.action_open_folder = self._make_action("Open Folder...", self._on_open_folder)
        self.action_batch_select_zips = self._make_action(
            "Select Multiple ZIPs...", self._on_batch_select_zips
        )
        self.action_batch_analyze = self._make_action(
            "Batch Analyze Folder...", self._on_batch_analyze_folder
        )
        toolbar.addAction(self.action_open_zip)
        toolbar.addAction(self.action_open_folder)
        toolbar.addAction(self.action_batch_select_zips)
        toolbar.addAction(self.action_batch_analyze)
        toolbar.addSeparator()

        self.action_export_csv = self._make_action("Export CSV...", self._on_export_csv)
        self.action_export_excel = self._make_action("Export Excel...", self._on_export_excel)
        self.action_export_json = self._make_action("Export JSON...", self._on_export_json)
        toolbar.addAction(self.action_export_csv)
        toolbar.addAction(self.action_export_excel)
        toolbar.addAction(self.action_export_json)

    def _build_central_widget(self) -> None:
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._build_top_splitter())
        splitter.addWidget(self._build_warnings_panel())
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

    def _build_top_splitter(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_info_panel())
        splitter.addWidget(self._build_payload_table())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        return splitter

    def _build_info_panel(self) -> QWidget:
        group = QGroupBox("Robot Info")
        form = QFormLayout(group)

        self.label_model = QLabel("-")
        self.label_backup_name = QLabel("-")
        self.label_kss_version = QLabel("-")
        self.label_controller = QLabel("-")
        self.label_serial = QLabel("-")
        self.label_payload_count = QLabel("-")

        form.addRow("Model:", self.label_model)
        form.addRow("Backup Name:", self.label_backup_name)
        form.addRow("KSS Version:", self.label_kss_version)
        form.addRow("Controller:", self.label_controller)
        form.addRow("Serial Number:", self.label_serial)
        form.addRow("Unique Payloads:", self.label_payload_count)

        return group

    def _build_payload_table(self) -> QWidget:
        self.table_view = QTableView()
        self.table_view.setModel(self._payload_model)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        return self.table_view

    def _build_warnings_panel(self) -> QWidget:
        group = QGroupBox("Warnings")
        layout = QVBoxLayout(group)
        self.warnings_list = QListWidget()
        layout.addWidget(self.warnings_list)
        return group

    # -- Backup loading --------------------------------------------------

    def _on_open_zip(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open KUKA Backup", "", "ZIP Archives (*.zip)"
        )
        if path_str:
            self._start_analysis(Path(path_str))

    def _on_open_folder(self) -> None:
        path_str = QFileDialog.getExistingDirectory(self, "Open KUKA Backup Folder")
        if path_str:
            self._start_analysis(Path(path_str))

    def _on_batch_select_zips(self) -> None:
        path_strs, _ = QFileDialog.getOpenFileNames(
            self, "Select Multiple KUKA Backups", "", "ZIP Archives (*.zip)"
        )
        if not path_strs:
            return

        self._open_batch_window([Path(p) for p in path_strs])

    def _on_batch_analyze_folder(self) -> None:
        folder_str = QFileDialog.getExistingDirectory(
            self, "Select Folder Containing Multiple Backups"
        )
        if not folder_str:
            return

        paths = discover_batch_paths(Path(folder_str))
        if not paths:
            QMessageBox.information(
                self,
                "No Backups Found",
                "No .zip files or subfolders were found directly inside the selected folder.",
            )
            return

        self._open_batch_window(paths)

    def _open_batch_window(self, paths: list[Path]) -> None:
        batch_window = BatchResultsWindow(self._engine, paths, parent=self)
        self._batch_windows.append(batch_window)
        batch_window.show()

    def _start_analysis(self, path: Path) -> None:
        self.statusBar().showMessage(f"Analyzing {path.name}...")
        self._set_actions_enabled(False)

        thread = QThread(self)
        worker = AnalysisWorker(self._engine, path)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_analysis_finished)
        worker.finished.connect(thread.quit)
        worker.failed.connect(self._on_analysis_failed)
        worker.failed.connect(thread.quit)
        thread.finished.connect(self._on_thread_finished)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None

    def _on_analysis_finished(self, robot: RobotInfo) -> None:
        self._current_robot = robot
        self._payload_model.set_payloads(robot.payloads)
        self.table_view.resizeColumnsToContents()
        self._update_info_panel(robot)
        self._update_warnings_panel(robot)
        self.statusBar().showMessage(f"Loaded: {robot.general.backup_name}")
        self._set_robot_loaded(True)

    def _on_analysis_failed(self, message: str) -> None:
        self.statusBar().showMessage("Analysis failed")
        self._set_actions_enabled(True)
        QMessageBox.critical(self, "Analysis Failed", message)

    # -- Display updates ---------------------------------------------------

    def _update_info_panel(self, robot: RobotInfo) -> None:
        self.label_model.setText(robot.model)
        self.label_backup_name.setText(robot.general.backup_name)
        self.label_kss_version.setText(robot.general.kss_version or "-")
        self.label_controller.setText(robot.controller.controller_type.value)
        self.label_serial.setText(robot.controller.serial_number or "-")
        self.label_payload_count.setText(str(len(robot.payloads)))

    def _update_warnings_panel(self, robot: RobotInfo) -> None:
        self.warnings_list.clear()
        for warning in robot.warnings:
            item = QListWidgetItem(f"[{warning.level.value}] {warning.source}: {warning.message}")
            item.setForeground(self._warning_color(warning.level))
            self.warnings_list.addItem(item)

    @staticmethod
    def _warning_color(level: WarningLevel) -> Qt.GlobalColor:
        if level == WarningLevel.ERROR:
            return Qt.GlobalColor.red
        if level == WarningLevel.WARNING:
            return Qt.GlobalColor.darkYellow
        return Qt.GlobalColor.black

    def _set_robot_loaded(self, loaded: bool) -> None:
        self.action_export_csv.setEnabled(loaded)
        self.action_export_excel.setEnabled(loaded)
        self.action_export_json.setEnabled(loaded)
        self._set_actions_enabled(True)

    def _set_actions_enabled(self, enabled: bool) -> None:
        self.action_open_zip.setEnabled(enabled)
        self.action_open_folder.setEnabled(enabled)
        self.action_batch_select_zips.setEnabled(enabled)
        self.action_batch_analyze.setEnabled(enabled)

    # -- Export --------------------------------------------------------------

    def _on_export_csv(self) -> None:
        self._export(CsvExporter(), "CSV Files (*.csv)", ".csv")

    def _on_export_excel(self) -> None:
        self._export(ExcelExporter(), "Excel Files (*.xlsx)", ".xlsx")

    def _on_export_json(self) -> None:
        self._export(JsonExporter(), "JSON Files (*.json)", ".json")

    def _export(self, exporter: Exporter, file_filter: str, suffix: str) -> None:
        if self._current_robot is None:
            return

        default_name = f"{self._current_robot.general.backup_name}{suffix}"
        path_str, _ = QFileDialog.getSaveFileName(self, "Export Results", default_name, file_filter)
        if not path_str:
            return

        try:
            exporter.export_to_file(self._current_robot, Path(path_str))
        except OSError as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
            return

        self.statusBar().showMessage(f"Exported to {path_str}")
