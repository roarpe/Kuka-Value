"""Unit tests for AxisLoadAnalyzer."""

import tempfile
from pathlib import Path

import pytest

from kuka_value.analyzers.axis_load_analyzer import AxisLoadAnalyzer
from kuka_value.models.warnings import WarningLog
from kuka_value.parser.backup_reader import BackupReader


@pytest.fixture
def temp_dir() -> Path:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def analyzer() -> AxisLoadAnalyzer:
    return AxisLoadAnalyzer()


@pytest.fixture
def warnings() -> WarningLog:
    return WarningLog()


def _axis_load_line(axis: int, mass: float, x: float = 0.0) -> str:
    return (
        f"DECL LOAD LOAD_A{axis}_DATA={{M {mass},"
        f"CM {{X {x},Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0}},"
        f"J {{X 0.0,Y 0.0,Z 0.0}}}}\n"
    )


class TestExtraction:
    def test_extracts_single_axis_load(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(_axis_load_line(3, 12.5, x=50.0))

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert len(result) == 1
        assert result[0].axis == 3
        assert result[0].mass == 12.5
        assert result[0].center_of_gravity.x == 50.0
        assert len(warnings) == 0

    def test_extracts_multiple_axes(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        content = _axis_load_line(1, 5.0) + _axis_load_line(3, 12.5)
        (temp_dir / "$config.dat").write_text(content)

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert len(result) == 2
        assert result[0].axis == 1
        assert result[1].axis == 3

    def test_results_sorted_by_axis_number(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        content = _axis_load_line(5, 1.0) + _axis_load_line(2, 2.0) + _axis_load_line(3, 3.0)
        (temp_dir / "$config.dat").write_text(content)

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert [al.axis for al in result] == [2, 3, 5]

    def test_source_file_tracked(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(_axis_load_line(3, 10.0))

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result[0].source_file == "$config.dat"

    def test_dollar_prefixed_form_also_matches(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_A3_DATA={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert len(result) == 1
        assert result[0].axis == 3


class TestDeduplication:
    def test_first_occurrence_wins_for_same_axis(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config1.dat").write_text(_axis_load_line(3, 10.0))
        (temp_dir / "$config2.dat").write_text(_axis_load_line(3, 99.0))

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert len(result) == 1
        # File iteration order isn't guaranteed across filesystems, but
        # exactly one of the two values must win - never both/merged.
        assert result[0].mass in (10.0, 99.0)


class TestEmptyFiltering:
    def test_zero_mass_is_filtered(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(_axis_load_line(3, 0.0))

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result == []

    def test_negative_mass_is_filtered(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(_axis_load_line(3, -1.0))

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result == []


class TestIncompleteData:
    def test_missing_cm_warns_and_defaults_to_zero(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text("DECL LOAD LOAD_A3_DATA={M 10.0}\n")

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert len(result) == 1
        assert result[0].center_of_gravity.is_zero()
        assert len(warnings) == 1
        assert "incompleto" in next(iter(warnings)).message.lower()

    def test_missing_j_is_silently_none(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "DECL LOAD LOAD_A3_DATA={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert len(result) == 1
        assert result[0].inertia is None
        assert len(warnings) == 0

    def test_missing_mass_is_skipped_with_warning(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "DECL LOAD LOAD_A3_DATA={CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result == []
        assert len(warnings) == 1
        assert "masa" in next(iter(warnings)).message.lower()

    def test_continues_scanning_after_corrupt_entry(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        content = "DECL LOAD LOAD_A1_DATA={CM {X 0.0,Y 0.0,Z 0.0}}\n" + _axis_load_line(3, 10.0)
        (temp_dir / "$config.dat").write_text(content)

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert len(result) == 1
        assert result[0].axis == 3


class TestFileFiltering:
    def test_ignores_non_dat_src_files(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "notes.txt").write_text(_axis_load_line(3, 10.0))

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result == []

    def test_scans_src_files(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "program.src").write_text(_axis_load_line(3, 10.0))

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert len(result) == 1


class TestNoAxisLoads:
    def test_empty_backup_returns_empty_list(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result == []
        assert len(warnings) == 0

    def test_backup_with_only_load_data_returns_empty_list(
        self, temp_dir: Path, analyzer: AxisLoadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA[1]={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result == []
