from src.parser import arg_parser
from src.db import (
    resolve_db,
    import_file,
    fetch_file_set,
    drop_file_set,
    get_healthcheck,
    get_user_config,
    set_user_config
)
from datetime import date

arg_namespace = arg_parser.parse_args()

try:
    resolve_db()
except Exception as err:
    raise RuntimeError(f"Couldn't resolve database: {type(err).__name__} - {err}") from None

match arg_namespace.command:
    case "import":
        import_file(
            source=arg_namespace.source,
            description=arg_namespace.description if arg_namespace.description else "",
            date_created=arg_namespace.date_created if arg_namespace.date_created else date.today(),
            tags=arg_namespace.tags if arg_namespace.tags else tuple(),
        )
        print("File imported successfully!")
    case "fetch":
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
        if not arg_namespace.dry_run:
            print("File fetched successfully!")
        else:
            display_rows = []
            for file_id, hash_, name_, description, date_created_, date_added_ in res:
                if len(description) > 23:
                    description = f"{description[:10]}...{description[-10:]}"
                display_rows.append((
                    f"({file_id})",
                    name_,
                    description,
                    date.fromisoformat(date_created_).strftime("%Y.%m.%d"),
                    date.fromisoformat(date_added_).strftime("%Y.%m.%d"),
                ))

            if display_rows:
                from tabulate import tabulate

                table = tabulate(display_rows, headers=("Id", "Name", "Description", "Created on", "Added on"))
            else:
                table = ""
            total_files = f"\n\nTotal {len(res)} files."
            print(table + total_files)
    case "delete":
        matching_files = drop_file_set(
            id_=arg_namespace.id,
            name=arg_namespace.name,
            description_contains=arg_namespace.description_contains,
            date_created=arg_namespace.date_created,
            date_added=arg_namespace.date_added,
            tags=arg_namespace.tags if arg_namespace.tags else tuple(),
            dry_run=True,
        )
        if matching_files and matching_files > 1 and not arg_namespace.all:
            raise RuntimeError(
                f"Multiple files match the given criteria ({matching_files}); use --all to delete them."
            )

        drop_file_set(
            id_=arg_namespace.id,
            name=arg_namespace.name,
            description_contains=arg_namespace.description_contains,
            date_created=arg_namespace.date_created,
            date_added=arg_namespace.date_added,
            tags=arg_namespace.tags if arg_namespace.tags else tuple(),
            dry_run=arg_namespace.dry_run,
        )
        if not arg_namespace.dry_run:
            print("File(s) deleted successfully!")
    case "healthcheck":
        report = get_healthcheck()
        if report is None:
            print("Healthcheck passed: index and storage are in sync.")
        else:
            missing_storage = [i[0] for i in report['index-mismatch']]
            missing_in_index = report["storage-mismatch"]
            print(f"Files missing in storage: {', '.join(missing_storage)}.")
            print(f"Files missing in index: {', '.join(missing_in_index)}.")
    case "config":
        if arg_namespace.config_command == "set":
            set_user_config(arg_namespace.field, arg_namespace.value)
            print("Configuration updated successfully!")
        elif arg_namespace.config_command == "list":
            config = get_user_config()
            for k, v in config.items():
                print(f"{k}: {v}")
