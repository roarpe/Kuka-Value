"""JSON export for robot analysis results."""

from __future__ import annotations

import json
from typing import Any

from kuka_value.exporters.base import Exporter
from kuka_value.models.axis_load import AxisLoad
from kuka_value.models.payload import Payload, Vector3D
from kuka_value.models.robot_info import RobotInfo
from kuka_value.models.warnings import AnalysisWarning


class JsonExporter(Exporter):
    """Exports a robot analysis result as JSON, preserving full fidelity.

    Unlike CSV/Excel (human-facing tables), this format is meant for
    programmatic consumption, so every field on RobotInfo is included,
    including the full warning log.
    """

    def export(self, robot: RobotInfo) -> bytes:
        data = self.robot_dict(robot)
        return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def robot_dict(robot: RobotInfo) -> dict[str, Any]:
        """Build the full-fidelity dict representation of one robot.

        Shared with BatchJsonExporter so a batch's JSON output is
        exactly an array of what single-robot export() would produce
        per item, plus batch-only fields.
        """
        return {
            "model": robot.model,
            "general": {
                "backup_name": robot.general.backup_name,
                "kss_version": robot.general.kss_version,
            },
            "controller": {
                "controller_type": robot.controller.controller_type.value,
                "serial_number": robot.controller.serial_number,
            },
            "payloads": [JsonExporter._payload_dict(p) for p in robot.payloads],
            "axis_loads": [JsonExporter._axis_load_dict(a) for a in robot.axis_loads],
            "warnings": [JsonExporter._warning_dict(w) for w in robot.warnings],
        }

    @staticmethod
    def _vector_dict(vector: Vector3D | None) -> dict[str, float] | None:
        if vector is None:
            return None
        return {"x": vector.x, "y": vector.y, "z": vector.z}

    @staticmethod
    def _payload_dict(payload: Payload) -> dict[str, Any]:
        return {
            "mass": payload.mass,
            "center_of_gravity": JsonExporter._vector_dict(payload.center_of_gravity),
            "inertia": JsonExporter._vector_dict(payload.inertia),
            "indices": payload.indices,
            "source_file": payload.source_file,
        }

    @staticmethod
    def _axis_load_dict(axis_load: AxisLoad) -> dict[str, Any]:
        return {
            "axis": axis_load.axis,
            "mass": axis_load.mass,
            "center_of_gravity": JsonExporter._vector_dict(axis_load.center_of_gravity),
            "inertia": JsonExporter._vector_dict(axis_load.inertia),
            "source_file": axis_load.source_file,
        }

    @staticmethod
    def _warning_dict(warning: AnalysisWarning) -> dict[str, str]:
        return {
            "level": warning.level.value,
            "message": warning.message,
            "source": warning.source,
        }
