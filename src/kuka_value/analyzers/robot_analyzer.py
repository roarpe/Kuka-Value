"""Robot model detection and name normalization."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from kuka_value.analyzers._common import read_file_safe
from kuka_value.models.warnings import WarningLog
from kuka_value.parser.backup_reader import BackupReader, FileInfo
from kuka_value.parser.krl_parser import KrlValue, parse_assignments

# Files larger than this are skipped during the broad (priority 4) fallback
# scan, to avoid wasting time decoding large binary artifacts.
_MAX_FALLBACK_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# KR<payload><reach>[-<variant_digit>][<suffix letters>]
# e.g. "KR240R2900" -> KR / 240 / R2900
#      "KR270R3100-2K" -> KR / 270 / R3100-2 / K
_MODEL_NAME_RE = re.compile(r"^([A-Z]+)(\d+)(R\d+(?:-\d+)?)([A-Z]+)?$")

_TRAFONAME_VARS = frozenset({"$TRAFONAME"})
_MACHINE_DAT_VARS = frozenset({"$ROBOT_TYPE", "$ROBOT_MODEL"})
_ROBCOR_VARS = frozenset({"$ROBCOR_NAME", "$ROBCOR_TYPE"})


class ModelSource(Enum):
    """Where the robot model was identified from."""

    TRAFONAME = "TRAFONAME"
    MACHINE_DAT = "MACHINE_DAT"
    ROBCOR = "ROBCOR"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ModelDetectionResult:
    """Result of robot model detection."""

    model: str
    raw_value: str
    source: ModelSource


class RobotAnalyzer:
    """Detects robot model from backup files.

    Detection strategy, in priority order:
        1. $TRAFONAME in a MACHINE.DAT-like file
        2. $ROBOT_TYPE / $ROBOT_MODEL in a MACHINE.DAT-like file
        3. $ROBCOR_NAME / $ROBCOR_TYPE in a ROBCOR-like file
        4. Broad search across all files (last resort)

    Never raises for missing or malformed data: records a warning and
    returns ModelSource.UNKNOWN instead.
    """

    def analyze(self, reader: BackupReader, warnings: WarningLog) -> ModelDetectionResult:
        """Detect the robot model from a backup.

        Args:
            reader: Backup reader with indexed files
            warnings: Warning log to record detection issues

        Returns:
            Detected model with source and raw value
        """
        files = reader.list_files()

        strategies: list[tuple[str, frozenset[str], ModelSource]] = [
            ("MACHINE", _TRAFONAME_VARS, ModelSource.TRAFONAME),
            ("MACHINE", _MACHINE_DAT_VARS, ModelSource.MACHINE_DAT),
            ("ROBCOR", _ROBCOR_VARS, ModelSource.ROBCOR),
        ]

        for keyword, var_names, source in strategies:
            found = self._search_files(files, keyword, var_names)
            if found is not None:
                return self._build_result(found, source)

        # Priority 4: broad fallback, no filename restriction
        for _keyword, var_names, source in strategies:
            found = self._search_files(files, "", var_names, size_limited=True)
            if found is not None:
                return self._build_result(found, source)

        warnings.warn(
            "Could not determine robot model: TRAFONAME, MACHINE.DAT and "
            "ROBCOR were all missing, unreadable, or did not contain a "
            "recognizable model identifier.",
            source="RobotAnalyzer",
        )
        return ModelDetectionResult(model="UNKNOWN", raw_value="", source=ModelSource.UNKNOWN)

    def _build_result(self, raw_value: str, source: ModelSource) -> ModelDetectionResult:
        # TRAFONAME values sometimes carry an axis-config suffix, e.g.
        # "KR240R2900#A1" - strip it before normalizing.
        clean_value = raw_value.split("#")[0].strip()
        return ModelDetectionResult(
            model=self.normalize_model_name(clean_value),
            raw_value=clean_value,
            source=source,
        )

    def _search_files(
        self,
        files: list[FileInfo],
        keyword: str,
        var_names: frozenset[str],
        *,
        size_limited: bool = False,
    ) -> str | None:
        """Search files whose name contains keyword for any of var_names.

        Args:
            files: Files to search
            keyword: Case-insensitive substring to match in filename
                (empty string matches all files)
            var_names: KRL variable names to look for
            size_limited: If True, skip files larger than the fallback
                size threshold

        Returns:
            Raw extracted value, or None if not found
        """
        candidates = [f for f in files if keyword.upper() in f.path.name.upper()]

        for file_info in candidates:
            if size_limited and file_info.size > _MAX_FALLBACK_FILE_SIZE:
                continue

            content = read_file_safe(file_info)
            if content is None:
                continue

            value = self._extract_variable(content, var_names)
            if value is not None:
                return value

        return None

    @staticmethod
    def _extract_variable(content: str, var_names: frozenset[str]) -> str | None:
        """Find the first assignment matching var_names and extract its value."""
        for assignment in parse_assignments(content):
            if assignment.name.upper() in var_names:
                value = RobotAnalyzer._value_as_model_string(assignment.value)
                if value:
                    return value
        return None

    @staticmethod
    def _value_as_model_string(value: KrlValue) -> str | None:
        """Extract a raw model identifier from a string or enum KRL value."""
        string_val = value.as_string()
        if string_val:
            return string_val

        enum_val = value.as_enum()
        if enum_val:
            return enum_val.replace("_", "")

        return None

    @staticmethod
    def normalize_model_name(raw: str) -> str:
        """Normalize a compact robot model name into its spaced form.

        Examples:
            KR240R2900       -> KR 240 R2900
            KR270R3100-2K    -> KR 270 R3100-2 K

        Names that don't match the expected pattern (including names
        that are already normalized) are returned unchanged.

        Args:
            raw: Raw model identifier

        Returns:
            Normalized model name
        """
        candidate = raw.strip()
        match = _MODEL_NAME_RE.match(candidate.upper())
        if not match:
            return candidate

        prefix, payload, reach, variant = match.groups()
        parts = [prefix, payload, reach]
        if variant:
            parts.append(variant)
        return " ".join(parts)
