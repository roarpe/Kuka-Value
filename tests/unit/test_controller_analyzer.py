"""Unit tests for ControllerAnalyzer."""

import tempfile
from pathlib import Path

import pytest

from kuka_value.analyzers.controller_analyzer import ControllerAnalyzer
from kuka_value.parser.backup_reader import BackupReader


@pytest.fixture
def temp_dir() -> Path:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def analyzer() -> ControllerAnalyzer:
    return ControllerAnalyzer()


class TestRobotInfoXmlPriority:
    def test_serial_from_robot_info_xml(self, temp_dir: Path, analyzer: ControllerAnalyzer) -> None:
        (temp_dir / "RobotInfo.xml").write_text("<Root><SerialNumber>626925</SerialNumber></Root>")

        reader = BackupReader(temp_dir)
        assert analyzer.detect_serial_number(reader) == "626925"

    def test_robot_info_xml_takes_priority_over_am_ini(
        self, temp_dir: Path, analyzer: ControllerAnalyzer
    ) -> None:
        (temp_dir / "RobotInfo.xml").write_text("<Root><SerialNumber>111</SerialNumber></Root>")
        (temp_dir / "am.ini").write_text("IRSerialNr=222\n")

        reader = BackupReader(temp_dir)
        assert analyzer.detect_serial_number(reader) == "111"


class TestAmIniPriority:
    def test_serial_from_am_ini(self, temp_dir: Path, analyzer: ControllerAnalyzer) -> None:
        (temp_dir / "am.ini").write_text("SomeOtherKey=x\nIRSerialNr=626925\n")

        reader = BackupReader(temp_dir)
        assert analyzer.detect_serial_number(reader) == "626925"

    def test_am_ini_filename_case_insensitive(
        self, temp_dir: Path, analyzer: ControllerAnalyzer
    ) -> None:
        (temp_dir / "AM.INI").write_text("IRSerialNr=999\n")

        reader = BackupReader(temp_dir)
        assert analyzer.detect_serial_number(reader) == "999"

    def test_am_ini_tolerates_spacing_around_equals(
        self, temp_dir: Path, analyzer: ControllerAnalyzer
    ) -> None:
        (temp_dir / "am.ini").write_text("IRSerialNr = 777\n")

        reader = BackupReader(temp_dir)
        assert analyzer.detect_serial_number(reader) == "777"


class TestBroadFallback:
    def test_finds_serial_number_keyword_in_arbitrary_file(
        self, temp_dir: Path, analyzer: ControllerAnalyzer
    ) -> None:
        (temp_dir / "config.cfg").write_text('RobotSerialNumber="626925"\n')

        reader = BackupReader(temp_dir)
        assert analyzer.detect_serial_number(reader) == "626925"

    def test_ignores_files_with_unrecognized_extensions(
        self, temp_dir: Path, analyzer: ControllerAnalyzer
    ) -> None:
        (temp_dir / "notes.txt").write_text("SerialNumber=626925\n")

        reader = BackupReader(temp_dir)
        assert analyzer.detect_serial_number(reader) is None

    def test_skips_oversized_files_in_fallback(
        self, temp_dir: Path, analyzer: ControllerAnalyzer
    ) -> None:
        oversized = temp_dir / "huge.cfg"
        oversized.write_text("SerialNumber=626925\n" + "x" * (6 * 1024 * 1024))

        reader = BackupReader(temp_dir)
        assert analyzer.detect_serial_number(reader) is None


class TestNotFound:
    def test_returns_none_when_nothing_matches(
        self, temp_dir: Path, analyzer: ControllerAnalyzer
    ) -> None:
        (temp_dir / "unrelated.dat").write_text("nothing interesting here\n")

        reader = BackupReader(temp_dir)
        assert analyzer.detect_serial_number(reader) is None

    def test_empty_backup_returns_none(self, temp_dir: Path, analyzer: ControllerAnalyzer) -> None:
        reader = BackupReader(temp_dir)
        assert analyzer.detect_serial_number(reader) is None

    def test_never_raises_on_unreadable_or_malformed_files(
        self, temp_dir: Path, analyzer: ControllerAnalyzer
    ) -> None:
        (temp_dir / "RobotInfo.xml").write_text("<Root><Unclosed>")
        (temp_dir / "am.ini").write_text("garbage\x00binary\n")

        reader = BackupReader(temp_dir)
        assert analyzer.detect_serial_number(reader) is None
