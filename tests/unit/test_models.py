"""Unit tests for domain models."""

import pytest

from kuka_value.models.controller_info import ControllerInfo, ControllerType
from kuka_value.models.general_info import GeneralInfo
from kuka_value.models.payload import Payload, Vector3D
from kuka_value.models.robot_info import RobotInfo
from kuka_value.models.warnings import AnalysisWarning, WarningLevel, WarningLog


class TestVector3D:
    """Test Vector3D value object."""

    def test_create_vector(self) -> None:
        v = Vector3D(x=1.0, y=2.0, z=3.0)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0

    def test_vector_is_frozen(self) -> None:
        v = Vector3D(x=1.0, y=2.0, z=3.0)
        try:
            v.x = 5.0  # type: ignore[misc]
            pytest.fail("Should not allow mutation")
        except AttributeError:
            pass

    def test_vector_equality(self) -> None:
        v1 = Vector3D(x=1.0, y=2.0, z=3.0)
        v2 = Vector3D(x=1.0, y=2.0, z=3.0)
        assert v1 == v2

    def test_vector_zero(self) -> None:
        v = Vector3D.zero()
        assert v.x == 0.0
        assert v.y == 0.0
        assert v.z == 0.0

    def test_vector_is_zero(self) -> None:
        assert Vector3D.zero().is_zero()
        assert not Vector3D(x=1.0, y=0.0, z=0.0).is_zero()


class TestPayload:
    """Test Payload dataclass."""

    def test_create_payload(self) -> None:
        p = Payload(
            mass=10.5,
            center_of_gravity=Vector3D(x=100.0, y=0.0, z=50.0),
        )
        assert p.mass == 10.5
        assert p.center_of_gravity.x == 100.0
        assert p.inertia is None

    def test_payload_with_inertia(self) -> None:
        p = Payload(
            mass=25.0,
            center_of_gravity=Vector3D(x=0.0, y=0.0, z=100.0),
            inertia=Vector3D(x=0.5, y=0.5, z=0.3),
        )
        assert p.inertia is not None
        assert p.inertia.x == 0.5

    def test_payload_with_indices(self) -> None:
        p = Payload(
            mass=10.0,
            center_of_gravity=Vector3D.zero(),
            indices=[1, 3, 7],
        )
        assert p.indices == [1, 3, 7]

    def test_payload_is_empty_negative_mass(self) -> None:
        p = Payload(mass=-1.0, center_of_gravity=Vector3D.zero())
        assert p.is_empty()

    def test_payload_is_empty_zero_mass(self) -> None:
        p = Payload(mass=0.0, center_of_gravity=Vector3D.zero())
        assert p.is_empty()

    def test_payload_is_not_empty(self) -> None:
        p = Payload(mass=5.0, center_of_gravity=Vector3D.zero())
        assert not p.is_empty()

    def test_payload_equality_by_values(self) -> None:
        """Two payloads with same mass/cog/inertia should be equal regardless of indices."""
        p1 = Payload(
            mass=10.0,
            center_of_gravity=Vector3D(x=1.0, y=2.0, z=3.0),
            indices=[1],
        )
        p2 = Payload(
            mass=10.0,
            center_of_gravity=Vector3D(x=1.0, y=2.0, z=3.0),
            indices=[5],
        )
        assert p1.same_payload(p2)

    def test_payload_not_equal_different_mass(self) -> None:
        p1 = Payload(mass=10.0, center_of_gravity=Vector3D.zero())
        p2 = Payload(mass=20.0, center_of_gravity=Vector3D.zero())
        assert not p1.same_payload(p2)

    def test_payload_not_equal_different_cog(self) -> None:
        p1 = Payload(mass=10.0, center_of_gravity=Vector3D(x=1.0, y=0.0, z=0.0))
        p2 = Payload(mass=10.0, center_of_gravity=Vector3D(x=2.0, y=0.0, z=0.0))
        assert not p1.same_payload(p2)

    def test_payload_merge_indices(self) -> None:
        """Merging should combine indices from duplicate payloads."""
        p1 = Payload(
            mass=10.0,
            center_of_gravity=Vector3D(x=1.0, y=2.0, z=3.0),
            indices=[1, 3],
        )
        p2 = Payload(
            mass=10.0,
            center_of_gravity=Vector3D(x=1.0, y=2.0, z=3.0),
            indices=[5, 7],
        )
        merged = p1.merge_indices(p2)
        assert merged.indices == [1, 3, 5, 7]
        assert merged.mass == 10.0

    def test_payload_source_file(self) -> None:
        p = Payload(
            mass=10.0,
            center_of_gravity=Vector3D.zero(),
            source_file="R1/MADA/$config.dat",
        )
        assert p.source_file == "R1/MADA/$config.dat"


