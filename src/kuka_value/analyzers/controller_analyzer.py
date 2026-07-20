"""Controller info detection (currently: serial number only)."""

from __future__ import annotations

import re

from kuka_value.analyzers._common import read_file_safe
from kuka_value.analyzers.robot_info_xml import find_robot_info_xml
from kuka_value.parser.backup_reader import BackupReader

# Files larger than this are skipped during the broad fallback scan, to
# avoid wasting time decoding large binary artifacts.
_MAX_FALLBACK_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

_AM_INI_SERIAL_RE = re.compile(r"IRSerialNr\s*=\s*(\S+)", re.IGNORECASE)

_FALLBACK_KEYWORDS = ("SerialNumber", "IRSerialNr", "RobotSerialNumber", "RobotSerial")
_FALLBACK_RE = re.compile(
    r"(?:" + "|".join(_FALLBACK_KEYWORDS) + r")\s*[=:]?\s*[\"']?([A-Za-z0-9_-]+)[\"']?",
    re.IGNORECASE,
)
_FALLBACK_EXTENSIONS = frozenset({".xml", ".ini", ".cfg", ".dat"})


class ControllerAnalyzer:
    """Detects the robot's serial number from backup files.

    Detection strategy, in priority order:
        1. <SerialNumber> in RobotInfo.xml
        2. IRSerialNr= in am.ini
        3. Broad search across text files for known serial-number keywords

    Never raises: a missing serial number is common (not every backup
    includes RobotInfo.xml or am.ini), so it's simply left as None
    rather than treated as a warning-worthy anomaly.
    """

    def detect_serial_number(self, reader: BackupReader) -> str | None:
        """Detect the robot's serial number from a backup.

        Args:
            reader: Backup reader with indexed files

        Returns:
            Serial number if found, else None
        """
        xml_data = find_robot_info_xml(reader)
        if xml_data is not None and xml_data.serial_number:
            return xml_data.serial_number

        files = reader.list_files()

        for file_info in files:
            if file_info.path.name.lower() != "am.ini":
                continue
            content = read_file_safe(file_info)
            if content is None:
                continue
            match = _AM_INI_SERIAL_RE.search(content)
            if match:
                return match.group(1)

        for file_info in files:
            if file_info.size > _MAX_FALLBACK_FILE_SIZE:
                continue
            if file_info.path.suffix.lower() not in _FALLBACK_EXTENSIONS:
                continue
            content = read_file_safe(file_info)
            if content is None:
                continue
            match = _FALLBACK_RE.search(content)
            if match:
                return match.group(1)

        return None
