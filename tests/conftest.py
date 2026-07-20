"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

# Add src to path so we can import kuka_value
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest  # noqa: E402

from kuka_value.models.controller_info import ControllerInfo, ControllerType  # noqa: E402
from kuka_value.models.general_info import GeneralInfo  # noqa: E402
from kuka_value.models.payload import Payload, Vector3D  # noqa: E402
from kuka_value.models.robot_info import RobotInfo  # noqa: E402
from kuka_value.models.warnings import WarningLog  # noqa: E402


@pytest.fixture
def sample_robot_info() -> RobotInfo:
    """A representative RobotInfo with payloads (with/without inertia),
    a warning, and full controller/general metadata - shared across
    exporter tests so each doesn't need to rebuild this fixture."""
    warnings = WarningLog()
    warnings.warn("Payload incompleto: falta CM (centro de gravedad)", source="PayloadAnalyzer")

    payloads = [
        Payload(
            mass=10.5,
            center_of_gravity=Vector3D(x=100.0, y=0.0, z=50.0),
            inertia=Vector3D(x=0.5, y=0.5, z=0.3),
            indices=[1, 3],
            source_file="$config.dat",
        ),
        Payload(
            mass=25.0,
            center_of_gravity=Vector3D(x=0.0, y=0.0, z=0.0),
            inertia=None,
            indices=[2],
            source_file="$config2.dat",
        ),
    ]

    return RobotInfo(
        model="KR 240 R2900",
        general=GeneralInfo(backup_name="TestBackup", kss_version="8.6.8"),
        controller=ControllerInfo(controller_type=ControllerType.KRC4, serial_number="12345"),
        payloads=payloads,
        warnings=warnings,
    )