class TestControllerInfo:
    """Test ControllerInfo dataclass."""

    def test_create_controller_info(self) -> None:
        c = ControllerInfo(
            controller_type=ControllerType.KRC4,
            serial_number="123456",
        )
        assert c.controller_type == ControllerType.KRC4
        assert c.serial_number == "123456"

    def test_controller_type_enum(self) -> None:
        assert ControllerType.KRC2.value == "KRC2"
        assert ControllerType.KRC4.value == "KRC4"
        assert ControllerType.KRC5.value == "KRC5"

    def test_controller_unknown(self) -> None:
        c = ControllerInfo(controller_type=ControllerType.UNKNOWN)
        assert c.controller_type == ControllerType.UNKNOWN
        assert c.serial_number is None

    def test_controller_is_frozen(self) -> None:
        c = ControllerInfo(controller_type=ControllerType.KRC4)
        try:
            c.serial_number = "changed"  # type: ignore[misc]
            pytest.fail("Should not allow mutation")
        except AttributeError:
            pass


class TestGeneralInfo:
    """Test GeneralInfo dataclass."""

    def test_create_general_info(self) -> None:
        g = GeneralInfo(backup_name="MyRobot_2024-01-15")
        assert g.backup_name == "MyRobot_2024-01-15"

    def test_general_info_with_kss_version(self) -> None:
        g = GeneralInfo(
            backup_name="Robot1",
            kss_version="8.6.8",
        )
        assert g.kss_version == "8.6.8"

    def test_general_info_is_frozen(self) -> None:
        g = GeneralInfo(backup_name="test")
        try:
            g.backup_name = "changed"  # type: ignore[misc]
            pytest.fail("Should not allow mutation")
        except AttributeError:
            pass


class TestWarningLog:
    """Test warning system."""

    def test_create_warning(self) -> None:
        w = AnalysisWarning(
            level=WarningLevel.WARNING,
            message="MACHINE.DAT not found",
            source="RobotAnalyzer",
        )
        assert w.level == WarningLevel.WARNING
        assert w.message == "MACHINE.DAT not found"

    def test_warning_log_empty(self) -> None:
        log = WarningLog()
        assert len(log) == 0
        assert not log.has_errors()

    def test_warning_log_add(self) -> None:
        log = WarningLog()
        log.warn("Missing file", source="Parser")
        assert len(log) == 1

    def test_warning_log_convenience_methods(self) -> None:
        log = WarningLog()
        log.info("Started analysis", source="Engine")
        log.warn("Incomplete data", source="Analyzer")
        log.error("Corrupt file", source="Parser")

        assert len(log) == 3
        assert log.has_errors()

    def test_warning_log_filter_by_level(self) -> None:
        log = WarningLog()
        log.info("info1", source="A")
        log.warn("warn1", source="B")
        log.warn("warn2", source="C")
        log.error("err1", source="D")

        warnings = log.get_by_level(WarningLevel.WARNING)
        assert len(warnings) == 2

        errors = log.get_by_level(WarningLevel.ERROR)
        assert len(errors) == 1

    def test_warning_log_iterable(self) -> None:
        log = WarningLog()
        log.warn("w1", source="A")
        log.warn("w2", source="B")

        messages = [w.message for w in log]
        assert messages == ["w1", "w2"]


class TestRobotInfo:
    """Test RobotInfo aggregate root."""

    def test_create_robot_info(self) -> None:
        robot = RobotInfo(
            model="KR 240 R2900",
            general=GeneralInfo(backup_name="Backup_001"),
            controller=ControllerInfo(controller_type=ControllerType.KRC4),
        )
        assert robot.model == "KR 240 R2900"
        assert robot.general.backup_name == "Backup_001"
        assert robot.controller.controller_type == ControllerType.KRC4

    def test_robot_info_with_payloads(self) -> None:
        payloads = [
            Payload(mass=10.0, center_of_gravity=Vector3D.zero(), indices=[1]),
            Payload(mass=25.0, center_of_gravity=Vector3D(x=50.0, y=0.0, z=100.0), indices=[3]),
        ]
        robot = RobotInfo(
            model="KR 210 R2700",
            general=GeneralInfo(backup_name="test"),
            controller=ControllerInfo(controller_type=ControllerType.KRC2),
            payloads=payloads,
        )
        assert len(robot.payloads) == 2
        assert robot.payloads[0].mass == 10.0

    def test_robot_info_empty_payloads_default(self) -> None:
        robot = RobotInfo(
            model="KR 6 R900",
            general=GeneralInfo(backup_name="test"),
            controller=ControllerInfo(controller_type=ControllerType.KRC4),
        )
        assert robot.payloads == []

    def test_robot_info_warnings_default(self) -> None:
        robot = RobotInfo(
            model="KR 6 R900",
            general=GeneralInfo(backup_name="test"),
            controller=ControllerInfo(controller_type=ControllerType.KRC4),
        )
        assert len(robot.warnings) == 0

    def test_robot_info_with_warnings(self) -> None:
        warnings = WarningLog()
        warnings.warn("LOAD_DATA corrupto", source="PayloadAnalyzer")

        robot = RobotInfo(
            model="KR 6 R900",
            general=GeneralInfo(backup_name="test"),
            controller=ControllerInfo(controller_type=ControllerType.KRC4),
            warnings=warnings,
        )
        assert len(robot.warnings) == 1
        assert not robot.warnings.has_errors()
