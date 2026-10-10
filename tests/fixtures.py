import pytest
import json
import shutil
from docstorage.db import resolve_db, import_file
from datetime import date
from pathlib import Path

# Fixture Hierarchy
# - setup_db_environment
# - setup_files_to_move
# - setup_incomplete_db_environment
#
# - setup_db_environment => setup_db
# - (setup_db, setup_files_to_move) => setup_populated_storage

# All fixtures yield the root of the temporary directory


@pytest.fixture
def setup_db_environment(tmp_path, monkeypatch):
    """Set up the database volume and yield the temp directory root."""
    (tmp_path / "volume" / "index").mkdir(parents=True)
    (tmp_path / "volume" / "storage").mkdir(parents=True)
    (tmp_path / "landing").mkdir()
    (tmp_path / "config").mkdir()

    config = {
        "landing-directory": str((tmp_path / "landing").resolve()),
        "db-path": str((tmp_path / "volume" / "index" / "index.db").resolve()),
        "storage-path": str((tmp_path / "volume" / "storage").resolve()),
    }
    with open(tmp_path / "config" / "config.json", "w") as f:
        json.dump(config, f)

    monkeypatch.setenv("TEST_CONFIG_PATH", str(tmp_path / "config" / "config.json"))
    monkeypatch.setenv("DOCSTORAGE_ENV", "test")
    yield tmp_path


@pytest.fixture
def setup_incomplete_db_environment(tmp_path, monkeypatch):
    """Configure invalid database paths and yield the temp directory root."""
    # Index storage & landing are not created
    (tmp_path / "config").mkdir()
    config = {
        "db-path": str((tmp_path / "volume" / "index" / "index.db").resolve()),
        "storage-path": str((tmp_path / "volume" / "storage").resolve()),
        "landing-directory": str((tmp_path / "landing").resolve()),
    }
    with open(tmp_path / "config" / "config.json", "w") as f:
        json.dump(config, f)

    monkeypatch.setenv("TEST_CONFIG_PATH", str(tmp_path / "config" / "config.json"))
    monkeypatch.setenv("DOCSTORAGE_ENV", "test")
    yield tmp_path


@pytest.fixture
def setup_db(setup_db_environment):
    """Initialize the database and yield the temp directory root."""
    resolve_db()
    yield setup_db_environment


@pytest.fixture
def setup_files_to_move(tmp_path, monkeypatch):
    """Copy test files into and yield the temp directory root."""
    test_volume = Path(__file__).parent / "volume"
    for file in test_volume.iterdir():
        if file.name.startswith("."):
            continue
        shutil.copy2(file, tmp_path / file.name)
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
