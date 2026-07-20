"""Integration tests for Engine: full analysis pipeline."""

import tempfile
from pathlib import Path
from zipfile import ZipFile

import pytest

from kuka_value.analyzers.robot_analyzer import RobotAnalyzer
from kuka_value.engine.engine import Engine
from kuka_value.models.controller_info import ControllerType
from kuka_value.parser.backup_reader import BackupReader


@pytest.fixture
def temp_dir() -> Path:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def engine() -> Engine:
    return Engine()


def _load_data_line(index: int, mass: float, x: float = 0.0) -> str:
    return (
        f"$LOAD_DATA[{index}]={{M {mass},"
        f"CM {{X {x},Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0}},"
        f"J {{X 0.0,Y 0.0,Z 0.0}}}}\n"
    )


class TestFullPipeline:
    """Test end-to-end backup analysis via Engine.parse()."""

    def test_parse_folder_backup(self, temp_dir: Path, engine: Engine) -> None:
        backup = temp_dir / "MyRobotBackup"
        backup.mkdir()
        (backup / "$machine.dat").write_text('$TRAFONAME[]="KR240R2900"\n')
        (backup / "$config.dat").write_text(_load_data_line(1, 10.5, x=100.0))

        robot = engine.parse(backup)

        assert robot.model == "KR 240 R2900"
        assert len(robot.payloads) == 1
        assert robot.payloads[0].mass == 10.5
        assert robot.general.backup_name == "MyRobotBackup"

    def test_parse_zip_backup(self, temp_dir: Path, engine: Engine) -> None:
        source = temp_dir / "source"
        source.mkdir()
        (source / "$machine.dat").write_text('$TRAFONAME[]="KR240R2900"\n')
        (source / "$config.dat").write_text(_load_data_line(1, 15.0))

        zip_path = temp_dir / "MyRobot.zip"
        with ZipFile(zip_path, "w") as zf:
            for file in source.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(source))

        robot = engine.parse(zip_path)

        assert robot.model == "KR 240 R2900"
        assert len(robot.payloads) == 1
        assert robot.general.backup_name == "MyRobot"

    def test_parse_deduplicates_payloads_end_to_end(self, temp_dir: Path, engine: Engine) -> None:
        backup = temp_dir / "backup"
        backup.mkdir()
        (backup / "$machine.dat").write_text('$TRAFONAME[]="KR6R900"\n')
        (backup / "$config1.dat").write_text(_load_data_line(1, 10.0, x=5.0))
        (backup / "$config2.dat").write_text(_load_data_line(5, 10.0, x=5.0))

        robot = engine.parse(backup)

        assert len(robot.payloads) == 1
        assert sorted(robot.payloads[0].indices) == [1, 5]

    def test_parse_empty_backup_returns_unknown_with_warning(
        self, temp_dir: Path, engine: Engine
    ) -> None:
        backup = temp_dir / "empty"
        backup.mkdir()

        robot = engine.parse(backup)

        assert robot.model == "UNKNOWN"
        assert robot.payloads == []
        assert len(robot.warnings) >= 1
        assert not robot.warnings.has_errors()

    def test_parse_controller_defaults_to_unknown(self, temp_dir: Path, engine: Engine) -> None:
        backup = temp_dir / "backup"
        backup.mkdir()
        (backup / "$machine.dat").write_text('$TRAFONAME[]="KR240R2900"\n')

        robot = engine.parse(backup)

        assert robot.controller.controller_type == ControllerType.UNKNOWN
        assert robot.controller.serial_number is None


class TestBackupNaming:
    """Test how backup_name is derived from the input path."""

    def test_backup_name_from_folder(self, temp_dir: Path, engine: Engine) -> None:
        backup = temp_dir / "ProductionCell42"
        backup.mkdir()

        robot = engine.parse(backup)

        assert robot.general.backup_name == "ProductionCell42"

    def test_backup_name_strips_zip_extension(self, temp_dir: Path, engine: Engine) -> None:
        source = temp_dir / "source"
        source.mkdir()
        zip_path = temp_dir / "Cell42_2024-01-15.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("placeholder.txt", "x")

        robot = engine.parse(zip_path)

        assert robot.general.backup_name == "Cell42_2024-01-15"


class TestErrorPropagation:
    """Test that I/O boundary errors propagate (per architecture: file
    not found and ZIP corruption are legitimate exceptions, not warnings)."""

    def test_nonexistent_path_raises(self, temp_dir: Path, engine: Engine) -> None:
        with pytest.raises(FileNotFoundError):
            engine.parse(temp_dir / "does_not_exist")

    def test_invalid_zip_raises(self, temp_dir: Path, engine: Engine) -> None:
        bad_zip = temp_dir / "bad.zip"
        bad_zip.write_text("not a zip file")

        with pytest.raises(ValueError):
            engine.parse(bad_zip)


class TestResourceCleanup:
    """Test that the backup reader is always closed, even on failure."""

    def test_reader_closed_on_success(self, temp_dir: Path, engine: Engine) -> None:
        source = temp_dir / "source"
        source.mkdir()
        zip_path = temp_dir / "backup.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("placeholder.txt", "x")

        close_calls = []
        original_close = BackupReader.close

        def tracking_close(self: BackupReader) -> None:
            close_calls.append(True)
            original_close(self)

        BackupReader.close = tracking_close  # type: ignore[method-assign]
        try:
            engine.parse(zip_path)
        finally:
            BackupReader.close = original_close  # type: ignore[method-assign]

        # close() is idempotent, so __del__ may also trigger a (no-op)
        # call when the reader is garbage collected; what matters is
        # that Engine explicitly closed it at least once.
        assert len(close_calls) >= 1

    def test_reader_closed_even_if_analyzer_raises(
        self, temp_dir: Path, engine: Engine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = temp_dir / "source"
        source.mkdir()
        zip_path = temp_dir / "backup.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("placeholder.txt", "x")

        close_calls = []
        original_close = BackupReader.close

        def tracking_close(self: BackupReader) -> None:
            close_calls.append(True)
            original_close(self)

        monkeypatch.setattr(BackupReader, "close", tracking_close)

        def boom(_self: RobotAnalyzer, _reader: object, _warnings: object) -> None:
            raise RuntimeError("simulated analyzer failure")

        monkeypatch.setattr(RobotAnalyzer, "analyze", boom)

        with pytest.raises(RuntimeError):
            engine.parse(zip_path)

        assert len(close_calls) >= 1
