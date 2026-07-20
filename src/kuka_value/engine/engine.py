"""Engine: the single public entry point into backup analysis.

The UI (or any other caller) never touches the parser, analyzers, or
file I/O directly. It only ever calls:

    engine = Engine()
    robot = engine.parse(path)
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from kuka_value.analyzers.axis_load_analyzer import AxisLoadAnalyzer
from kuka_value.analyzers.controller_analyzer import ControllerAnalyzer
from kuka_value.analyzers.payload_analyzer import PayloadAnalyzer
from kuka_value.analyzers.robot_analyzer import RobotAnalyzer
from kuka_value.models.batch_result import BatchItemResult
from kuka_value.models.controller_info import ControllerInfo, ControllerType
from kuka_value.models.general_info import GeneralInfo
from kuka_value.models.robot_info import RobotInfo
from kuka_value.models.warnings import WarningLog
from kuka_value.parser.backup_reader import BackupReader


class Engine:
    """Orchestrates backup reading, analysis, and result assembly."""

    def __init__(self) -> None:
        self._robot_analyzer = RobotAnalyzer()
        self._payload_analyzer = PayloadAnalyzer()
        self._axis_load_analyzer = AxisLoadAnalyzer()
        self._controller_analyzer = ControllerAnalyzer()

    def parse(self, path: Path) -> RobotInfo:
        """Analyze a KUKA robot backup.

        Args:
            path: Path to a .zip backup file or an extracted backup folder

        Returns:
            Complete analysis result, including any warnings recorded
            for incomplete or malformed data encountered along the way

        Raises:
            FileNotFoundError: If path does not exist
            ValueError: If path is a ZIP file but is not a valid archive
        """
        reader = BackupReader(path)
        try:
            return self._analyze(reader, path)
        finally:
            reader.close()

    def parse_many(self, paths: Iterable[Path]) -> Iterator[BatchItemResult]:
        """Analyze multiple backups, isolating per-item failures.

        Unlike parse(), a single corrupt or missing backup does not
        abort the batch: it is reported as a failed BatchItemResult
        and processing continues with the next path. Results are
        yielded as they complete, so callers can report progress
        without waiting for the whole batch to finish.

        Args:
            paths: Backups to analyze, each a .zip file or a folder

        Returns:
            One BatchItemResult per path, in the same order
        """
        for path in paths:
            try:
                robot = self.parse(path)
            except Exception as exc:
                yield BatchItemResult(source_path=path, robot=None, error=str(exc))
            else:
                yield BatchItemResult(source_path=path, robot=robot, error=None)

    def _analyze(self, reader: BackupReader, source_path: Path) -> RobotInfo:
        warnings = WarningLog()

        model_result = self._robot_analyzer.analyze(reader, warnings)
        payloads = self._payload_analyzer.analyze(reader, warnings)
        axis_loads = self._axis_load_analyzer.analyze(reader, warnings)
        serial_number = self._controller_analyzer.detect_serial_number(reader)

        general = GeneralInfo(backup_name=self._backup_name(source_path))
        controller = ControllerInfo(
            controller_type=ControllerType.UNKNOWN, serial_number=serial_number
        )

        return RobotInfo(
            model=model_result.model,
            general=general,
            controller=controller,
            payloads=payloads,
            axis_loads=axis_loads,
            warnings=warnings,
        )

    @staticmethod
    def _backup_name(path: Path) -> str:
        if path.suffix.lower() == ".zip":
            return path.stem
        return path.name
