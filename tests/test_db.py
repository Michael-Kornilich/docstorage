from fixtures import *
import sqlite3

from docstorage.db import (
    resolve_db,
    import_file,
    fetch_file_set,
    _build_where_restrictions,
    drop_file_set,
    get_healthcheck
)
from docstorage.utility import DateInterval
from docstorage.config import Config


def get_index_len():
    with sqlite3.connect(Config()["db-path"]) as con:
        res = con.execute("""SELECT *
                             FROM "index" """).fetchall()
    return len(res)


def get_storage_len():
    STORAGE_PATH = Config()["storage-path"]
    return len(list(Path(STORAGE_PATH).iterdir()))


def get_landing_dir_len():
    landing_dir = Config()["landing-directory"]
    return len(list(Path(landing_dir).iterdir()))


def get_tags_len():
    with sqlite3.connect(Config()["db-path"]) as con:
        res = con.execute("""SELECT *
                             FROM tags """).fetchall()
    return len(res)


class TestResolve:
    # TODO: paths pointing towards a file
    def test_first_start(self, setup_db_environment):
        resolve_db()

        with sqlite3.connect(Path(Config()["db-path"])) as con:
            tables = con.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()

        assert {name for (name,) in tables} == {"index", "tags"}

    def test_valid_existing_db(self, setup_populated_storage):
        resolve_db()

    def test_empty_existing_db(self, setup_db_environment):
        volume_path = setup_db_environment
        (volume_path / "volume" / "index" / "index.db").touch()
        with pytest.raises(RuntimeError):
            resolve_db()

    def test_incomplete_internal_fs(self, setup_incomplete_db_environment):
        resolve_db()

    def test_fs_pointing_to_file(self, setup_db_environment):
        (setup_db_environment / "landing").rmdir()
        resolve_db()
        assert (setup_db_environment / "landing").exists()


class TestImport:
    def test_normal_import(self, setup_db, setup_files_to_move):
        filepath = setup_files_to_move / "normal-file-a.pdf"
        should_bytes = filepath.read_bytes()
        import_file(filepath, "some description",
                    date(2026, 1, 1), ["tag1", "tag2"])

        assert get_storage_len() == 1, "The file has not been moved successfully"
        assert get_tags_len() == 2

        internal_filepath: Path = list(Path(setup_db / "volume" / "storage").iterdir())[0]
        got_bytes = internal_filepath.read_bytes()

        assert got_bytes == should_bytes, "Bytes mismatch"

    def test_normal_whitespace_import(self, setup_db, setup_files_to_move):
        filepath = setup_files_to_move / "normal file c.pdf"
        should_bytes = filepath.read_bytes()
        import_file(filepath, "some description",
                    date(2026, 1, 1), ["tag1", "tag2"])

        assert get_storage_len() == 1, "The file has not been moved successfully"
        assert get_tags_len() == 2

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

    def test_duplicate_tags(self, setup_db, setup_files_to_move):
        filepath = setup_files_to_move / "normal-file-a.pdf"
        with pytest.raises(ImportError):
            import_file(filepath, "some description",
                        date(2026, 1, 1), ["tag", "tag"])

    # Missing file and directory will not be tested here


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
        assert get_tags_len() == 2

    def test_id_delete(self, setup_populated_storage):
        drop_file_set(id_=1, dry_run=False)
        assert get_storage_len() == 2
        assert get_index_len() == 2
        assert get_tags_len() == 4

    def test_name_delete(self, setup_populated_storage):
        drop_file_set(name="normal-file-a.pdf", dry_run=False)
        assert get_storage_len() == 2
        assert get_index_len() == 2
        assert get_tags_len() == 4

    def test_dry_run(self, setup_populated_storage):
        assert drop_file_set(description_contains="content", dry_run=True) == 2, \
            "Returned number of dry-dropped does match the expected number"
        assert get_index_len() == 3
        assert get_storage_len() == 3

    def test_tag_delete(self, setup_populated_storage):
        drop_file_set(tags=["tag2", "tag3"], dry_run=False)
        assert get_index_len() == 1
        assert get_storage_len() == 1
        assert get_tags_len() == 2

    def test_missing_tags(self, setup_populated_storage):
        drop_file_set(tags=["tag-1", "tag-2"], dry_run=False)
        assert get_index_len() == 3
        assert get_storage_len() == 3
        assert get_tags_len() == 6

    def test_missing_drop(self, setup_populated_storage):
        drop_file_set(id_=0, dry_run=False)

    def test_miscellaneous_dry(self, setup_populated_storage):
        assert drop_file_set(id_=10, dry_run=True) == 0, "Bad id failed"
        assert drop_file_set(name="hello-world", dry_run=True) == 0, "Bad name failed"
        assert drop_file_set(description_contains="description", dry_run=True) == 3, "Multiple descriptions failed"
        assert drop_file_set(tags=["tag-1", "tag-2"], dry_run=True) == 0, "Bad tags failed"

        assert get_index_len() == 3, "Dry run failed"
        assert get_storage_len() == 3, "Dry run failed"
        assert get_tags_len() == 6, "Dry run failed"


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
        fetch_file_set(name="normal-file-a.pdf", dry_run=False, keep_existing=True)
        assert get_storage_len() == 3
        assert get_index_len() == 3
        assert get_landing_dir_len() == 3

        for i in Path(setup_populated_storage / "landing").iterdir():
            assert i.name in ("normal-file-a.pdf", "normal-file-a (1).pdf", "normal-file-a (2).pdf")

    def test_existing_but_no_key(self, setup_populated_storage):
        fetch_file_set(name="normal-file-a.pdf", dry_run=False)
        with pytest.raises(FileExistsError):
            fetch_file_set(name="normal-file-a.pdf", dry_run=False)

    def test_no_landing_dir(self, setup_populated_storage):
        Path(setup_populated_storage / "landing").rmdir()
        fetch_file_set(name="normal-file-a.pdf", dry_run=False)


