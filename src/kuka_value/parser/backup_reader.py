"""Backup reader for ZIP and folder inputs with file indexing."""

import contextlib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile


@dataclass
class FileInfo:
    """Information about a single file in backup."""

    path: Path  # Relative path from backup root
    size: int
    absolute_path: Path | None = None  # For reading file content


class FileIndex:
    """Single-pass index of backup files."""

    def __init__(self, files: list[FileInfo]) -> None:
        """Initialize file index.

        Args:
            files: List of FileInfo objects
        """
        self.files = files
        self._name_map: dict[str, FileInfo] = {f.path.name: f for f in files}
        self._dir_map: dict[str, list[FileInfo]] = self._build_dir_map()

    @staticmethod
    def build(backup_path: Path) -> "FileIndex":
        """Build index by traversing directory exactly once.

        Args:
            backup_path: Path to backup directory

        Returns:
            FileIndex with all files indexed

        Raises:
            FileNotFoundError: If path doesn't exist
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup path not found: {backup_path}")

        files: list[FileInfo] = []
        for file_path in backup_path.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(backup_path)
                files.append(
                    FileInfo(
                        path=rel_path,
                        size=file_path.stat().st_size,
                        absolute_path=file_path,
                    )
                )

        return FileIndex(files)

    def _build_dir_map(self) -> dict[str, list[FileInfo]]:
        """Build directory-to-files mapping."""
        dir_map: dict[str, list[FileInfo]] = {}

        for file_info in self.files:
            parent = file_info.path.parent.name
            if parent not in dir_map:
                dir_map[parent] = []
            dir_map[parent].append(file_info)

        return dir_map

    def get_by_name(self, filename: str) -> FileInfo | None:
        """Find file by exact name.

        Args:
            filename: Name to search for

        Returns:
            FileInfo if found, None otherwise
        """
        return self._name_map.get(filename)

    def get_by_pattern(self, pattern: str) -> list[FileInfo]:
        """Find files by glob pattern.

        Args:
            pattern: Glob pattern (e.g., "*.src", "LOAD_DATA/*.src")

        Returns:
            List of matching FileInfo objects
        """
        import fnmatch

        matching = []
        for file_info in self.files:
            # Use path parts for matching
            file_parts = file_info.path.parts

            # If pattern has directory separator, match against path
            if "/" in pattern or "\\" in pattern:
                # Full path matching
                path_str = "/".join(file_parts)
                if fnmatch.fnmatch(path_str, pattern.replace("\\", "/")):
                    matching.append(file_info)
            else:
                # Just filename matching
                if fnmatch.fnmatch(file_info.path.name, pattern):
                    matching.append(file_info)

        return matching

    def get_by_directory(self, directory: str) -> list[FileInfo]:
        """Find all files in directory.

        Args:
            directory: Directory name to search

        Returns:
            List of FileInfo objects in that directory
        """
        return self._dir_map.get(directory, [])


class BackupReader:
    """Read backup files from ZIP or folder."""

    def __init__(self, backup_source: Path) -> None:
        """Initialize backup reader.

        Args:
            backup_source: Path to ZIP file or folder

        Raises:
            FileNotFoundError: If path doesn't exist
            ValueError: If ZIP file is invalid
        """
        if not backup_source.exists():
            raise FileNotFoundError(f"Backup source not found: {backup_source}")

        self.is_temporary = False
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None

        if backup_source.suffix.lower() == ".zip":
            self._open_zip(backup_source)
        else:
            self.backup_path = backup_source

        self.index = FileIndex.build(self.backup_path)

    def _open_zip(self, zip_path: Path) -> None:
        """Extract ZIP to temporary directory.

        Args:
            zip_path: Path to ZIP file

        Raises:
            ValueError: If ZIP is invalid
        """
        try:
            # Validate ZIP before extracting
            with ZipFile(zip_path) as zf:
                zf.testzip()
        except BadZipFile as e:
            raise ValueError(f"Invalid ZIP file: {zip_path}") from e

        # Extract to temp directory
        self._temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self._temp_dir.name)

        with ZipFile(zip_path) as zf:
            zf.extractall(temp_path)

        self.backup_path = temp_path
        self.is_temporary = True

    def read_file(self, relative_path: str) -> str:
        """Read file content.

        Args:
            relative_path: Path relative to backup root

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        # Try to find in index first
        file_info = self.index.get_by_name(Path(relative_path).name)
        if file_info and file_info.absolute_path and file_info.absolute_path.exists():
            return file_info.absolute_path.read_text(encoding="utf-8", errors="replace")

        # Fallback to path-based lookup
        file_path = self.backup_path / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found in backup: {relative_path}")

        return file_path.read_text(encoding="utf-8", errors="replace")

    def list_files(self) -> list[FileInfo]:
        """List all files in backup.

        Returns:
            List of all FileInfo objects
        """
        return self.index.files

    def find_files(self, pattern: str) -> list[FileInfo]:
        """Find files by pattern.

        Args:
            pattern: Glob pattern

        Returns:
            List of matching FileInfo objects
        """
        return self.index.get_by_pattern(pattern)

    def find_files_in_directory(self, directory: str) -> list[FileInfo]:
        """Find all files in directory.

        Args:
            directory: Directory name

        Returns:
            List of FileInfo objects in directory
        """
        return self.index.get_by_directory(directory)

    def close(self) -> None:
        """Close backup and clean up temporary files."""
        if self.is_temporary and self._temp_dir:
            self._temp_dir.cleanup()
            self._temp_dir = None

    def __enter__(self) -> "BackupReader":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Context manager exit with cleanup."""
        self.close()

    def __del__(self) -> None:
        """Ensure cleanup on deletion."""
        with contextlib.suppress(Exception):
            self.close()
