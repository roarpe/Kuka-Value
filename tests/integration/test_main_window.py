"""Integration tests for MainWindow.

These instantiate the real widget tree via pytest-qt's qtbot fixture.
Blocking modal dialogs (QMessageBox, QFileDialog) are monkeypatched so
tests never hang waiting for a real user.
"""

import tempfile
from pathlib import Path
from zipfile import ZipFile

import pytest
from PySide6.QtGui import QColor

from kuka_value.exporters.csv_exporter import CsvExporter
from kuka_value.exporters.excel_exporter import ExcelExporter
from kuka_value.exporters.json_exporter import JsonExporter
from kuka_value.models.controller_info import ControllerInfo, ControllerType
from kuka_value.models.general_info import GeneralInfo
from kuka_value.models.robot_info import RobotInfo
from kuka_value.models.warnings import WarningLog
from kuka_value.ui.main_window import MainWindow


@pytest.fixture
def main_window(qtbot: object) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)  # type: ignore[attr-defined]
    return window


@pytest.fixture
def temp_dir() -> Path:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestInitialState:
    def test_export_actions_disabled_initially(self, main_window: MainWindow) -> None:
        assert not main_window.action_export_csv.isEnabled()
        assert not main_window.action_export_excel.isEnabled()
        assert not main_window.action_export_json.isEnabled()

    def test_open_actions_enabled_initially(self, main_window: MainWindow) -> None:
        assert main_window.action_open_zip.isEnabled()
        assert main_window.action_open_folder.isEnabled()

    def test_labels_show_placeholder(self, main_window: MainWindow) -> None:
        assert main_window.label_model.text() == "-"
        assert main_window.label_backup_name.text() == "-"

    def test_payload_table_empty(self, main_window: MainWindow) -> None:
        assert main_window._payload_model.rowCount() == 0


class TestAnalysisFinished:
    def test_updates_info_panel(
        self, main_window: MainWindow, sample_robot_info: RobotInfo
    ) -> None:
        main_window._on_analysis_finished(sample_robot_info)

        assert main_window.label_model.text() == "KR 240 R2900"
        assert main_window.label_backup_name.text() == "TestBackup"
        assert main_window.label_kss_version.text() == "8.6.8"
        assert main_window.label_controller.text() == "KRC4"
        assert main_window.label_serial.text() == "12345"
        assert main_window.label_payload_count.text() == "2"

    def test_populates_payload_table(
        self, main_window: MainWindow, sample_robot_info: RobotInfo
    ) -> None:
        main_window._on_analysis_finished(sample_robot_info)
        assert main_window._payload_model.rowCount() == 2

    def test_populates_warnings_panel(
        self, main_window: MainWindow, sample_robot_info: RobotInfo
    ) -> None:
        main_window._on_analysis_finished(sample_robot_info)
        assert main_window.warnings_list.count() == 1

    def test_enables_export_actions(
        self, main_window: MainWindow, sample_robot_info: RobotInfo
    ) -> None:
        main_window._on_analysis_finished(sample_robot_info)

        assert main_window.action_export_csv.isEnabled()
        assert main_window.action_export_excel.isEnabled()
        assert main_window.action_export_json.isEnabled()

    def test_sets_current_robot(
        self, main_window: MainWindow, sample_robot_info: RobotInfo
    ) -> None:
        main_window._on_analysis_finished(sample_robot_info)
        assert main_window._current_robot is sample_robot_info


