"""Controller information model."""

from dataclasses import dataclass
from enum import Enum


class ControllerType(Enum):
    """KUKA controller generations."""

    KRC2 = "KRC2"
    KRC4 = "KRC4"
    KRC5 = "KRC5"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ControllerInfo:
    """Controller identification and metadata."""

    controller_type: ControllerType
    serial_number: str | None = None
