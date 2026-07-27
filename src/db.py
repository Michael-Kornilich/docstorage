"""Database- and storage-related functions"""
import sqlite3
from src.utility import DateInterval
from pathlib import Path
from datetime import date
from typing import Sequence
from hashlib import sha256


def _get_db_vars() -> tuple[Path, Path]:
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

    DB_PATH, STORAGE_PATH = _get_db_vars()

    # id: SQLite's specific alias for rowid. The primary key is automatically generated
    create_index_sql = """
                       CREATE TABLE "index"
                       (
                           id           INTEGER PRIMARY KEY,
                           sha256       TEXT NOT NULL UNIQUE,
                           name         TEXT NOT NULL,
                           description  TEXT NOT NULL,
                           date_created TEXT NOT NULL,
                           date_added   TEXT NOT NULL DEFAULT CURRENT_DATE
                       ) \
                       """.strip()
    create_tags_sql = """
                      CREATE TABLE "tags"
                      (
                          id  INTEGER REFERENCES "index" (id) ON DELETE CASCADE,
                          tag TEXT NOT NULL,
                          PRIMARY KEY (id, tag)
                      ) \
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

        with open(DB_PATH, mode="rb") as f:
            if len(f.read()) == 0:
                raise RuntimeError(f"Corrupted index: no data available")
    return


# Everything below assumes a valid DB #

# healthcheck - checks to what extent the index and the storage agree

# --------------------------------------
# ------ Import related functions ------
# --------------------------------------
def _prepare_insert(
        name: str,
        hexdigest: str,
        description: str,
        date_created: date,
        tags: Sequence[str],
) -> sqlite3.Connection:
    """
    Helper function to insert the given data into index.
    Does not commit the transaction, hence prepare_insert.
    Raises FileExistsError if the insert is duplicate
    """

    DB_PATH, _ = _get_db_vars()

    con = sqlite3.connect(DB_PATH, autocommit=False)
    con.execute("PRAGMA foreign_keys = ON")  # Turned off by default for backwards compatibility

    insert_sql = """
                 INSERT INTO "index" (sha256, name, description, date_created)
                 VALUES (?, ?, ?, ?) \
                 """
    params = (hexdigest, name, description, date_created.isoformat())

    try:
        cursor = con.execute(insert_sql, params)
        index_id = cursor.lastrowid
        con.executemany(
            """INSERT INTO tags (id, tag)
               VALUES (?, ?)""",
            [(index_id, tag) for tag in tags]
        )
    except Exception as err:
        con.rollback()
        con.close()
        raise RuntimeError(f"Could not insert the given data: {type(err).__name__} - {err}") from err

    return con


def import_file(
        source: Path,
        description: str,
        date_created: date,
        tags: Sequence[str]
) -> None:
    """
    Moves the specified file into the internal storage and adds and entry to the index.
    Owns file checking. Path checking is done upstream
    """

    _, STORAGE_PATH = _get_db_vars()

    try:
        with open(source, mode="rb") as source_file:
            binary = source_file.read()
    except PermissionError as err:
        raise ImportError("Cannot read the given file: not enough permissions.") from err

    if not binary:
        raise ImportError("Cannot move empty files.")

    hexdigest = sha256(binary).hexdigest()

    try:
        con = _prepare_insert(source.name, hexdigest, description, date_created, tags)
    except Exception as err:
        raise ImportError(f"Could not update the index: {type(err).__name__} - {err}") from err

    with open(STORAGE_PATH / hexdigest, mode="wb") as target_file:
        target_file.write(binary)

    try:
        source.unlink()
    except PermissionError as err:
        Path(STORAGE_PATH / hexdigest).unlink()
        con.rollback()
        raise ImportError("Cannot move the given file: not enough permissions.") from err
    else:
        con.commit()
    finally:
        con.close()

    return


# --------------------------------------
# ------ Fetch related functions -------
# --------------------------------------

# read - read an entry and serve the file into the landing directory

# --------------------------------------
# ------- Drop related functions -------
# --------------------------------------
def _prepare_drop(id_: int) -> sqlite3.Connection:
    """
    Helper function to drop the given id from the table.
    Does not commit the drop, hence the name.
    Raises FileExistsError if the insert is duplicate
    """
    DB_PATH, _ = _get_db_vars()
    con = sqlite3.connect(DB_PATH, autocommit=False)
    con.execute("PRAGMA foreign_keys = ON")  # Turned off by default for backwards compatibility
    res = con.execute("""DELETE
                         FROM "index"
                         WHERE id = ?""", (id_,))

    if res.rowcount == 0:
        con.rollback()
        con.close()
        raise IndexError(f"Index does not exist: {id_}")

    return con


def _build_where_restrictions(
        id_: bool = False,
        name: bool = False,
        description_contains: bool = False,
        date_created: DateInterval | None = None,
        date_added: DateInterval | None = None,
        tags: Sequence[str] | None = (),
) -> str:
    """
    Helper function to build restriction for the WHERE clause.
    Parameters specify which dimensions to include.

    Returns an SQL-string ready for parameter insertion.
    Parameter names are:

    - (function parameter => SQL parameter)
    - id_ => id_
    - name => name
    - description_contains => description_contains
    - date_created => date_created_lower, date_created_upper
    - date_added => date_added_lower, date_added_upper
    - tags => tags
    """

    where_restrictions = []
    if id_:
        where_restrictions.append(f"id = :id_")
    if name:
        where_restrictions.append(f"name = :name")

    if description_contains:
        where_restrictions.append(f"description LIKE :description_contains")

    for name_, param in {"date_created": date_created, "date_added": date_added}.items():
        if not param:
            continue
        lower_sign = ">" + ("=" if param.include_lower else "")
        upper_sign = "<" + ("=" if param.include_upper else "")
        where_restrictions.append(f"{name_} {lower_sign} :{name_}_lower")
        where_restrictions.append(f"{name_} {upper_sign} :{name_}_upper")

    if tags:
        # Don't even ask how
        # tag in (:tag0, :tag1, :tag2, ...)
        tag_clause = "tag in " + "(" + ", ".join([f":tag{n}" for n, _ in enumerate(tags)]) + ")"
        where_restrictions.append(tag_clause)

    return " AND ".join(where_restrictions).strip()


def drop_file_set(
        id_: int | None = None,
        name: str | None = None,
        description_contains: str | None = None,
        date_created: DateInterval | None = None,
        date_added: DateInterval | None = None,
        tags: Sequence[str] = (),
        dry_run: bool = True,
) -> None | int:
    """
    Drop file(s) that match the union (AND) of the specified restrictions.
    If multiple files match the set of restrictions, all matching are dropped.
    Unspecified restrictions (None) are ignored.

    dry_run: If true, do not drop any files, but return the number of potentially dropped files.
    """
    DB_PATH, STORAGE_PATH = _get_db_vars()

    where_restrictions = _build_where_restrictions(bool(id_), bool(name), bool(description_contains),
                                                   date_created, date_added, tags)

    params = locals().copy()
    params.pop("dry_run")

    # Prepare parameter for binding
    for param in ("date_added", "date_created"):
        if not params.get(param):
            continue
        params.update({
            f"{param}_lower": params[param].lower,
            f"{param}_upper": params[param].upper,
        })
        params.pop(param)

    if params.get("tags"):
        for i, tag in enumerate(params.get("tags")):
            params.update({f"tag{i}": tag})
        params.pop("tags")

    if params.get("description_contains"):
        params["description_contains"] = "%" + params["description_contains"] + "%"

    with sqlite3.connect(DB_PATH) as con:
        select_query = f"""
        SELECT
            distinct 
            id,
            sha256
        FROM "index" i LEFT JOIN "tags" t USING (id)
        WHERE 
            {where_restrictions}
        """
        res = con.execute(select_query, params)
        files_to_drop = res.fetchall()

    if dry_run:
        return len(files_to_drop)

    for (i, hash_) in files_to_drop:
        con = _prepare_drop(i)
        Path(STORAGE_PATH / hash_).unlink(missing_ok=True)
        con.commit()
        con.close()

    return None
