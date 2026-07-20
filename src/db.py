import sqlite3
from pathlib import Path
from datetime import date
from typing import Sequence
from hashlib import sha256


def _get_db_path() -> tuple[Path, Path]:
    """Helper function to load DB paths. Returns a tuple of (db_path, storage_path)"""
    import os
    if not os.getenv("DB_PATH"):
        raise LookupError("Env variable DB_PATH is not specified")
    if not os.getenv("STORAGE_PATH"):
        raise LookupError("Env variable STORAGE_PATH is not specified")

    return Path(os.getenv("DB_PATH")), Path(os.getenv("STORAGE_PATH"))


def resolve_db() -> None:
    """Create a new index or check the validity of the existing one. Raises if DB and storage paths are misspecified."""

    DB_PATH, STORAGE_PATH = _get_db_path()

    # id: SQLite's specific alias for rowid. The primary key is automatically generated
    create_index_sql = """
    CREATE TABLE "index" (
        id INTEGER PRIMARY KEY,
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
        # Won't handle the case where the index does not exist, but files do or the other way around
        # Since this is a very unlikely scenario
        # This code is assumed to be executed on the very first start of the app.
        print("Index not found: creating a new one")
        try:
            DB_PATH.touch()
        except FileNotFoundError:
            raise FileNotFoundError(f"Failed to create the index: bad path") from None

        with sqlite3.connect(DB_PATH) as con:
            con.execute("PRAGMA foreign_keys = ON")
            con.execute(create_index_sql)
            con.execute(create_tags_sql)
    else:
        # Won't handle the case of direct changes to the table since too complicated
        try:
            sqlite3.connect(DB_PATH).close()
        except Exception as err:
            raise RecursionError(f"Corrupted index: {err}") from err
    return


#######################################
# Everything below assumes a valid DB #
#######################################

def _insert_uncommited(
        name: str,
        hexdigest: str,
        description: str,
        date_created: date,
        tags: Sequence[str],
) -> sqlite3.Connection:
    """Helper function to insert the given data into index. Raises FileExistsError if the insert is duplicate"""

    DB_PATH, STORAGE_PATH = _get_db_path()

    con = sqlite3.connect(DB_PATH, autocommit=False)
    con.execute("PRAGMA foreign_keys = ON")  # Turned off by default for backwards compatibility

    res = con.execute("""SELECT id, sha256 FROM "index" """).fetchall()
    for id_, hash_ in res:
        if hash_ == hexdigest:
            raise FileExistsError(f"The given file already exists in the database under id '{id_}'")

    insert_sql = """
        INSERT INTO "index" (sha256, name, description, date_created) 
        VALUES  (?, ?, ?, ?)
        """
    params = (hexdigest, name, description, date_created.isoformat())
    cursor = con.execute(insert_sql, params)
    index_id = cursor.lastrowid

    con.executemany(
        """INSERT INTO tags (id, tag) VALUES (?, ?)""",
        [(index_id, tag) for tag in tags]
    )
    return con


def import_file(
        source: Path,
        description: str,
        date_created: date,
        tags: Sequence[str]
) -> None:
    """Moves the specified file into the internal storage and adds and entry to the index"""

    DB_PATH, STORAGE_PATH = _get_db_path()

    if not DB_PATH.exists():
        raise FileNotFoundError("The index does not exist. "
                                "Run resolve_db() to init the database or docstorage healthcheck to check the health")

    with open(source, mode="rb") as source_file:
        binary = source_file.read()
    source_hash = sha256(binary).hexdigest()

    con = _insert_uncommited(source.name, source_hash, description, date_created, tags)

    with open(STORAGE_PATH / source_hash, mode="wb") as target_file:
        target_file.write(binary)

    con.commit()
    con.close()
    source.unlink()
    return

# TODO: test both functions

# read - read an entry and serve the file into the landing directory
# drop - remove an entry
# healthcheck - checks to what extent the index and the storage agree
