import sqlite3
from pathlib import Path
from datetime import date
from collections import Sequence
from hashlib import sha256

DB_PATH: Path = Path("~/Documents/Dev/projects/docstorage/volume/index/index.db")
STORAGE_PATH: Path = Path("~/Documents/Dev/projects/docstorage/volume/storage")


def resolve_db() -> None:
    """Create a new index or check the validity of the existing one"""

    create_index_sql = """
    CREATE TABLE "index" (
        id INTEGER PRIMARY KEY, -- SQLite's specific alias for rowid. The primary key is automatically generated
        sha256 TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        date_created TEXT NOT NULL,
        date_added TEXT NOT NULL DEFAULT CURRENT_DATE
    )
    """.strip()
    create_tags_sql = """
    CREATE TABLE "tags" (
        id INTEGER REFERENCES "index" (id) ON DELETE CASCADE,
        tag TEXT NOT NULL,
        PRIMARY KEY (id, tag)
    )
    """.strip()
    _internal_table = "CREATE TABLE sqlite_sequence(name,seq)"

    if not DB_PATH.exists():
        # Won't handle the case where the index does not exist, but files do
        # Since this is a very unlikely scenario
        # This code is assumed to be executed on the very first start of the app.
        print("Index not found: creating a new one")
        DB_PATH.touch()
        with sqlite3.connect(DB_PATH) as con:
            con.execute("PRAGMA foreign_keys = ON")
            con.execute(create_index_sql)
            con.execute(create_tags_sql)
    else:
        should_tables = {create_index_sql, create_tags_sql, _internal_table}

        with sqlite3.connect(DB_PATH) as con:
            res = con.execute("""select sql from sqlite_schema;""").fetchall()
        got_tables = set([i[0] for i in res])

        if len(got_tables) != len(should_tables) or got_tables.difference(should_tables):
            raise RuntimeError("The index is corrupted.")
    return


def import_file(
        source: Path,
        description: str,
        date_created: date,
        tags: Sequence[str]
) -> None:
    """Moves the specified file into the internal storage and adds and entry to the index"""

    if not DB_PATH.exists():
        raise FileNotFoundError("The index does not exist. "
                                "Run resolve_db() to init the database or docstorage healthcheck to check the health")

    with open(source, mode="rb") as source_file:
        binary = source_file.read()
    source_hash = sha256(binary).hexdigest()

    con = sqlite3.connect(DB_PATH, autocommit=False)
    con.execute("PRAGMA foreign_keys = ON")  # Turned off by default for backwards compatibility
    # TODO: handle duplicate imports

    insert_sql = """
    INSERT INTO "index" (sha256, name, description, date_created) 
    VALUES  (?, ?, ?, ?)
    """
    params = (source_hash, source.name, description, date_created.isoformat())
    cursor = con.execute(insert_sql, params)
    index_id = cursor.lastrowid

    con.executemany(
        """INSERT INTO tags (id, tag) VALUES (?, ?)""",
        [(index_id, tag) for tag in tags]
    )

    with open(STORAGE_PATH / source_hash, mode="wb") as target_file:
        target_file.write(binary)

    source.unlink()
    con.commit()
    con.close()

# read - read an entry and serve the file into the landing directory
# drop - remove an entry
# healthcheck - checks to what extent the index and the storage agree
