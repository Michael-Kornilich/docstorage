from src.parser import arg_parser
from src.db import (
    resolve_db,
    import_file,
    fetch_file_set,
    drop_file_set,
    get_healthcheck,
    get_overview
)
from src.utility import get_config, set_config
from datetime import date
from pathlib import Path


def tabulate_fileset(file_set: tuple[tuple[str, ...], ...]) -> str:
    """Create a table display of the given file set.
    Each tuple in the file set is expected to have the following properties in the order:
        file id
        hash
        name
        description
        date_created
        date_added
    """
    if len(file_set) == 0:
        return ""

    display_rows = []
    for file_id, hash_, name_, description, date_created_, date_added_ in file_set:
        if len(description) > 23:
            description = f"{description[:10]}...{description[-10:]}"
        display_rows.append((
            f"({file_id})",
            name_ or "-",
            description,
            date.fromisoformat(date_created_).strftime("%Y.%m.%d") if date_created_ else "",
            date.fromisoformat(date_added_).strftime("%Y.%m.%d") if date_added_ else "",
        ))

    if display_rows:
        from tabulate import tabulate

        table = tabulate(display_rows, headers=("Id", "Name", "Description", "Created on", "Added on"))
    else:
        table = ""
    total_files = f"Total {len(file_set)} files."
    return (table + "\n\n" + total_files).strip()


arg_namespace = arg_parser.parse_args()

try:
    resolve_db()
except Exception as err:
    raise RuntimeError(f"Couldn't resolve database: {err} ({type(err).__name__})") from err

match arg_namespace.command:
    case "import":
        try:
            import_file(
                source=Path(arg_namespace.source),
                description=arg_namespace.description if arg_namespace.description else "",
                date_created=arg_namespace.date_created if arg_namespace.date_created else date.today(),
                tags=arg_namespace.tags if arg_namespace.tags else tuple(),
            )
        except Exception as err:
            print(f"Couldn't import file: {err} ({type(err).__name__})")
        else:
            print("File imported successfully!")
    case "fetch":
        try:
            res = fetch_file_set(
                id_=arg_namespace.id,
                name=arg_namespace.name,
                description_contains=arg_namespace.description_contains,
                date_created=arg_namespace.date_created,
                date_added=arg_namespace.date_added,
                tags=arg_namespace.tags if arg_namespace.tags else tuple(),
                dry_run=arg_namespace.dry_run,
                keep_existing=arg_namespace.keep_existing,
            )
        except Exception as err:
            print(f"Couldn't fetch file: {err} ({type(err).__name__})")
            quit()

        if not arg_namespace.dry_run:
            print("File fetched successfully!")
        else:
            print(tabulate_fileset(res))
    case "delete":
        if arg_namespace.dry_run:
            matching_files = fetch_file_set(
                id_=arg_namespace.id,
                name=arg_namespace.name,
                description_contains=arg_namespace.description_contains,
                date_created=arg_namespace.date_created,
                date_added=arg_namespace.date_added,
                tags=arg_namespace.tags if arg_namespace.tags else tuple(),
                dry_run=True,
            )
            print("Matching files:", end="\n\n")
            print(tabulate_fileset(matching_files), end="\n\n")
            if arg_namespace.all:
                print("(the operation will delete all matching files)")
            if not arg_namespace.all and len(matching_files) > 1:
                print("(use --all to delete all matching files)")
            quit()

        try:
            n_matching_files = drop_file_set(
                id_=arg_namespace.id,
                name=arg_namespace.name,
                description_contains=arg_namespace.description_contains,
                date_created=arg_namespace.date_created,
                date_added=arg_namespace.date_added,
                tags=arg_namespace.tags if arg_namespace.tags else tuple(),
                dry_run=True,
            )
        except Exception as err:
            print(f"Couldn't inspect files: {err} ({type(err).__name__})")
            quit()

        if n_matching_files > 1 and not arg_namespace.all:
            print(f"Multiple files ({n_matching_files}) match the given criteria. Use --all to delete all of them.",
                  end="\n\n")
            quit()

        try:
            n_files = drop_file_set(
                id_=arg_namespace.id,
                name=arg_namespace.name,
                description_contains=arg_namespace.description_contains,
                date_created=arg_namespace.date_created,
                date_added=arg_namespace.date_added,
                tags=arg_namespace.tags if arg_namespace.tags else tuple(),
                dry_run=False,
            )
        except Exception as err:
            print(f"Couldn't drop file(s): {err} ({type(err).__name__})")
            quit()
        print("File(s) deleted successfully!")
    case "healthcheck":
        report = get_healthcheck()
        if report is None:
            print("Healthcheck passed: index and storage are in sync.")
        else:
            from tabulate import tabulate

            if report["index-mismatch"]:
                print("Index has the following entries without corresponding storage items:", end="\n\n")
                print(tabulate(report["index-mismatch"], headers=("Id", "Name")), end="\n\n")
            else:
                print("Index has the following entries without corresponding storage items: None", end="\n\n")

            missing_in_index = report["storage-mismatch"]
            if missing_in_index:
                print(f"The following files were found unexpectedly in the storage: "
                      f"{', '.join(missing_in_index)}")
            else:
                print(f"The following files were found unexpectedly in the storage: Nonea")
    case "overview":
        res = get_overview()
        print(f"Total files: {res['n-total-files']}")
        print(f"Tags used: {", ".join(res['unique-tags']) or 'None'}")
        if res["n-total-files"] > 0:
            print(f"Min date created: {res['min-max-dates'][0]}")
            print(f"Max date created: {res['min-max-dates'][1]}")
    case "config":
        if arg_namespace.config_command == "set":
            set_config("user", arg_namespace.field, arg_namespace.value)
            print("Configuration updated successfully!")
        elif arg_namespace.config_command == "list":
            config = get_config("user")
            for k, v in config.items():
                print(f"{k}: {v}")
