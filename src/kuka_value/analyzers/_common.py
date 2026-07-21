"""Shared utilities for analyzer modules."""

from __future__ import annotations

import logging

from kuka_value.models.payload import Orientation, Vector3D
from kuka_value.parser.backup_reader import FileInfo
from kuka_value.parser.krl_parser import KrlStruct

logger = logging.getLogger(__name__)


def read_file_safe(file_info: FileInfo) -> str | None:
    """Read file content, returning None on any I/O error.

    Args:
        file_info: File to read (must have absolute_path set)

    Returns:
        Decoded text content, or None if unreadable
    """
    if file_info.absolute_path is None or not file_info.absolute_path.exists():
        return None
    try:
        return file_info.absolute_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        logger.debug("Could not read file: %s", file_info.path)
        return None


def extract_vector3d(struct: KrlStruct, field_name: str) -> Vector3D | None:
    """Extract an X/Y/Z vector sub-struct (e.g. CM or J) from a KRL struct.

    Missing X/Y/Z components within a present sub-struct default to
    0.0 (partial vectors are common and not treated as an error here -
    callers decide whether a missing sub-struct entirely is warning-
    worthy).

    Args:
        struct: Parent struct (e.g. the LOAD_DATA/LOAD_A<n>_DATA value)
        field_name: Sub-struct field name, e.g. "CM" or "J"

    Returns:
        The vector, or None if `field_name` is absent
    """
    sub = struct.get_struct(field_name)
    if sub is None:
        return None
    return Vector3D(
        x=sub.get_float("X") or 0.0,
        y=sub.get_float("Y") or 0.0,
        z=sub.get_float("Z") or 0.0,
    )


def extract_orientation(struct: KrlStruct, field_name: str) -> Orientation | None:
    """Extract an A/B/C orientation sub-struct (e.g. CM) from a KRL struct.

    Missing A/B/C components within a present sub-struct default to
    0.0, mirroring extract_vector3d's handling of partial vectors.

    Args:
        struct: Parent struct (e.g. the LOAD_DATA/LOAD_A<n>_DATA value)
        field_name: Sub-struct field name, e.g. "CM"

    Returns:
        The orientation, or None if `field_name` is absent
    """
    sub = struct.get_struct(field_name)
    if sub is None:
        return None
    return Orientation(
        a=sub.get_float("A") or 0.0,
        b=sub.get_float("B") or 0.0,
        c=sub.get_float("C") or 0.0,
    )
