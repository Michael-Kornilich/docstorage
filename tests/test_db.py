import pytest
from pathlib import Path
from src.db import resolve_db, import_file, _insert_uncommited


@pytest.fixture
def setup_db_environment(tmp_path, monkeypatch):
    Path.mkdir(tmp_path / "volume")
    Path.mkdir(tmp_path / "volume" / "index")
    Path.mkdir(tmp_path / "volume" / "storage")

    monkeypatch.setenv(
        "DB_PATH",
        str(tmp_path / "volume" / "index" / "index.db"),
    )
    monkeypatch.setenv(
        "STORAGE_PATH",
        str(tmp_path / "volume" / "index" / "storage"),
    )
    yield


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
    yield


class TestResolver:
    def test_first_start(self, setup_db_environment):
        resolve_db()

    def test_valid_existing_db(self, setup_db_environment):
        resolve_db()
        resolve_db()

    def test_bad_path(self, setup_bad_db_environment):
        with pytest.raises(FileNotFoundError):
            resolve_db()

    def test_missing_env_vars(self):
        with pytest.raises(LookupError):
            resolve_db()


class TestInserter:
    pass


class TestImporter:
    pass
