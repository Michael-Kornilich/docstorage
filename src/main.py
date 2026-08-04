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
        source = arg_namespace.source
        description = arg_namespace.description or ""
        date_created = arg_namespace.date_created or date.today()
        tags = arg_namespace.tags or tuple()
        import_file(source, description, date_created, tags)
        print("File imported successfully!")
    case "fetch":
        pass

# Display fetch dry run
# display_rows = []
# for file_id, hash_, name_, description, date_created_, date_added_ in files_to_fetch:
#     if len(description) > 23:
#         description = f"{description[:10]}...{description[-10:]}"
#     display_rows.append((
#         f"({file_id})",
#         name_,
#         description,
#         date.fromisoformat(date_created_).strftime("%Y.%m.%d"),
#         date.fromisoformat(date_added_).strftime("%Y.%m.%d"),
#     ))
#
# if display_rows:
#     from tabulate import tabulate
#     table = tabulate(display_rows, headers=("Id", "Name", "Description", "Created on", "Added on"))
# else:
#     table = ""
# total_files = f"\n\nTotal {len(files_to_fetch)} files."
# table + total_files
