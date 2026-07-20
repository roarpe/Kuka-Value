"""Shared parser for RobotInfo.xml.

Real KUKA backups often keep robot type and serial number together in
a single small XML file at C/KRC/Roboter/Rdc/RobotInfo.xml - a much
more reliable source than parsing KRL variable assignments (TRAFONAME,
$ROBOT_TYPE, ...), which can be arrays with several slots and no
guarantee the first match is the active one.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from kuka_value.analyzers._common import read_file_safe
from kuka_value.parser.backup_reader import BackupReader, FileInfo


@dataclass(frozen=True)
class RobotInfoXmlData:
    """Values extracted from RobotInfo.xml, if present."""

    robot_type: str | None
    serial_number: str | None


def find_robot_info_xml(reader: BackupReader) -> RobotInfoXmlData | None:
    """Locate and parse RobotInfo.xml anywhere in the backup.

    Searches by filename only (case-insensitive), so it's found
    regardless of the backup's exact root layout.

    Args:
        reader: Backup reader with indexed files

    Returns:
        Extracted data, or None if no readable/parseable RobotInfo.xml
        with at least one recognized field was found
    """
    files = reader.list_files()
    candidates = [f for f in files if f.path.name.lower() == "robotinfo.xml"]

    for file_info in candidates:
        data = _parse(file_info)
        if data is not None:
            return data

    return None


def _parse(file_info: FileInfo) -> RobotInfoXmlData | None:
    content = read_file_safe(file_info)
    if content is None:
        return None

    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return None

    robot_type = _find_tag_text(root, "RobotType")
    serial_number = _find_tag_text(root, "SerialNumber")

    if robot_type is None and serial_number is None:
        return None

    return RobotInfoXmlData(robot_type=robot_type, serial_number=serial_number)


def _find_tag_text(root: ET.Element, tag: str) -> str | None:
    """Find the first element matching `tag`, tolerating XML namespaces."""
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1]  # strip {namespace} prefix
        if local_name == tag and element.text:
            text = element.text.strip()
            if text:
                return text
    return None
