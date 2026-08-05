"""Database- and storage-related functions"""
import sqlite3
import shutil
from src.utility import DateInterval
from pathlib import Path
from datetime import date
from typing import Literal, Sequence


# TODO: better documentation

def _get_config(tp: Literal["user", "local"]) -> dict[str, str]:
    """Helper function to load and validate either the user or local configuration."""
    import os
    CONFIG_DIR = Path(os.environ["PROJECT_ROOT"]) / "config"
    CONFIG_KEYS = {
        "user": {"landing-directory"},
        "local": {"db-path", "storage-path"},
    }
    if tp not in ("user", "local"):
        raise ValueError(f"Unknown config type: {tp}")

    config_path = CONFIG_DIR / f"{tp}.json"
    try:
        import json
        with open(config_path, mode="r") as f:
            config = json.load(f)
    except Exception as err:
        raise ImportError(f"Failed to load {tp} config: {err}") from err

    if CONFIG_KEYS[tp] != set(config.keys()) or not all(isinstance(value, str) for value in config.values()):
        raise KeyError(f"The {tp} config keys do not match the expected keys.")
    return config


def _set_config(tp: Literal["user", "local"], key: str, value: str) -> None:
    """Helper function to validate and set either the user or local configuration."""
    config = _get_config(tp)
    if key not in config:
        raise KeyError(f"The {key} is invalid.")

    config[key] = value

    import os
    import json

    config_path = Path(os.environ["PROJECT_ROOT"]) / "config" / f"{tp}.json"
    with open(config_path, "w") as f:
        json.dump(config, f)
    return


# Possible issue: odd paths leading outside the project are unhandled
def resolve_db() -> None:
    """Create a new index or check the validity of the existing one. Raises if DB and storage paths are misspecified."""

    config = _get_config("local")
    DB_PATH, STORAGE_PATH = Path(config["db-path"]), Path(config["storage-path"])

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
    return None


# Everything below assumes a valid DB #

