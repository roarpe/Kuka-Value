"""Excel (.xlsx) export for robot analysis results."""

from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Font

from kuka_value.exporters.base import Exporter
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

_BOLD = Font(bold=True)


class ExcelExporter(Exporter):
    """Exports a robot analysis result as a formatted .xlsx workbook.

    Produces two sheets: "Summary" (model/backup/controller metadata)
    and "Payloads" (the unique-payload table).
    """

    def export(self, robot: RobotInfo) -> bytes:
        workbook = Workbook()
        self._write_summary_sheet(workbook, robot)
        self._write_payloads_sheet(workbook, robot)

        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def _write_summary_sheet(workbook: Workbook, robot: RobotInfo) -> None:
        sheet = workbook.active
        assert sheet is not None
        sheet.title = "Summary"

        rows: list[tuple[str, str | int]] = [
            ("Model", robot.model),
            ("Backup Name", robot.general.backup_name),
            ("KSS Version", robot.general.kss_version or ""),
            ("Controller Type", robot.controller.controller_type.value),
            ("Serial Number", robot.controller.serial_number or ""),
            ("Unique Payloads", len(robot.payloads)),
            ("Warnings", len(robot.warnings)),
        ]
        for row in rows:
            sheet.append(row)

        for cell in sheet["A"]:
            cell.font = _BOLD

    @staticmethod
    def _write_payloads_sheet(workbook: Workbook, robot: RobotInfo) -> None:
        sheet = workbook.create_sheet("Payloads")
        sheet.append(PAYLOAD_HEADERS)
        for cell in sheet[1]:
            cell.font = _BOLD

        for payload in robot.payloads:
            sheet.append(ExcelExporter.payload_row(payload))

    @staticmethod
    def payload_row(payload: Payload) -> list[str | float | None]:
        inertia = payload.inertia
        return [
            ", ".join(str(i) for i in payload.indices),
            payload.mass,
            payload.center_of_gravity.x,
            payload.center_of_gravity.y,
            payload.center_of_gravity.z,
            inertia.x if inertia else None,
            inertia.y if inertia else None,
            inertia.z if inertia else None,
            payload.source_file or "",
        ]
