"""CSV export for robot analysis results."""

from __future__ import annotations

import csv
import io

from kuka_value.exporters.base import Exporter
from kuka_value.models.axis_load import AxisLoad
from kuka_value.models.payload import Payload
from kuka_value.models.robot_info import RobotInfo

PAYLOAD_HEADERS = [
    "Index(es)",
    "Mass (kg)",
    "CoG X (mm)",
    "CoG Y (mm)",
    "CoG Z (mm)",
    "Inertia X (kgm2)",
    "Inertia Y (kgm2)",
    "Inertia Z (kgm2)",
    "Source File",
]

AXIS_LOAD_HEADERS = [
    "Axis",
    "Mass (kg)",
    "CoG X (mm)",
    "CoG Y (mm)",
    "CoG Z (mm)",
    "Inertia X (kgm2)",
    "Inertia Y (kgm2)",
    "Inertia Z (kgm2)",
    "Source File",
]


class CsvExporter(Exporter):
    """Exports a robot analysis result as CSV.

    Layout: a short metadata block (model, backup name, controller,
    warning count), a blank separator line, the unique-payload table,
    another blank separator, then the axis-loads table (if any).
    """

    def export(self, robot: RobotInfo) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(["Model", robot.model])
        writer.writerow(["Backup Name", robot.general.backup_name])
        writer.writerow(["KSS Version", robot.general.kss_version or ""])
        writer.writerow(["Controller Type", robot.controller.controller_type.value])
        writer.writerow(["Serial Number", robot.controller.serial_number or ""])
        writer.writerow(["Warnings", len(robot.warnings)])
        writer.writerow([])

        writer.writerow(PAYLOAD_HEADERS)
        for payload in robot.payloads:
            writer.writerow(self.payload_row(payload))
        writer.writerow([])

        writer.writerow(AXIS_LOAD_HEADERS)
        for axis_load in robot.axis_loads:
            writer.writerow(self.axis_load_row(axis_load))

        # utf-8-sig: BOM so Excel opens non-ASCII content correctly
        return buffer.getvalue().encode("utf-8-sig")

    @staticmethod
    def payload_row(payload: Payload) -> list[str | float]:
        inertia = payload.inertia
        return [
            ", ".join(str(i) for i in payload.indices),
            payload.mass,
            payload.center_of_gravity.x,
            payload.center_of_gravity.y,
            payload.center_of_gravity.z,
            inertia.x if inertia else "",
            inertia.y if inertia else "",
            inertia.z if inertia else "",
            payload.source_file or "",
        ]

    @staticmethod
    def axis_load_row(axis_load: AxisLoad) -> list[str | float | int]:
        inertia = axis_load.inertia
        return [
            axis_load.axis,
            axis_load.mass,
            axis_load.center_of_gravity.x,
            axis_load.center_of_gravity.y,
            axis_load.center_of_gravity.z,
            inertia.x if inertia else "",
            inertia.y if inertia else "",
            inertia.z if inertia else "",
            axis_load.source_file or "",
        ]
