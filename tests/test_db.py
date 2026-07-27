import os
import sqlite3
from datetime import date
import subprocess
import pytest
from pathlib import Path

from src.db import (
    resolve_db,
    import_file,
    _prepare_insert,
    _prepare_drop,
    _get_db_vars
)


@pytest.fixture
def setup_db_environment(tmp_path, monkeypatch):
    """Yields path to the volume"""
    subprocess.run(["mkdir", "-p", f"{tmp_path}/volume/index", f"{tmp_path}/volume/storage"])

    monkeypatch.setenv(
        "DB_PATH",
        str(tmp_path / "volume" / "index" / "index.db"),
    )
    monkeypatch.setenv(
        "STORAGE_PATH",
        str(tmp_path / "volume" / "storage"),
    )
    yield tmp_path / "volume"


@pytest.fixture
def setup_bad_db_environment(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "DB_PATH",
        str(tmp_path / "volume" / "index" / "index.db"),
    )
    monkeypatch.setenv(
        "STORAGE_PATH",
        str(tmp_path / "volume" / "index" / "storage"),
    )
    yield tmp_path / "volume"


@pytest.fixture
def setup_db(setup_db_environment):
    """Yields path to the volume/"""
    resolve_db()
    yield setup_db_environment


@pytest.fixture
def setup_files_to_move(tmp_path, monkeypatch):
    root = "/Users/Misha/Documents/Dev/projects/docstorage"
    for i in ["empty_file.pdf", "normal_file.pdf", "normal_file_duplicate.pdf"]:
        subprocess.run(["cp", f"{root}/tests/volume/{i}", str(tmp_path / i)])
    yield tmp_path


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
        (volume_path / "index" / "index.db").touch()
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
        filepath = setup_files_to_move / "normal_file.pdf"
        should_bytes = filepath.read_bytes()
        import_file(filepath, "some description",
                    date(2026, 1, 1), ["tag1", "tag2"])

        assert list(Path(setup_db / "storage").iterdir()), "The file has not been moved"

        internal_filepath: Path = list(Path(setup_db / "storage").iterdir())[0]
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
        filepath = setup_files_to_move / "normal_file.pdf"
        import_file(filepath, "some description",
                    date(2026, 1, 1), ["tag1", "tag2"])

        filepath = setup_files_to_move / "normal_file_duplicate.pdf"
        with pytest.raises(ImportError):
            import_file(filepath, "some description",
                        date(2026, 1, 1), ["tag1", "tag2"])

    # Missing file and directory will not be tested here


class TestHelperDrop:
    def test_normal_drop(self, setup_db, setup_files_to_move):
        import_file(setup_files_to_move / "normal_file.pdf", "Some description",
                    date(2026, 1, 1), ["tag1", "tag2"])

        con = _prepare_drop(1)
        con.commit()
        con.close()

        with sqlite3.connect(setup_db / "index" / "index.db") as con:
            res = con.execute("""SELECT *
                                 FROM "index" """).fetchall()
            assert len(res) == 0

    def test_missing_drop(self, setup_db):
        with pytest.raises(IndexError):
            _prepare_drop(1)


class TestWhereBuilder:
    def test_normal_inputs(self):
        pass

    def test_only_id(self):
        pass


class TestDelete:
    def test_normal_delete(self, setup_db, setup_files_to_move):
        pass

    def test_mising_landing_dir(self, setup_db):
        pass
