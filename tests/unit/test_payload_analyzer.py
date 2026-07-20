"""Unit tests for PayloadAnalyzer."""

import tempfile
from pathlib import Path

import pytest

from kuka_value.analyzers.payload_analyzer import PayloadAnalyzer
from kuka_value.models.payload import Vector3D
from kuka_value.models.warnings import WarningLog
from kuka_value.parser.backup_reader import BackupReader


@pytest.fixture
def temp_dir() -> Path:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def analyzer() -> PayloadAnalyzer:
    return PayloadAnalyzer()


@pytest.fixture
def warnings() -> WarningLog:
    return WarningLog()


class TestExtraction:
    """Test basic LOAD_DATA extraction."""

    def test_extracts_single_payload(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA[1]={M 10.5,"
            "CM {X 100.0,Y 0.0,Z 50.0,A 0.0,B 0.0,C 0.0},"
            "J {X 0.5,Y 0.5,Z 0.3}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 1
        p = payloads[0]
        assert p.mass == 10.5
        assert p.center_of_gravity == Vector3D(x=100.0, y=0.0, z=50.0)
        assert p.inertia == Vector3D(x=0.5, y=0.5, z=0.3)
        assert p.indices == [1]

    def test_extracts_via_decl_form(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "DECL LOAD_DATA LOAD_DATA[2]={M 5.0,"
            "CM {X 0.0,Y 0.0,Z 10.0,A 0.0,B 0.0,C 0.0},"
            "J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 1
        assert payloads[0].mass == 5.0
        assert payloads[0].indices == [2]

    def test_extracts_multiple_distinct_payloads(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA[1]={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
            "$LOAD_DATA[2]={M 25.0,CM {X 50.0,Y 0.0,Z 100.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 2
        masses = sorted(p.mass for p in payloads)
        assert masses == [10.0, 25.0]

    def test_source_file_recorded(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA[1]={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert payloads[0].source_file == "$config.dat"


class TestDeduplication:
    """Test duplicate payload detection and index merging."""

    def test_deduplicates_identical_payloads(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA[1]={M 10.0,CM {X 5.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
            "$LOAD_DATA[3]={M 10.0,CM {X 5.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 1
        assert payloads[0].indices == [1, 3]

    def test_does_not_merge_different_payloads(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA[1]={M 10.0,CM {X 5.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
            "$LOAD_DATA[2]={M 10.0,CM {X 9.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 2

    def test_deduplicates_across_multiple_files(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config1.dat").write_text(
            "$LOAD_DATA[1]={M 10.0,CM {X 5.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )
        (temp_dir / "$config2.dat").write_text(
            "$LOAD_DATA[7]={M 10.0,CM {X 5.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 1
        assert sorted(payloads[0].indices) == [1, 7]


class TestEmptyPayloadFiltering:
    """Test that empty payloads (M<=0) are excluded."""

    def test_ignores_mass_negative_one(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA[1]={M -1.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 0

    def test_ignores_mass_zero(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA[1]={M 0.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 0

    def test_mixed_empty_and_valid_payloads(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA[1]={M -1.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
            "$LOAD_DATA[2]={M 15.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 1
        assert payloads[0].mass == 15.0


class TestIncompleteData:
    """Test graceful handling of incomplete/corrupt LOAD_DATA."""

    def test_missing_cm_uses_zero_and_warns(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text("$LOAD_DATA[1]={M 10.0,J {X 0.0,Y 0.0,Z 0.0}}\n")

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 1
        assert payloads[0].center_of_gravity == Vector3D.zero()
        assert len(warnings) == 1
        assert "incompleto" in list(warnings)[0].message.lower()

    def test_missing_inertia_is_none_no_warning(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA[1]={M 10.0,CM {X 1.0,Y 2.0,Z 3.0,A 0.0,B 0.0,C 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 1
        assert payloads[0].inertia is None
        assert len(warnings) == 0

    def test_missing_mass_skips_and_warns_corrupt(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA[1]={CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 0
        assert len(warnings) == 1
        assert "corrupt" in list(warnings)[0].message.lower()

    def test_non_struct_value_skips_and_warns(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text("$LOAD_DATA[1]=42\n")

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 0
        assert len(warnings) == 1

    def test_missing_index_skips_and_warns(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 0
        assert len(warnings) == 1

    def test_continues_after_corrupt_entry(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text(
            "$LOAD_DATA[1]=42\n"
            "$LOAD_DATA[2]={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 1
        assert payloads[0].mass == 10.0


class TestFileFiltering:
    """Test that only relevant files are scanned."""

    def test_ignores_non_dat_src_files(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "notes.txt").write_text(
            "$LOAD_DATA[1]={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 0

    def test_scans_src_files_too(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "program.src").write_text(
            "$LOAD_DATA[1]={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}\n"
        )

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert len(payloads) == 1


class TestEmptyBackup:
    """Test edge cases with no data."""

    def test_empty_backup_returns_empty_list(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert payloads == []

    def test_no_load_data_present(
        self, temp_dir: Path, analyzer: PayloadAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$config.dat").write_text("$TOOL_DATA[1]={X 0.0,Y 0.0,Z 100.0}\n")

        reader = BackupReader(temp_dir)
        payloads = analyzer.analyze(reader, warnings)

        assert payloads == []
