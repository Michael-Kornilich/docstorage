"""Database- and storage-related functions"""
import sqlite3
import shutil
from src.utility import DateInterval, get_config
from pathlib import Path
from datetime import date
from typing import Sequence
from contextlib import contextmanager


@contextmanager
def _open_transaction() -> sqlite3.Connection:
    """Yield an open SQLite transaction with PRAGMA foreign_keys = ON"""
    DB_PATH = get_config("local")["db-path"]
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("BEGIN")
    try:
        yield con
    except Exception:
        con.execute("ROLLBACK")
        raise
    else:
        con.execute("COMMIT")
    finally:
        con.close()
    return


def resolve_db() -> None:
    """
    Create a new index or check the validity of the existing one. Raises if DB and storage paths are misspecified.

    Create a new storage, if it does not exist.

    For both cases the whole path is created (mkdir -p)

    Get the storage and db paths from the local.josn config.

    Expected keys: 'db-path', 'storage-path'
    """

    config = get_config("local")
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
                       )
                       """.strip()
    create_tags_sql = """
                      CREATE TABLE "tags"
                      (
                          id  INTEGER REFERENCES "index" (id) ON DELETE CASCADE,
                          tag TEXT NOT NULL,
                          PRIMARY KEY (id, tag)
                      )
                      """.strip()

    if not STORAGE_PATH.exists():
        print("=> Storage path not found: creating a new one")
        STORAGE_PATH.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        # Won't handle the case where the index does not exist, but files do or the other way around
        # Since this is a very unlikely scenario
        # This code is assumed to be executed on the very first start of the app.
        print("=> Index not found: creating a new one")
        try:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            DB_PATH.touch()
        except FileNotFoundError:
            raise FileNotFoundError(f"Failed to create the index: bad path") from None
        except Exception as err:
            raise RuntimeError(f"An unexpected exception occured while creating index: "
                               f"{type(err).__name__} - {err}") from err

        with _open_transaction() as con:
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
    config = get_config("local")
    DB_PATH, STORAGE_PATH = Path(config["db-path"]), Path(config["storage-path"])

    where_restrictions = _build_where_restrictions(bool(id_), bool(name), bool(description_contains),
                                                   date_created, date_added, tags)

    params = locals().copy()

    # Prepare parameter for binding
    for param in ("date_added", "date_created"):
        if not params.get(param):
            continue
        params.update({
            f"{param}_lower": params[param].lower.isoformat(),
            f"{param}_upper": params[param].upper.isoformat(),
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
                {"WHERE " + where_restrictions if where_restrictions else ""}
                """
        res = con.execute(select_query, params)
        files_to_fetch = res.fetchall()
        return [i[0] for i in files_to_fetch]


def get_healthcheck() -> dict | None:
    """
    Compare hashes stored in index and in the storage. Return a mismatch report or None

    Report structure:

    'index-mismatch': [id, name] values that are in the index, but are missing from the storage

    'storage-mismatch': [hashes] values that are in the storage, but are missing from the index
    """
    config = get_config("local")
    _, STORAGE_PATH = Path(config["db-path"]), Path(config["storage-path"])
    with _open_transaction() as con:
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
        select_query = f"""
            SELECT
                id,
                name
            FROM "index"
            WHERE sha256 in ({placeholders})
        """
        with _open_transaction() as con:
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


# --------------------------------------
# ------ Import related functions ------
# --------------------------------------
def import_file(
        source: Path,
        description: str,
        date_created: date,
        tags: Sequence[str]
) -> None:
    """
    Moves the specified file into the internal storage and adds and entry to the index.
    Owns file checking. Path checking is done upstream
    Parameters are assumed true
    """

    STORAGE_PATH = Path(get_config("local")["storage-path"])

    try:
        with open(source, mode="rb") as source_file:
            binary = source_file.read()
    except PermissionError as err:
        raise ImportError("Cannot read the given file: not enough permissions.") from err
    if not binary:
        raise ImportError("Cannot move empty files.")

    from hashlib import sha256
    hexdigest = sha256(binary).hexdigest()

    insert_sql = """
                 INSERT INTO "index" (sha256, name, description, date_created)
                 VALUES (?, ?, ?, ?)
                 """
    params = (hexdigest, source.name, description, date_created.isoformat())
    try:
        with _open_transaction() as con:
            cursor = con.execute(insert_sql, params)
            index_id = cursor.lastrowid
            con.executemany(
                """INSERT INTO tags (id, tag)
                   VALUES (?, ?)""",
                [(index_id, tag) for tag in tags]
            )

            with open(STORAGE_PATH / hexdigest, mode="wb") as target_file:
                target_file.write(binary)
            source.unlink()
    except Exception as err:
        Path(STORAGE_PATH / hexdigest).unlink(missing_ok=True)
        raise ImportError(f"Could not update the index: {type(err).__name__} - {err}") from err

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

    None describes a non-existent condition. For example name=None means that the name is irrelevant in selection
    dry_run: If true, do not fetch any files, but return a tuple of potentially fetched ones.
    """
    local_config = get_config("local")
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

    config = get_config("user")

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
            while (Path(config["landing-directory"]) / new_name).exists():
                new_name = "doc " + new_name
            shutil.copy2(STORAGE_PATH / hash_, Path(config["landing-directory"]) / new_name)
        else:
            shutil.copy2(STORAGE_PATH / hash_, target_file)

    return None


def get_overview() -> dict:
    """
    Returns a dictionary of total number of files stored ("total-n-files": int),
    unique tags ("unique-tags": tuple), and the first and last date created ("min-max-dates": tuple with dates, or an empty tuple)
    """
    DB_PATH = Path(get_config("local")["db-path"])
    with sqlite3.connect(DB_PATH) as con:
        ids = con.execute("""SELECT COUNT(distinct id)
                             FROM "index" """).fetchall()
        n_files = ids[0][0]

        tags = con.execute("""SELECT distinct tag
                              FROM tags""").fetchall()
        tags = tuple(tag[0] for tag in tags)

        border_dates = con.execute("""SELECT min(date_created), max(date_created)
                                      FROM "index" """).fetchall()
        border_dates = border_dates[0]

        if all(border_dates):
            border_dates = tuple(date.fromisoformat(i) for i in border_dates)
        else:
            border_dates = tuple()

    return {"n-total-files": n_files, "unique-tags": tags, "min-max-dates": border_dates}


# --------------------------------------
# ------- Drop related functions -------
# --------------------------------------
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
    Tags: A file is considered a match if intersect of its tags is non-empty with the given tags

    dry_run: If true, do not drop any files, but return the number of potentially dropped files.
    """
    config = get_config("local")
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
        with _open_transaction() as con:
            con.execute("""DELETE
                           FROM "index"
                           WHERE id = ?""", (i,))
            Path(STORAGE_PATH / hash_).unlink(missing_ok=True)

    return None
