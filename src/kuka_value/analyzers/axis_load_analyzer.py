"""LOAD_A<n>_DATA extraction: supplementary per-axis load data."""

from __future__ import annotations

import re

from kuka_value.analyzers._common import extract_orientation, extract_vector3d, read_file_safe
from kuka_value.models.axis_load import AxisLoad
from kuka_value.models.payload import Vector3D
from kuka_value.models.warnings import WarningLog
from kuka_value.parser.backup_reader import BackupReader, FileInfo
from kuka_value.parser.krl_parser import KrlAssignment, KrlStruct, parse_assignments

# Matches LOAD_A3_DATA, $LOAD_A3_DATA, load_a12_data, etc.
_AXIS_LOAD_NAME_RE = re.compile(r"^\$?LOAD_A(\d+)_DATA$")
_AXIS_LOAD_FILE_EXTENSIONS = frozenset({".dat", ".src"})


class AxisLoadAnalyzer:
    """Extracts supplementary per-axis loads from a backup.

    Scans every .dat/.src file for DECL LOAD LOAD_A<n>_DATA={...}
    declarations (e.g. LOAD_A3_DATA for a load mounted on axis 3),
    distinct from PayloadAnalyzer's LOAD_DATA[n] (the primary flange
    payload). Unlike LOAD_DATA, there is no array index - one
    declaration per axis - so the first occurrence of a given axis
    wins if it's declared more than once across files.

    Never raises for malformed entries: records a warning and skips
    the offending entry instead.
    """

    def analyze(self, reader: BackupReader, warnings: WarningLog) -> list[AxisLoad]:
        """Extract all supplementary axis loads from a backup.

        Args:
            reader: Backup reader with indexed files
            warnings: Warning log to record extraction issues

        Returns:
            Axis loads, one per axis found, sorted by axis number
        """
        found: dict[int, AxisLoad] = {}

        for file_info in self._candidate_files(reader):
            content = read_file_safe(file_info)
            if content is None:
                continue

            for assignment in parse_assignments(content):
                axis = self._match_axis(assignment.name)
                if axis is None or axis in found:
                    continue

                axis_load = self._extract_axis_load(axis, assignment, file_info, warnings)
                if axis_load is None or axis_load.is_empty():
                    continue

                found[axis] = axis_load

        return [found[axis] for axis in sorted(found)]

    @staticmethod
    def _candidate_files(reader: BackupReader) -> list[FileInfo]:
        return [
            f for f in reader.list_files() if f.path.suffix.lower() in _AXIS_LOAD_FILE_EXTENSIONS
        ]

    @staticmethod
    def _match_axis(name: str) -> int | None:
        match = _AXIS_LOAD_NAME_RE.match(name.upper())
        if match is None:
            return None
        return int(match.group(1))

    @staticmethod
    def _extract_axis_load(
        axis: int, assignment: KrlAssignment, file_info: FileInfo, warnings: WarningLog
    ) -> AxisLoad | None:
        struct = assignment.value.as_struct()
        if struct is None:
            warnings.warn(
                f"LOAD_A{axis}_DATA corrupto: valor no es una estructura",
                source="AxisLoadAnalyzer",
            )
            return None

        mass = struct.get_float("M")
        if mass is None:
            warnings.warn(
                f"LOAD_A{axis}_DATA corrupto: falta el campo M (masa)",
                source="AxisLoadAnalyzer",
            )
            return None

        cog = AxisLoadAnalyzer._extract_center_of_gravity(axis, struct, warnings)
        inertia = extract_vector3d(struct, "J")
        orientation = extract_orientation(struct, "CM")

        return AxisLoad(
            axis=axis,
            mass=mass,
            center_of_gravity=cog,
            inertia=inertia,
            orientation=orientation,
            source_file=str(file_info.path),
        )

    @staticmethod
    def _extract_center_of_gravity(axis: int, struct: KrlStruct, warnings: WarningLog) -> Vector3D:
        cm = extract_vector3d(struct, "CM")
        if cm is None:
            warnings.warn(
                f"LOAD_A{axis}_DATA incompleto: falta CM (centro de gravedad)",
                source="AxisLoadAnalyzer",
            )
            return Vector3D.zero()
        return cm
