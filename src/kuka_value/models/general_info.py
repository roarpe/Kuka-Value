"""General backup metadata."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GeneralInfo:
    """High-level metadata about the backup."""

    backup_name: str
    kss_version: str | None = None
