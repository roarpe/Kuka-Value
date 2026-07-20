"""Robot information aggregate root."""

from dataclasses import dataclass, field

from kuka_value.models.controller_info import ControllerInfo
from kuka_value.models.general_info import GeneralInfo
from kuka_value.models.payload import Payload
from kuka_value.models.warnings import WarningLog


@dataclass
class RobotInfo:
    """Aggregate root: complete analysis result for a robot backup."""

    model: str
    general: GeneralInfo
    controller: ControllerInfo
    payloads: list[Payload] = field(default_factory=list)
    warnings: WarningLog = field(default_factory=WarningLog)