class TestRandom:
    def test_random_good(self, setup_db):
        from random import randbytes, randint, choice
        from string import ascii_letters, digits, punctuation, whitespace
        from datetime import timedelta

        punctuation_wo_quotes = punctuation.replace('"', "").replace("'", "")

        root = setup_db
        source_dir = root / "random-source"
        source_dir.mkdir()

        records = []
        test_size = 50
        for index in range(test_size):
            binary = randbytes(randint(1, 10_000))
            name = f"random-{index}.bin"
            description = "".join(choice(ascii_letters + digits + whitespace + punctuation_wo_quotes)
                                  for _ in range(randint(1, 40))).strip()
            created = date(randint(1980, 2060), randint(1, 12), randint(1, 28))
            tags = list({
                "".join(choice(ascii_letters + digits + punctuation_wo_quotes)
                        for _ in range(randint(1, 8)))
                for _ in range(randint(1, 4))
            })
            source = source_dir / name
            source.write_bytes(binary)
            import_file(source, description, created, tags)
            records.append({
                "name": name,
                "bytes": binary,
                "description": description,
                "date_created": created,
                "tags": tags,
            })

        assert get_index_len() == len(records)
        assert get_storage_len() == len(records)
        assert get_tags_len() == len([t for i in records for t in i["tags"]])
        assert all(not (source_dir / record["name"]).exists() for record in records)

        selected = records[randint(0, test_size - 1)]
        lower_days = randint(0, 365)
        upper_days = randint(0, 365)
        interval = DateInterval(
            lower=selected["date_created"] - timedelta(days=lower_days),
            upper=selected["date_created"] + timedelta(days=upper_days),
            include_lower=True if lower_days == 0 else choice([True, False]),
            include_upper=True if upper_days == 0 else choice([True, False]),
        )
        fetched = fetch_file_set(
            date_created=interval,
            tags=selected["tags"][:1],
            dry_run=True,
        )
        assert fetched

        fetch_file_set(
            date_created=interval,
            tags=selected["tags"][:1],
            dry_run=False,
        )
        fetched_names = {row[2] for row in fetched}
        landing_files = {file.name: file.read_bytes()
                         for file in (root / "landing").iterdir()}
        assert set(landing_files) == fetched_names
        for record in records:
            if record["name"] in fetched_names:
                assert landing_files[record["name"]] == record["bytes"]

        for file in (root / "landing").iterdir():
            file.unlink()
        for row in fetched:
            drop_file_set(id_=int(row[0]), dry_run=False)

        assert get_index_len() == len(records) - len(fetched)
        assert get_storage_len() == len(records) - len(fetched)
        assert get_healthcheck() is None
