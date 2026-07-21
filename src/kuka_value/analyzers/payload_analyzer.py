"""LOAD_DATA extraction and duplicate payload detection."""

from __future__ import annotations

from kuka_value.analyzers._common import extract_orientation, extract_vector3d, read_file_safe
from kuka_value.models.payload import Payload, Vector3D
from kuka_value.models.warnings import WarningLog
from kuka_value.parser.backup_reader import BackupReader, FileInfo
from kuka_value.parser.krl_parser import KrlAssignment, KrlStruct, parse_assignments

_LOAD_DATA_NAMES = frozenset({"LOAD_DATA", "$LOAD_DATA"})
_PAYLOAD_FILE_EXTENSIONS = frozenset({".dat", ".src"})


class PayloadAnalyzer:
    """Extracts unique payloads from LOAD_DATA structures across a backup.

    Scans every .dat/.src file for LOAD_DATA assignments (both the
    system-variable form $LOAD_DATA[n]=... and the DECL form
    DECL LOAD_DATA LOAD_DATA[n]=...), extracts mass/center-of-gravity/
    inertia, discards empty slots (M <= 0), and merges duplicate
    payloads while preserving every index where they occur.

    Never raises for malformed entries: records a warning and skips
    the offending entry instead.
    """

    def analyze(self, reader: BackupReader, warnings: WarningLog) -> list[Payload]:
        """Extract all unique payloads from a backup.

        Args:
            reader: Backup reader with indexed files
            warnings: Warning log to record extraction issues

        Returns:
            Deduplicated list of payloads, each with all indices where
            an identical payload was found
        """
        raw_payloads: list[Payload] = []

        for file_info in self._candidate_files(reader):
            content = read_file_safe(file_info)
            if content is None:
                continue

            for assignment in parse_assignments(content):
                if assignment.name.upper() not in _LOAD_DATA_NAMES:
                    continue

                payload = self._extract_payload(assignment, file_info, warnings)
                if payload is None or payload.is_empty():
                    continue

                raw_payloads.append(payload)

        return self._deduplicate(raw_payloads)

    @staticmethod
    def _candidate_files(reader: BackupReader) -> list[FileInfo]:
        return [f for f in reader.list_files() if f.path.suffix.lower() in _PAYLOAD_FILE_EXTENSIONS]

    @staticmethod
    def _extract_payload(
        assignment: KrlAssignment, file_info: FileInfo, warnings: WarningLog
    ) -> Payload | None:
        struct = assignment.value.as_struct()
        if struct is None:
            warnings.warn(
                "LOAD_DATA corrupto: valor no es una estructura", source="PayloadAnalyzer"
            )
            return None

        mass = struct.get_float("M")
        if mass is None:
            warnings.warn("LOAD_DATA corrupto: falta el campo M (masa)", source="PayloadAnalyzer")
            return None

        if assignment.index is None:
            warnings.warn("LOAD_DATA corrupto: falta el índice del array", source="PayloadAnalyzer")
            return None

        cog = PayloadAnalyzer._extract_center_of_gravity(struct, warnings)
        inertia = PayloadAnalyzer._extract_inertia(struct)
        orientation = extract_orientation(struct, "CM")

        return Payload(
            mass=mass,
            center_of_gravity=cog,
            inertia=inertia,
            orientation=orientation,
            indices=[assignment.index],
            source_file=str(file_info.path),
        )

    @staticmethod
    def _extract_center_of_gravity(struct: KrlStruct, warnings: WarningLog) -> Vector3D:
        cm = extract_vector3d(struct, "CM")
        if cm is None:
            warnings.warn(
                "Payload incompleto: falta CM (centro de gravedad)", source="PayloadAnalyzer"
            )
            return Vector3D.zero()
        return cm

    @staticmethod
    def _extract_inertia(struct: KrlStruct) -> Vector3D | None:
        return extract_vector3d(struct, "J")

    @staticmethod
    def _deduplicate(payloads: list[Payload]) -> list[Payload]:
        unique: list[Payload] = []

        for payload in payloads:
            for i, existing in enumerate(unique):
                if existing.same_payload(payload):
                    unique[i] = existing.merge_indices(payload)
                    break
            else:
                unique.append(payload)

        return unique
