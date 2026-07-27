import os
import sqlite3
from datetime import date
import subprocess
import pytest
from pathlib import Path

from src.db import (
    _get_db_vars,
    resolve_db,
    _prepare_insert,
    import_file,

    _prepare_drop,
    _build_where_restrictions,
    drop_file_set,
)
from src.utility import DateInterval


# Fixture Hierarchy
# - setup_db_environment
# - setup_files_to_move
# - setup_bad_db_environment
#
# - setup_db_environment => setup_db
# - (setup_db, setup_files_to_move) => setup_populated_storage

@pytest.fixture
def setup_db_environment(tmp_path, monkeypatch):
    """Set up the database volume and yield the temp directory root."""
    subprocess.run(["mkdir", "-p", f"{tmp_path}/volume/index", f"{tmp_path}/volume/storage"])

    monkeypatch.setenv(
        "DB_PATH",
        str(tmp_path / "volume" / "index" / "index.db"),
    )
    monkeypatch.setenv(
        "STORAGE_PATH",
        str(tmp_path / "volume" / "storage"),
    )
    yield tmp_path


@pytest.fixture
def setup_bad_db_environment(tmp_path, monkeypatch):
    """Configure invalid database paths and yield the temp directory root."""
    monkeypatch.setenv(
        "DB_PATH",
        str(tmp_path / "volume" / "index" / "index.db"),
    )
    monkeypatch.setenv(
        "STORAGE_PATH",
        str(tmp_path / "volume" / "index" / "storage"),
    )
    yield tmp_path


@pytest.fixture
def setup_db(setup_db_environment):
    """Initialize the database and yield the temp directory root."""
    resolve_db()
    yield setup_db_environment


@pytest.fixture
def setup_files_to_move(tmp_path, monkeypatch):
    """Copy test files into and yield the temp directory root."""
    test_volume = Path("/Users/Misha/Documents/Dev/projects/docstorage/tests/volume")
    for file in test_volume.iterdir():
        if file.name.startswith("."):
            continue
        subprocess.run(["cp", file, str(tmp_path / file.name)], check=True)
    yield tmp_path


@pytest.fixture
def setup_populated_storage(setup_db, setup_files_to_move):
    """Populate the database and yield the temp directory root."""
    files = [
        {"filepath": setup_files_to_move / "normal-file-a.pdf",
         "description": "Some description of a, contains content",
         "date_created": date(2026, 1, 1), "tags": ["tag1", "tag2"]},
        {"filepath": setup_files_to_move / "normal-file-b.pdf", "description": "Some description of b",
         "date_created": date(2024, 1, 1), "tags": ["tag2", "tag3"]},
        {"filepath": setup_files_to_move / "normal file c.pdf",
         "description": "Some description of c, contains content",
         "date_created": date(2025, 5, 4), "tags": ["tag4", "tag5"]},
    ]
    for file in files:
        import_file(file["filepath"], file["description"], file["date_created"], file["tags"])

    yield setup_db


def test_missing_env_vars():
    with pytest.raises(LookupError):
        _get_db_vars()


class TestResolve:
    def test_first_start(self, setup_db_environment):
        resolve_db()

        with sqlite3.connect(Path(os.environ["DB_PATH"])) as con:
            tables = con.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()

        assert {name for (name,) in tables} == {"index", "tags"}

    def test_valid_existing_db(self, setup_db_environment):
        resolve_db()
        resolve_db()

    def test_empty_existing_db(self, setup_db_environment):
        volume_path = setup_db_environment
        (volume_path / "volume" / "index" / "index.db").touch()
        with pytest.raises(RuntimeError):
            resolve_db()

    def test_bad_path(self, setup_bad_db_environment):
        with pytest.raises(FileNotFoundError):
            resolve_db()


class TestHelperInsert:
    def test_normal_insert(self, setup_db):
        con = _prepare_insert(
            "test.pdf",
            "4c2e9e6da31a64c70623619c449a040968cdbea85945bf384fa30ed2d5d24fa3",
            "This is a test file.",
            date(2026, 1, 1),
            ["test", "tag", "tag2"]
        )
        con.commit()
        con.close()
        # TODO: assert internal state

    def test_duplicate_insert(self, setup_db):
        con = _prepare_insert(
            "test.pdf",
            "4c2e9e6da31a64c70623619c449a040968cdbea85945bf384fa30ed2d5d24fa3",
            "This is a test file.",
            date(2026, 1, 1),
            ["test", "tag", "tag2"]
        )
        con.commit()
        con.close()

        with pytest.raises(RuntimeError):
            con = _prepare_insert(
                "test.pdf",
                "4c2e9e6da31a64c70623619c449a040968cdbea85945bf384fa30ed2d5d24fa3",
                "This is a test file.",
                date(2026, 1, 1),
                ["test", "tag", "tag2"]
            )
            con.commit()
            con.close()

    def test_duplicate_tags(self, setup_db):
        with pytest.raises(RuntimeError):
            con = _prepare_insert(
                "test.pdf",
                "4c2e9e6da31a64c70623619c449a040968cdbea85945bf384fa30ed2d5d24fa3",
                "This is a test file.",
                date(2026, 1, 1),
                ["tag", "tag"]
            )
            con.commit()
            con.close()


