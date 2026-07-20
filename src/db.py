import os
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


# Possible issue: odd paths leading outside the project are unhandled
def resolve_db() -> None:
    """Create a new index or check the validity of the existing one. Raises if DB and storage paths are misspecified."""

    DB_PATH, STORAGE_PATH = _get_db_path()

    # id: SQLite's specific alias for rowid. The primary key is automatically generated
    create_index_sql = """
    CREATE TABLE "index" (
        id INTEGER PRIMARY KEY,
        sha256 TEXT NOT NULL UNIQUE,
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

    if not DB_PATH.exists():
        # Won't handle the case where the index does not exist, but files do or the other way around
        # Since this is a very unlikely scenario
        # This code is assumed to be executed on the very first start of the app.
        print("Index not found: creating a new one")
        try:
            DB_PATH.touch()
        except FileNotFoundError:
            raise FileNotFoundError(f"Failed to create the index: bad path") from None
        except Exception as err:
            raise RuntimeError(f"An unexpected exception occured while creating index: "
                               f"{type(err).__name__} - {err}") from err

        with sqlite3.connect(DB_PATH) as con:
            con.execute("PRAGMA foreign_keys = ON")
            con.execute(create_index_sql)
            con.execute(create_tags_sql)
    else:
        # Assume existing DB scheme / data has not been tampered with. Check only for a valid file.
        # Otherwise, handling is too complicated
        try:
            sqlite3.connect(DB_PATH).close()
        except Exception as err:
            raise RuntimeError(f"Corrupted index: {type(err).__name__} - {err}") from err
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

    insert_sql = """
        INSERT INTO "index" (sha256, name, description, date_created) 
        VALUES  (?, ?, ?, ?)
        """
    params = (hexdigest, name, description, date_created.isoformat())

    try:
        cursor = con.execute(insert_sql, params)
    except sqlite3.IntegrityError as err:
        raise FileExistsError(f"The given file already exists in the database.") from err

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

    try:
        with open(source, mode="rb") as source_file:
            binary = source_file.read()
    except PermissionError as err:
        raise RuntimeError("Cannot read the given file: not enough permissions.") from err

    hexdigest = sha256(binary).hexdigest()

    con = _insert_uncommited(source.name, hexdigest, description, date_created, tags)

    with open(STORAGE_PATH / hexdigest, mode="wb") as target_file:
        target_file.write(binary)

    try:
        source.unlink()
    except PermissionError as err:
        Path(STORAGE_PATH / hexdigest).unlink()
        con.rollback()
        raise RuntimeError("Cannot move the given file: not enough permissions.") from err
    else:
        con.commit()
    finally:
        con.close()

    return

# read - read an entry and serve the file into the landing directory
# drop - remove an entry
# healthcheck - checks to what extent the index and the storage agree
