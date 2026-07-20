"""Shared utilities for analyzer modules."""

from __future__ import annotations

import logging

from kuka_value.parser.backup_reader import FileInfo

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