class TestImport:
    def test_normal_import(self, setup_db, setup_files_to_move):
        filepath = setup_files_to_move / "normal-file-a.pdf"
        should_bytes = filepath.read_bytes()
        import_file(filepath, "some description",
                    date(2026, 1, 1), ["tag1", "tag2"])

        assert list(Path(setup_db / "volume" / "storage").iterdir()), "The file has not been moved"

        internal_filepath: Path = list(Path(setup_db / "volume" / "storage").iterdir())[0]
        got_bytes = internal_filepath.read_bytes()

        assert got_bytes == should_bytes, "Bytes mismatch"

    def test_normal_whitespace_import(self, setup_db, setup_files_to_move):
        filepath = setup_files_to_move / "normal file c.pdf"
        should_bytes = filepath.read_bytes()
        import_file(filepath, "some description",
                    date(2026, 1, 1), ["tag1", "tag2"])

        assert list(Path(setup_db / "volume" / "storage").iterdir()), "The file has not been moved"

        internal_filepath: Path = list(Path(setup_db / "volume" / "storage").iterdir())[0]
        got_bytes = internal_filepath.read_bytes()

        assert got_bytes == should_bytes, "Bytes mismatch"

    def test_zero_bytes_import(self, setup_db, setup_files_to_move):
        filepath = setup_files_to_move / "empty_file.pdf"
        with pytest.raises(ImportError):
            import_file(filepath, "some description",
                        date(2026, 1, 1), ["tag1", "tag2"])

    def test_forbidden_import(self, setup_db):
        pass

    def test_duplicate_import(self, setup_db, setup_files_to_move):
        filepath = setup_files_to_move / "normal-file-a.pdf"
        import_file(filepath, "some description",
                    date(2026, 1, 1), ["tag1", "tag2"])

        filepath = setup_files_to_move / "normal-file-a-duplicate.pdf"
        with pytest.raises(ImportError):
            import_file(filepath, "some description",
                        date(2026, 1, 1), ["tag1", "tag2"])

    # Missing file and directory will not be tested here


class TestHelperDrop:
    def test_normal_drop(self, setup_db, setup_files_to_move):
        import_file(setup_files_to_move / "normal-file-a.pdf", "Some description",
                    date(2026, 1, 1), ["tag1", "tag2"])

        con = _prepare_drop(1)
        con.commit()
        con.close()

        with sqlite3.connect(setup_db / "volume" / "index" / "index.db") as con:
            res = con.execute("""SELECT *
                                 FROM "index" """).fetchall()
            assert len(res) == 0

    def test_missing_drop(self, setup_db):
        with pytest.raises(IndexError):
            _prepare_drop(1)


class TestWhereClauseBuild:
    def test_normal_inputs(self):
        created_interval = DateInterval(lower=date(2024, 1, 1), upper=date(2025, 1, 1))
        added_interval = DateInterval(lower=date(2025, 1, 1), upper=date(2026, 1, 1))
        got = _build_where_restrictions(id_=True, name=True, description_contains=True, date_created=created_interval,
                                        date_added=added_interval, tags=True)
        expected = ("id = :id_ AND name = :name AND description LIKE :description_contains AND "
                    "date_created >= :date_created_lower AND date_created <= :date_created_upper AND "
                    "date_added >= :date_added_lower AND date_added <= :date_added_upper AND "
                    "tag = :tags")
        assert got == expected, "Mismatch between expected and got SQL-string"

    def test_date_created_inclusive(self):
        interval = DateInterval(lower=date(2025, 1, 1), upper=date(2026, 1, 1))
        assert "date_created >= :date_created_lower AND date_created <= :date_created_upper" == _build_where_restrictions(
            date_created=interval), "Date created check failed"

    def test_date_created_exclusive(self):
        interval = DateInterval(lower=date(2025, 1, 1), upper=date(2026, 1, 1),
                                include_lower=False, include_upper=False)
        assert "date_created > :date_created_lower AND date_created < :date_created_upper" == _build_where_restrictions(
            date_created=interval), "Date created check failed"

    def test_only_one(self):
        assert "id = :id_" == _build_where_restrictions(id_=True), "Id only failed"
        assert "name = :name" == _build_where_restrictions(name=True), "Name only failed"
        assert "description LIKE :description_contains" == _build_where_restrictions(description_contains=True), \
            "Description only failed"
        assert "tag = :tags" == _build_where_restrictions(tags=True), "Tags only failed"

    def test_empty(self):
        assert "" == _build_where_restrictions()


class TestDelete:
    def test_normal_delete(self, setup_populated_storage):
        drop_file_set(description_contains="content", dry_run=False)
        assert len(list(Path(setup_populated_storage / "volume" / "storage").iterdir())) == 1
        with sqlite3.connect() as con:
            pass
        assert True  # check the index

    def test_dry_run(self, setup_populated_storage):
        assert drop_file_set(description_contains="content", dry_run=True) == 2
        assert True  # not dropped entries in the index

    def test_tag_delete(self, setup_populated_storage):
        drop_file_set(tags=["tag2", "tag3"], dry_run=False)
        assert len(list(Path(setup_populated_storage / "volume" / "storage").iterdir())) == 1

    def test_missing_tags(self, setup_populated_storage):
        drop_file_set(tags=["tag-1", "tag-2"], dry_run=False)
        assert len(list(Path(setup_populated_storage / "volume").iterdir())) == 3
        assert True # check index