class TestAnalysisFailed:
    def test_shows_error_dialog(
        self, main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        shown_messages = []
        monkeypatch.setattr(
            "kuka_value.ui.main_window.QMessageBox.critical",
            lambda *args: shown_messages.append(args[-1]),
        )

        main_window._on_analysis_failed("backup not found")

        assert shown_messages == ["backup not found"]

    def test_reenables_open_actions(
        self, main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("kuka_value.ui.main_window.QMessageBox.critical", lambda *_args: None)

        main_window.action_open_zip.setEnabled(False)
        main_window.action_open_folder.setEnabled(False)

        main_window._on_analysis_failed("boom")

        assert main_window.action_open_zip.isEnabled()
        assert main_window.action_open_folder.isEnabled()

    def test_does_not_touch_current_robot(
        self, main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("kuka_value.ui.main_window.QMessageBox.critical", lambda *_args: None)

        main_window._on_analysis_failed("boom")

        assert main_window._current_robot is None


class TestExport:
    def test_export_with_no_robot_does_nothing(
        self, main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dialog_calls = []
        monkeypatch.setattr(
            "kuka_value.ui.main_window.QFileDialog.getSaveFileName",
            lambda *_args: dialog_calls.append(True),
        )

        main_window._on_export_csv()

        assert dialog_calls == []

    def test_export_csv_writes_expected_content(
        self,
        main_window: MainWindow,
        sample_robot_info: RobotInfo,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / "result.csv"
        monkeypatch.setattr(
            "kuka_value.ui.main_window.QFileDialog.getSaveFileName",
            lambda *_args: (str(target), "CSV Files (*.csv)"),
        )

        main_window._on_analysis_finished(sample_robot_info)
        main_window._on_export_csv()

        assert target.exists()
        assert target.read_bytes() == CsvExporter().export(sample_robot_info)

    def test_export_cancelled_dialog_writes_nothing(
        self,
        main_window: MainWindow,
        sample_robot_info: RobotInfo,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "kuka_value.ui.main_window.QFileDialog.getSaveFileName",
            lambda *_args: ("", ""),
        )

        main_window._on_analysis_finished(sample_robot_info)
        main_window._on_export_csv()

        assert list(tmp_path.iterdir()) == []

    def test_export_excel_writes_expected_content(
        self,
        main_window: MainWindow,
        sample_robot_info: RobotInfo,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / "result.xlsx"
        monkeypatch.setattr(
            "kuka_value.ui.main_window.QFileDialog.getSaveFileName",
            lambda *_args: (str(target), "Excel Files (*.xlsx)"),
        )

        main_window._on_analysis_finished(sample_robot_info)
        main_window._on_export_excel()

        assert target.exists()
        assert target.read_bytes() == ExcelExporter().export(sample_robot_info)

    def test_export_json_writes_expected_content(
        self,
        main_window: MainWindow,
        sample_robot_info: RobotInfo,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / "result.json"
        monkeypatch.setattr(
            "kuka_value.ui.main_window.QFileDialog.getSaveFileName",
            lambda *_args: (str(target), "JSON Files (*.json)"),
        )

        main_window._on_analysis_finished(sample_robot_info)
        main_window._on_export_json()

        assert target.exists()
        assert target.read_bytes() == JsonExporter().export(sample_robot_info)

    def test_export_oserror_shows_error_dialog(
        self,
        main_window: MainWindow,
        sample_robot_info: RobotInfo,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / "result.csv"
        monkeypatch.setattr(
            "kuka_value.ui.main_window.QFileDialog.getSaveFileName",
            lambda *_args: (str(target), "CSV Files (*.csv)"),
        )

        def boom(_self: object, _robot: object, _path: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr("kuka_value.exporters.csv_exporter.CsvExporter.export_to_file", boom)

        shown_messages = []
        monkeypatch.setattr(
            "kuka_value.ui.main_window.QMessageBox.critical",
            lambda *args: shown_messages.append(args[-1]),
        )

        main_window._on_analysis_finished(sample_robot_info)
        main_window._on_export_csv()

        assert shown_messages == ["disk full"]


class TestWarningColors:
    def test_error_level_warning_is_red(self, main_window: MainWindow) -> None:
        warnings = WarningLog()
        warnings.error("Corrupt backup", source="Engine")
        robot = RobotInfo(
            model="UNKNOWN",
            general=GeneralInfo(backup_name="test"),
            controller=ControllerInfo(controller_type=ControllerType.UNKNOWN),
            payloads=[],
            warnings=warnings,
        )

        main_window._on_analysis_finished(robot)

        item = main_window.warnings_list.item(0)
        assert item.foreground().color() == QColor("red")

    def test_info_level_warning_is_black(self, main_window: MainWindow) -> None:
        warnings = WarningLog()
        warnings.info("Analysis started", source="Engine")
        robot = RobotInfo(
            model="UNKNOWN",
            general=GeneralInfo(backup_name="test"),
            controller=ControllerInfo(controller_type=ControllerType.UNKNOWN),
            payloads=[],
            warnings=warnings,
        )

        main_window._on_analysis_finished(robot)

        item = main_window.warnings_list.item(0)
        assert item.foreground().color() == QColor("black")


class TestFullOpenFlow:
    def test_open_zip_runs_analysis_end_to_end(
        self,
        main_window: MainWindow,
        temp_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        qtbot: object,
    ) -> None:
        source = temp_dir / "source"
        source.mkdir()
        (source / "$machine.dat").write_text('$TRAFONAME[]="KR240R2900"\n')

        zip_path = temp_dir / "backup.zip"
        with ZipFile(zip_path, "w") as zf:
            for file in source.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(source))

        monkeypatch.setattr(
            "kuka_value.ui.main_window.QFileDialog.getOpenFileName",
            lambda *_args: (str(zip_path), "ZIP Archives (*.zip)"),
        )

        main_window._on_open_zip()
        qtbot.waitUntil(lambda: main_window._current_robot is not None, timeout=5000)  # type: ignore[attr-defined]

        assert main_window._current_robot.model == "KR 240 R2900"
        assert main_window.label_model.text() == "KR 240 R2900"

        qtbot.waitUntil(lambda: main_window._thread is None, timeout=5000)  # type: ignore[attr-defined]

    def test_open_folder_runs_analysis_end_to_end(
        self,
        main_window: MainWindow,
        temp_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        qtbot: object,
    ) -> None:
        backup = temp_dir / "backup"
        backup.mkdir()
        (backup / "$machine.dat").write_text('$TRAFONAME[]="KR6R900"\n')

        monkeypatch.setattr(
            "kuka_value.ui.main_window.QFileDialog.getExistingDirectory",
            lambda *_args: str(backup),
        )

        main_window._on_open_folder()
        qtbot.waitUntil(lambda: main_window._current_robot is not None, timeout=5000)  # type: ignore[attr-defined]

        assert main_window._current_robot.model == "KR 6 R900"

    def test_open_zip_cancelled_dialog_does_nothing(
        self, main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "kuka_value.ui.main_window.QFileDialog.getOpenFileName",
            lambda *_args: ("", ""),
        )

        main_window._on_open_zip()

        assert main_window._current_robot is None
        assert main_window._thread is None

    def test_open_folder_cancelled_dialog_does_nothing(
        self, main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "kuka_value.ui.main_window.QFileDialog.getExistingDirectory",
            lambda *_args: "",
        )

        main_window._on_open_folder()

        assert main_window._current_robot is None
        assert main_window._thread is None
