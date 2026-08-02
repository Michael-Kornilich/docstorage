import sqlite3
from datetime import date
import shutil
import pytest
from pathlib import Path
import json

from src.db import (
    _get_config,
    _set_config,
    resolve_db,
    _prepare_insert,
    import_file,
    get_healthcheck,

    fetch_file_set,

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

# All fixtures yield the root of the temporary directory

@pytest.fixture
def setup_db_environment(tmp_path, monkeypatch):
    """Set up the database volume and yield the temp directory root."""
    (tmp_path / "volume" / "index").mkdir(parents=True)
    (tmp_path / "volume" / "storage").mkdir(parents=True)
    (tmp_path / "landing").mkdir()
    (tmp_path / "config").mkdir()

    user_config = {"landing-directory": str((tmp_path / "landing").resolve())}
    with open(tmp_path / "config" / "user.json", "w") as f:
        json.dump(user_config, f)
    local_config = {
        "db-path": str((tmp_path / "volume" / "index" / "index.db").resolve()),
        "storage-path": str((tmp_path / "volume" / "storage").resolve()),
    }
    with open(tmp_path / "config" / "local.json", "w") as f:
        json.dump(local_config, f)

    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    yield tmp_path


@pytest.fixture
def setup_bad_db_environment(tmp_path, monkeypatch):
    """Configure invalid database paths and yield the temp directory root."""
    (tmp_path / "config").mkdir()
    local_config = {
        "db-path": str((tmp_path / "volume" / "index" / "index.db").resolve()),
        "storage-path": str((tmp_path / "volume" / "index" / "storage").resolve()),
    }
    user_config = {"landing-directory": str((tmp_path / "landing").resolve())}
    with open(tmp_path / "config" / "local.json", "w") as f:
        json.dump(local_config, f)
    with open(tmp_path / "config" / "user.json", "w") as f:
        json.dump(user_config, f)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
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


def get_index_len():
    with sqlite3.connect(_get_config("local")["db-path"]) as con:
        res = con.execute("""SELECT *
                             FROM "index" """).fetchall()
    return len(res)


def get_storage_len():
    STORAGE_PATH = _get_config("local")["storage-path"]
    return len(list(Path(STORAGE_PATH).iterdir()))


def get_landing_dir_len():
    landing_dir = _get_config("user")["landing-directory"]
    return len(list(Path(landing_dir).iterdir()))


class TestConfigManager:
    def test_unknown_config_key(self, setup_db_environment):
        with pytest.raises(ValueError):
            _get_config("unknown")

    def test_set_good_config(self, setup_db_environment):
        _set_config("user", "landing-directory", "new/direcotory")
        _set_config("local", "db-path", "new/direcotory")

    def test_set_bad_config(self, setup_db_environment):
        with pytest.raises(KeyError):
            _set_config("user", "unknown", "new/direcotory")


class TestResolve:
    def test_first_start(self, setup_db_environment):
        resolve_db()

        with sqlite3.connect(Path(_get_config("local")["db-path"])) as con:
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
        assert get_index_len() == 1

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

        assert get_storage_len() == 1, "The file has not been moved successfully"

        internal_filepath: Path = list(Path(setup_db / "volume" / "storage").iterdir())[0]
        got_bytes = internal_filepath.read_bytes()

        assert got_bytes == should_bytes, "Bytes mismatch"

    def test_normal_whitespace_import(self, setup_db, setup_files_to_move):
        filepath = setup_files_to_move / "normal file c.pdf"
        should_bytes = filepath.read_bytes()
        import_file(filepath, "some description",
                    date(2026, 1, 1), ["tag1", "tag2"])

        assert get_storage_len() == 1, "The file has not been moved successfully"

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
                                        date_added=added_interval, tags=["a", "b"])
        expected = ("id = :id_ AND name = :name AND description LIKE :description_contains AND "
                    "date_created >= :date_created_lower AND date_created <= :date_created_upper AND "
                    "date_added >= :date_added_lower AND date_added <= :date_added_upper AND "
                    "tag in (:tag0, :tag1)")
        assert got == expected, "Mismatch between expected and got SQL-string"

    def test_tag_build(self):
        assert "tag in (:tag0, :tag1, :tag2)" == _build_where_restrictions(tags=["a", "b", "c"])

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
        assert "tag in (:tag0, :tag1)" == _build_where_restrictions(tags=["tag1", "tag2"]), "Tags only failed"

    def test_empty(self):
        assert "" == _build_where_restrictions()


class TestFeasibleSet:
    pass