def _get_feasible_file_set(
        id_: int | None = None,
        name: str | None = None,
        description_contains: str | None = None,
        date_created: DateInterval | None = None,
        date_added: DateInterval | None = None,
        tags: Sequence[str] = (),
) -> list[int]:
    """
    Helper function to return a set of file ids that fulfill given restrictions.
    Returns a list of ids
    """
    config = _get_config("local")
    DB_PATH, STORAGE_PATH = Path(config["db-path"]), Path(config["storage-path"])

    where_restrictions = _build_where_restrictions(bool(id_), bool(name), bool(description_contains),
                                                   date_created, date_added, tags)

    params = locals().copy()

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
                    distinct id
                FROM "index" i LEFT JOIN "tags" t USING (id)
                WHERE 
                    {where_restrictions}
                """
        res = con.execute(select_query, params)
        files_to_fetch = res.fetchall()
        return [i[0] for i in files_to_fetch]


def get_healthcheck() -> dict | None:
    """Compare hashes stored in index and in the storage. Return a mismatch report of None"""
    config = _get_config("local")
    DB_PATH, STORAGE_PATH = Path(config["db-path"]), Path(config["storage-path"])
    with sqlite3.connect(DB_PATH) as con:
        select_query = f"""
        SELECT
            sha256
        FROM "index"
        """
        index = con.execute(select_query).fetchall()
    storage_hashes = set(i.name for i in Path(STORAGE_PATH).iterdir())
    index_hashes = set(i[0] for i in index)

    missing_hashes = index_hashes.difference(storage_hashes)
    if missing_hashes:
        placeholders = ", ".join("?" for _ in missing_hashes)
        with sqlite3.connect(DB_PATH) as con:
            select_query = f"""
            SELECT
                id,
                name
            FROM "index"
            WHERE sha256 in ({placeholders})
            """
            res = con.execute(select_query, tuple(missing_hashes)).fetchall()
    else:
        res = []

    report = {
        "index-mismatch": res,
        "storage-mismatch": storage_hashes - index_hashes
    }

    if report["index-mismatch"] or report["storage-mismatch"]:
        return report
    return None


def set_user_config(key: str, value: str) -> None:
    """Exposed function to set the user config"""
    _set_config("user", key, value)
    return


def get_user_config() -> dict:
    """Exposed function to get user config"""
    return _get_config("user")


# get/set config - gets and sets config

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

    DB_PATH = Path(_get_config("local")["db-path"])

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

    STORAGE_PATH = Path(_get_config("local")["storage-path"])

    try:
        with open(source, mode="rb") as source_file:
            binary = source_file.read()
    except PermissionError as err:
        raise ImportError("Cannot read the given file: not enough permissions.") from err

    if not binary:
        raise ImportError("Cannot move empty files.")

    from hashlib import sha256
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

    return None


# --------------------------------------
# ------ Fetch related functions -------
# --------------------------------------

def fetch_file_set(
        id_: int | None = None,
        name: str | None = None,
        description_contains: str | None = None,
        date_created: DateInterval | None = None,
        date_added: DateInterval | None = None,
        tags: Sequence[str] = (),
        dry_run: bool = True,
        keep_existing: bool = False
) -> None | tuple[tuple[str, ...], ...]:
    """
    Fetch and serve file(s) that match the union (AND) of the specified restrictions.
    If multiple files match the set of restrictions, all matching are fetched.
    Unspecified restrictions (None) are ignored.

    dry_run: If true, do not fetch any files, but return a table + the number of potentially fetched ones.
    """
    local_config = _get_config("local")
    DB_PATH, STORAGE_PATH = Path(local_config["db-path"]), Path(local_config["storage-path"])

    ids = _get_feasible_file_set(id_, name, description_contains, date_created, date_added, tags)
    ids = [str(i) for i in ids]

    with sqlite3.connect(DB_PATH) as con:
        res = con.execute(f"""
        SELECT  
            id,
            sha256,
            name,
            description,
            date_created,
            date_added
        FROM "index"
        WHERE id in ({", ".join(ids)})
        """)
        files_to_fetch = res.fetchall()

    if dry_run:
        files_to_fetch = tuple(tuple(map(str, row)) for row in files_to_fetch)
        return files_to_fetch

    config = _get_config("user")

    # Empty dir regardless of the flag
    if not list(Path(config["landing-directory"]).iterdir()):
        for (_, hash_, name_, *_) in files_to_fetch:
            shutil.copy2(STORAGE_PATH / hash_, Path(config["landing-directory"]) / name_)
        return None

    # No flag, not empty
    if not keep_existing:
        raise FileExistsError("The landing directory is not empty.")

    # flag, not empty
    for (_, hash_, name_, *_) in files_to_fetch:
        target_file = Path(config["landing-directory"]) / name_
        if target_file.exists():
            new_name = "doc " + name_
            shutil.copy2(STORAGE_PATH / hash_, Path(config["landing-directory"]) / new_name)

    return None


# --------------------------------------
# ------- Drop related functions -------
# --------------------------------------
def _prepare_drop(id_: int) -> sqlite3.Connection:
    """
    Helper function to drop the given id from the table.
    Does not commit the drop, hence the name.
    Raises FileExistsError if the insert is duplicate
    """
    DB_PATH = Path(_get_config("local")["db-path"])
    con = sqlite3.connect(DB_PATH, autocommit=False)
    con.execute("PRAGMA foreign_keys = ON")  # Turned off by default for backwards compatibility
    res = con.execute("""DELETE
                         FROM "index"
                         WHERE id = ?""", (id_,))

    if res.rowcount == 0:
        con.rollback()
        con.close()
        raise IndexError(f"Id does not exist: {id_}")

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
    Helper function to build restriction(s) for a SELECT * WHERE clause.
    Parameters specify which dimensions to include.

    Returns an SQL-string ready for parameter insertion.
    Parameter names are:

    - (function parameter => SQL parameter)
    - id_ => id_
    - name => name
    - description_contains => description_contains
    - date_created => date_created_lower, date_created_upper
    - date_added => date_added_lower, date_added_upper
    - tags => tag0, tag1, ... (depending on how many tags passed)
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
    config = _get_config("local")
    DB_PATH, STORAGE_PATH = Path(config["db-path"]), Path(config["storage-path"])

    ids = _get_feasible_file_set(id_, name, description_contains, date_created, date_added, tags)
    ids = [str(i) for i in ids]

    with sqlite3.connect(DB_PATH) as con:
        res = con.execute(f"""
        SELECT 
            id, 
            sha256
        FROM "index"
        WHERE id in ({", ".join(ids)})
        """)
        files_to_drop = res.fetchall()

    if dry_run:
        return len(files_to_drop)

    for (i, hash_) in files_to_drop:
        con = _prepare_drop(i)
        Path(STORAGE_PATH / hash_).unlink(missing_ok=True)
        con.commit()
        con.close()

    return None
