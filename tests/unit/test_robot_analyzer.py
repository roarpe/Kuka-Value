"""Unit tests for RobotAnalyzer."""

import tempfile
from pathlib import Path

import pytest

from kuka_value.analyzers.robot_analyzer import ModelSource, RobotAnalyzer
from kuka_value.models.warnings import WarningLog
from kuka_value.parser.backup_reader import BackupReader


@pytest.fixture
def temp_dir() -> Path:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def analyzer() -> RobotAnalyzer:
    return RobotAnalyzer()


@pytest.fixture
def warnings() -> WarningLog:
    return WarningLog()


class TestNormalizeModelName:
    """Test the standalone name normalization logic."""

    def test_normalize_kr240r2900(self, analyzer: RobotAnalyzer) -> None:
        assert analyzer.normalize_model_name("KR240R2900") == "KR 240 R2900"

    def test_normalize_kr270r3100_2k(self, analyzer: RobotAnalyzer) -> None:
        assert analyzer.normalize_model_name("KR270R3100-2K") == "KR 270 R3100-2 K"

    def test_normalize_already_spaced_is_idempotent(self, analyzer: RobotAnalyzer) -> None:
        assert analyzer.normalize_model_name("KR 240 R2900") == "KR 240 R2900"

    def test_normalize_multi_letter_suffix(self, analyzer: RobotAnalyzer) -> None:
        assert analyzer.normalize_model_name("KR6R900SIXX") == "KR 6 R900 SIXX"

    def test_normalize_unrecognized_pattern_unchanged(self, analyzer: RobotAnalyzer) -> None:
        assert analyzer.normalize_model_name("SOMETHING_WEIRD") == "SOMETHING_WEIRD"

    def test_normalize_strips_whitespace(self, analyzer: RobotAnalyzer) -> None:
        assert analyzer.normalize_model_name("  KR240R2900  ") == "KR 240 R2900"


class TestTrafonamePriority:
    """Test priority 1: TRAFONAME detection."""

    def test_finds_trafoname_in_machine_file(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$machine.dat").write_text('$TRAFONAME[]="KR240R2900"\n')

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.source == ModelSource.TRAFONAME
        assert result.model == "KR 240 R2900"
        assert len(warnings) == 0

    def test_trafoname_strips_axis_config_suffix(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$machine.dat").write_text('$TRAFONAME[]="KR240R2900#A1"\n')

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.model == "KR 240 R2900"

    def test_trafoname_wins_over_robot_type_in_same_file(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$machine.dat").write_text(
            '$TRAFONAME[]="KR240R2900"\n$ROBOT_TYPE=#KR_6_R900\n'
        )

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.source == ModelSource.TRAFONAME
        assert result.model == "KR 240 R2900"


class TestMachineDatFallback:
    """Test priority 2: MACHINE.DAT $ROBOT_TYPE detection."""

    def test_falls_back_to_robot_type_enum(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$machine.dat").write_text("$ROBOT_TYPE=#KR_240_R2900\n")

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.source == ModelSource.MACHINE_DAT
        assert result.model == "KR 240 R2900"

    def test_machine_dat_wins_over_robcor(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$machine.dat").write_text("$ROBOT_TYPE=#KR_240_R2900\n")
        (temp_dir / "$robcor.dat").write_text('$ROBCOR_NAME[]="KR 6 R900"\n')

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.source == ModelSource.MACHINE_DAT
        assert result.model == "KR 240 R2900"


class TestRobcorFallback:
    """Test priority 3: ROBCOR detection."""

    def test_falls_back_to_robcor_name(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$robcor.dat").write_text('$ROBCOR_NAME[]="KR 240 R2900"\n')

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.source == ModelSource.ROBCOR
        assert result.model == "KR 240 R2900"

    def test_robcor_type_variable_also_matches(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$robcor.dat").write_text('$ROBCOR_TYPE[]="KR240R2900"\n')

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.source == ModelSource.ROBCOR
        assert result.model == "KR 240 R2900"


class TestBroadFallback:
    """Test priority 4: broad search in unconventional file locations."""

    def test_finds_trafoname_in_unconventionally_named_file(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "custom_config.dat").write_text('$TRAFONAME[]="KR240R2900"\n')

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.source == ModelSource.TRAFONAME
        assert result.model == "KR 240 R2900"

    def test_skips_oversized_files_in_broad_fallback(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        # A large unconventionally-named file should be skipped by the
        # broad fallback scan (performance guard), leaving the model
        # undetected.
        oversized = temp_dir / "huge_dump.dat"
        padding = "; padding\n" * 700_000  # > 5 MB
        oversized.write_text(padding + '$TRAFONAME[]="KR240R2900"\n')

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.source == ModelSource.UNKNOWN


class TestUnknownModel:
    """Test behavior when no model can be determined."""

    def test_empty_backup_returns_unknown(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.source == ModelSource.UNKNOWN
        assert result.model == "UNKNOWN"

    def test_unknown_model_logs_warning(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        reader = BackupReader(temp_dir)
        analyzer.analyze(reader, warnings)

        assert len(warnings) == 1
        assert not warnings.has_errors()

    def test_irrelevant_files_do_not_prevent_unknown(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "readme.txt").write_text("just some notes")
        (temp_dir / "$machine.dat").write_text("$SOME_OTHER_VAR=5\n")

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.source == ModelSource.UNKNOWN


class TestGracefulErrorHandling:
    """Test that analyzer never raises for malformed input."""

    def test_does_not_crash_on_garbage_content(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$machine.dat").write_text("this is not valid KRL at all {{{ ]][")

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.source == ModelSource.UNKNOWN

    def test_continues_scanning_after_unparseable_file(
        self, temp_dir: Path, analyzer: RobotAnalyzer, warnings: WarningLog
    ) -> None:
        (temp_dir / "$machine_bad.dat").write_text("garbage {{{ content")
        (temp_dir / "$machine_good.dat").write_text('$TRAFONAME[]="KR240R2900"\n')

        reader = BackupReader(temp_dir)
        result = analyzer.analyze(reader, warnings)

        assert result.model == "KR 240 R2900"
