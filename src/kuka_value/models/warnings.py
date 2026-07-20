"""Warning system for non-fatal analysis issues."""

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum


class WarningLevel(Enum):
    """Severity levels for analysis warnings."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class AnalysisWarning:
    """A single warning recorded during analysis."""

    level: WarningLevel
    message: str
    source: str


class WarningLog:
    """Accumulates warnings during analysis without raising exceptions."""

    def __init__(self) -> None:
        self._warnings: list[AnalysisWarning] = []

    def info(self, message: str, *, source: str) -> None:
        self._warnings.append(
            AnalysisWarning(level=WarningLevel.INFO, message=message, source=source)
        )

    def warn(self, message: str, *, source: str) -> None:
        self._warnings.append(
            AnalysisWarning(level=WarningLevel.WARNING, message=message, source=source)
        )

    def error(self, message: str, *, source: str) -> None:
        self._warnings.append(
            AnalysisWarning(level=WarningLevel.ERROR, message=message, source=source)
        )

    def has_errors(self) -> bool:
        return any(w.level == WarningLevel.ERROR for w in self._warnings)

    def get_by_level(self, level: WarningLevel) -> list[AnalysisWarning]:
        return [w for w in self._warnings if w.level == level]

    def __len__(self) -> int:
        return len(self._warnings)

    def __iter__(self) -> Iterator[AnalysisWarning]:
        return iter(self._warnings)
