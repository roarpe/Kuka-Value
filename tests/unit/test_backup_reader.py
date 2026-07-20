"""Unit tests for BackupReader."""

import tempfile
from pathlib import Path
from zipfile import ZipFile

import pytest

from kuka_value.parser.backup_reader import BackupReader, FileIndex


@pytest.fixture
def temp_dir() -> Path:
    """Create temporary directory for test backups."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def simple_backup_dir(temp_dir: Path) -> Path:
    """Create a simple backup directory structure."""
    backup = temp_dir / "backup_folder"
    backup.mkdir()

    (backup / "LOAD_DATA").mkdir()
    (backup / "LOAD_DATA" / "payload1.src").write_text("LOAD_DATA payload1")
    (backup / "LOAD_DATA" / "payload2.src").write_text("LOAD_DATA payload2")

    (backup / "MACHINE.DAT").write_text("MACHINE: KR 240 R2900")
    (backup / "ROBCOR").mkdir()
    (backup / "ROBCOR" / "data.src").write_text("ROBCOR data")

    return backup


@pytest.fixture
def simple_backup_zip(temp_dir: Path, simple_backup_dir: Path) -> Path:
    """Create a ZIP backup from folder structure."""
    zip_path = temp_dir / "backup.zip"

    with ZipFile(zip_path, "w") as zf:
        for file in simple_backup_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(simple_backup_dir.parent)
                zf.write(file, arcname)

    return zip_path


class TestFileIndex:
    """Test FileIndex data structure."""

    def test_file_index_stores_paths(self, simple_backup_dir: Path) -> None:
        """FileIndex should store all file paths."""
        index = FileIndex.build(simple_backup_dir)

        paths = {f.path for f in index.files}
        assert len(paths) == 4
        assert any("payload1.src" in str(p) for p in paths)
        assert any("payload2.src" in str(p) for p in paths)
        assert any("MACHINE.DAT" in str(p) for p in paths)
        assert any("data.src" in str(p) for p in paths)

    def test_file_index_stores_metadata(self, simple_backup_dir: Path) -> None:
        """FileIndex should store file size and absolute path."""
        index = FileIndex.build(simple_backup_dir)

        assert len(index.files) == 4
        for file_info in index.files:
            assert file_info.absolute_path is not None
            assert file_info.absolute_path.exists()
            assert file_info.size > 0

    def test_file_index_single_pass(self, simple_backup_dir: Path) -> None:
        """FileIndex.build should traverse directory exactly once."""
        index1 = FileIndex.build(simple_backup_dir)
        index2 = FileIndex.build(simple_backup_dir)

        # Both should have same files
        assert len(index1.files) == len(index2.files)
        paths1 = sorted(f.path.name for f in index1.files)
        paths2 = sorted(f.path.name for f in index2.files)
        assert paths1 == paths2

    def test_file_index_get_by_name(self, simple_backup_dir: Path) -> None:
        """FileIndex should find files by name."""
        index = FileIndex.build(simple_backup_dir)

        payload1 = index.get_by_name("payload1.src")
        assert payload1 is not None
        assert payload1.path.name == "payload1.src"

        missing = index.get_by_name("nonexistent.src")
        assert missing is None

    def test_file_index_get_by_pattern(self, simple_backup_dir: Path) -> None:
        """FileIndex should find files by glob pattern."""
        index = FileIndex.build(simple_backup_dir)

        src_files = index.get_by_pattern("*.src")
        assert len(src_files) == 3

        load_data_files = index.get_by_pattern("LOAD_DATA/*.src")
        assert len(load_data_files) == 2

    def test_file_index_get_by_directory(self, simple_backup_dir: Path) -> None:
        """FileIndex should find all files in directory."""
        index = FileIndex.build(simple_backup_dir)

        load_data_files = index.get_by_directory("LOAD_DATA")
        assert len(load_data_files) == 2

        nonexistent = index.get_by_directory("NONEXISTENT")
        assert len(nonexistent) == 0


class TestBackupReaderFolder:
    """Test BackupReader with folder input."""

    def test_reader_opens_folder(self, simple_backup_dir: Path) -> None:
        """BackupReader should open folder backup."""
        reader = BackupReader(simple_backup_dir)

        assert reader.backup_path == simple_backup_dir
        assert reader.is_temporary is False

    def test_reader_creates_index(self, simple_backup_dir: Path) -> None:
        """BackupReader should create file index."""
        reader = BackupReader(simple_backup_dir)

        assert reader.index is not None
        assert len(reader.index.files) == 4

    def test_reader_read_file(self, simple_backup_dir: Path) -> None:
        """BackupReader should read file content."""
        reader = BackupReader(simple_backup_dir)

        content = reader.read_file("LOAD_DATA/payload1.src")
        assert content == "LOAD_DATA payload1"

    def test_reader_read_file_not_found(self, simple_backup_dir: Path) -> None:
        """BackupReader should raise error for missing file."""
        reader = BackupReader(simple_backup_dir)

        with pytest.raises(FileNotFoundError):
            reader.read_file("NONEXISTENT.src")

    def test_reader_list_files(self, simple_backup_dir: Path) -> None:
        """BackupReader should list all files."""
        reader = BackupReader(simple_backup_dir)

        files = reader.list_files()
        assert len(files) == 4

        names = {f.path.name for f in files}
        assert "MACHINE.DAT" in names

    def test_reader_find_files_by_name(self, simple_backup_dir: Path) -> None:
        """BackupReader should find files by name."""
        reader = BackupReader(simple_backup_dir)

        files = reader.find_files("*.src")
        assert len(files) == 3

    def test_reader_find_files_in_directory(self, simple_backup_dir: Path) -> None:
        """BackupReader should find files in subdirectory."""
        reader = BackupReader(simple_backup_dir)

        files = reader.find_files_in_directory("LOAD_DATA")
        assert len(files) == 2

    def test_reader_close_folder(self, simple_backup_dir: Path) -> None:
        """BackupReader should handle close gracefully for folders."""
        reader = BackupReader(simple_backup_dir)
        reader.close()

        # Should still be accessible
        assert reader.backup_path.exists()


class TestBackupReaderZip:
    """Test BackupReader with ZIP input."""

    def test_reader_opens_zip(self, simple_backup_zip: Path) -> None:
        """BackupReader should open ZIP backup."""
        reader = BackupReader(simple_backup_zip)

        assert reader.backup_path.exists()
        assert reader.is_temporary is True

    def test_reader_extracts_zip_to_temp(self, simple_backup_zip: Path) -> None:
        """BackupReader should extract ZIP to temporary directory."""
        reader = BackupReader(simple_backup_zip)

        # backup_path should be temp directory, not zip file
        assert reader.backup_path != simple_backup_zip
        assert reader.backup_path.exists()
        assert reader.backup_path.is_dir()

    def test_reader_indexes_extracted_files(self, simple_backup_zip: Path) -> None:
        """BackupReader should index extracted files."""
        reader = BackupReader(simple_backup_zip)

        assert reader.index is not None
        assert len(reader.index.files) == 4

    def test_reader_read_file_from_zip(self, simple_backup_zip: Path) -> None:
        """BackupReader should read extracted file content."""
        reader = BackupReader(simple_backup_zip)

        content = reader.read_file("backup_folder/LOAD_DATA/payload1.src")
        assert content == "LOAD_DATA payload1"

    def test_reader_cleanup_temp_on_close(self, simple_backup_zip: Path) -> None:
        """BackupReader should clean up temporary directory on close."""
        reader = BackupReader(simple_backup_zip)
        temp_path = reader.backup_path

        assert temp_path.exists()
        reader.close()

        # Temporary directory should be cleaned up
        assert not temp_path.exists()

    def test_reader_cleanup_on_del(self, simple_backup_zip: Path) -> None:
        """BackupReader should clean up on deletion."""
        reader = BackupReader(simple_backup_zip)
        temp_path = reader.backup_path

        assert temp_path.exists()
        del reader

        # Temporary directory should be cleaned up
        assert not temp_path.exists()

    def test_reader_context_manager(self, simple_backup_zip: Path) -> None:
        """BackupReader should work as context manager."""
        temp_path = None

        with BackupReader(simple_backup_zip) as reader:
            temp_path = reader.backup_path
            assert temp_path.exists()
            assert len(reader.index.files) == 4

        # Should be cleaned up after context
        assert not temp_path.exists()


class TestBackupReaderErrors:
    """Test BackupReader error handling."""

    def test_reader_invalid_path(self) -> None:
        """BackupReader should raise error for invalid path."""
        with pytest.raises(FileNotFoundError):
            BackupReader(Path("/nonexistent/path"))

    def test_reader_invalid_zip(self, temp_dir: Path) -> None:
        """BackupReader should raise error for invalid ZIP."""
        bad_zip = temp_dir / "bad.zip"
        bad_zip.write_text("not a zip file")

        with pytest.raises(ValueError):
            BackupReader(bad_zip)

    def test_reader_empty_backup(self, temp_dir: Path) -> None:
        """BackupReader should handle empty backup."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        reader = BackupReader(empty_dir)
        assert len(reader.list_files()) == 0

    def test_reader_deeply_nested_files(self, temp_dir: Path) -> None:
        """BackupReader should handle deeply nested files."""
        nested = temp_dir / "nested" / "deep" / "structure" / "here"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_text("deep file")

        reader = BackupReader(temp_dir / "nested")
        files = reader.list_files()

        assert len(files) == 1
        assert "file.txt" in files[0].path.name


@pytest.mark.unit
def test_backup_reader_integration(simple_backup_dir: Path) -> None:
    """Integration test: read backup, find files, extract content."""
    reader = BackupReader(simple_backup_dir)

    # Find payload files
    payloads = reader.find_files("*.src")
    assert len(payloads) == 3

    # Read machine data
    machine_data = reader.read_file("MACHINE.DAT")
    assert "KR 240 R2900" in machine_data

    # Find files in specific directory
    load_data = reader.find_files_in_directory("LOAD_DATA")
    assert len(load_data) == 2

    reader.close()