class TestDelete:
    def test_normal_delete(self, setup_populated_storage):
        drop_file_set(description_contains="content", dry_run=False)
        assert get_storage_len() == 1
        assert get_index_len() == 1

    def test_id_delete(self, setup_populated_storage):
        drop_file_set(id_=1, dry_run=False)
        assert get_storage_len() == 2
        assert get_index_len() == 2

    def test_name_delete(self, setup_populated_storage):
        drop_file_set(name="normal-file-a.pdf", dry_run=False)
        assert get_storage_len() == 2
        assert get_index_len() == 2

    def test_dry_run(self, setup_populated_storage):
        assert drop_file_set(description_contains="content", dry_run=True) == 2, \
            "Returned number of dry-dropped does match the expected number"
        assert get_index_len() == 3
        assert get_storage_len() == 3

    def test_tag_delete(self, setup_populated_storage):
        drop_file_set(tags=["tag2", "tag3"], dry_run=False)
        assert get_index_len() == 1
        assert get_storage_len() == 1

    def test_missing_tags(self, setup_populated_storage):
        drop_file_set(tags=["tag-1", "tag-2"], dry_run=False)
        assert get_index_len() == 3
        assert get_storage_len() == 3

    def test_miscellaneous_dry(self, setup_populated_storage):
        assert drop_file_set(id_=10, dry_run=True) == 0, "Bad id failed"
        assert drop_file_set(name="hello-world", dry_run=True) == 0, "Bad name failed"
        assert drop_file_set(description_contains="description", dry_run=True) == 3, "Multiple descriptions failed"
        assert drop_file_set(tags=["tag-1", "tag-2"], dry_run=True) == 0, "Bad tags failed"

        assert get_index_len() == 3, "Dry run failed"
        assert get_storage_len() == 3, "Dry run failed"


class TestFetch:
    def test_normal_fetch(self, setup_populated_storage):
        out = fetch_file_set(id_=1, dry_run=False)
        assert out is None
        assert get_storage_len() == 3
        assert get_index_len() == 3
        assert get_landing_dir_len() == 1

    def test_empty_fetch(self, setup_populated_storage):
        out = fetch_file_set(id_=-1, dry_run=False)
        assert out is None
        assert get_storage_len() == 3
        assert get_index_len() == 3
        assert get_landing_dir_len() == 0

    def test_missing_fetch(self, setup_populated_storage):
        out = fetch_file_set(name="hello-world", dry_run=False)
        assert out is None
        assert get_storage_len() == 3
        assert get_index_len() == 3
        assert get_landing_dir_len() == 0

    def test_dry_run(self, setup_populated_storage):
        out = fetch_file_set(id_=1, dry_run=True)
        assert all(isinstance(i, str) for row in out for i in row)
        assert out is not None
        assert get_storage_len() == 3
        assert get_index_len() == 3
        assert get_landing_dir_len() == 0

    def test_exising_file_fetch(self, setup_populated_storage):
        fetch_file_set(name="normal-file-a.pdf", dry_run=False)
        fetch_file_set(name="normal-file-a.pdf", dry_run=False, keep_existing=True)
        assert get_storage_len() == 3
        assert get_index_len() == 3
        assert get_landing_dir_len() == 2

        for i in Path(setup_populated_storage / "landing").iterdir():
            assert i.name in ("normal-file-a.pdf", "doc normal-file-a.pdf")

    def test_existing_but_no_key(self, setup_populated_storage):
        fetch_file_set(name="normal-file-a.pdf", dry_run=False)
        with pytest.raises(FileExistsError):
            fetch_file_set(name="normal-file-a.pdf", dry_run=False)


class TestHealthcheck:
    def test_no_mismatch(self, setup_populated_storage):
        """Return no report when storage and index contain the same hashes."""
        assert get_healthcheck() is None

    def test_storage_mismatch(self, setup_populated_storage):
        """Report an indexed file whose storage file has been removed."""
        with sqlite3.connect(_get_config("local")["db-path"]) as con:
            file_hash, = con.execute(
                'SELECT sha256 FROM "index" WHERE id = 1'
            ).fetchone()

        Path(_get_config("local")["storage-path"], file_hash).unlink()

        assert get_healthcheck() == {
            "index-mismatch": [(1, "normal-file-a.pdf")],
            "storage-mismatch": set(),
        }

    def test_index_mismatch(self, setup_populated_storage):
        """Report a storage file whose index row has been removed."""
        with sqlite3.connect(_get_config("local")["db-path"]) as con:
            file_hash, = con.execute(
                'SELECT sha256 FROM "index" WHERE id = 1'
            ).fetchone()
            con.execute('DELETE FROM "index" WHERE id = 1')

        assert get_healthcheck() == {
            "index-mismatch": [],
            "storage-mismatch": {file_hash},
        }
