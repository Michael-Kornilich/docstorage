# Test missing file and if passed a directory
from fixtures import *
from src.db import get_healthcheck, get_overview
from src.config import Config
import sqlite3


class TestHealthcheck:
    def test_no_mismatch(self, setup_populated_storage):
        """Return no report when storage and index contain the same hashes."""
        assert get_healthcheck() is None

    def test_storage_mismatch(self, setup_populated_storage):
        """Report an indexed file whose storage file has been removed."""
        config = Config()
        with sqlite3.connect(config["db-path"]) as con:
            file_hash, = con.execute(
                'SELECT sha256 FROM "index" WHERE id = 1'
            ).fetchone()

        Path(config["storage-path"], file_hash).unlink()

        assert get_healthcheck() == {
            "index-mismatch": [(1, "normal-file-a.pdf")],
            "storage-mismatch": set(),
        }

    def test_index_mismatch(self, setup_populated_storage):
        """Report a storage file whose index row has been removed."""
        with sqlite3.connect(Config()["db-path"]) as con:
            file_hash, = con.execute(
                'SELECT sha256 FROM "index" WHERE id = 1'
            ).fetchone()
            con.execute('DELETE FROM "index" WHERE id = 1')

        assert get_healthcheck() == {
            "index-mismatch": [],
            "storage-mismatch": {file_hash},
        }


class TestGetOverview:
    def test_empty(self, setup_db):
        res = get_overview()
        assert set(res.keys()) == {"n-total-files", "unique-tags", "min-max-dates"}
        assert res["n-total-files"] == 0, "Files"
        assert res["unique-tags"] == tuple(), "Tags"
        assert res["min-max-dates"] == tuple(), "Dates"

    def test_normal(self, setup_populated_storage):
        res = get_overview()
        assert res == {"n-total-files": 3, "unique-tags": tuple("tag" + str(i) for i in range(1, 6)),
                       "min-max-dates": (date(2024, 1, 1), date(2026, 1, 1))}
