from dataclasses import dataclass
from datetime import date
import argparse
import re


@dataclass(frozen=True)
class DateInterval:
    include_upper: bool = True
    include_lower: bool = True
    upper: date = date(9999, 12, 31)
    lower: date = date(1, 1, 1)

    def __post_init__(self):
        """
        Check types and if the given interval is valid
        """
        if not isinstance(self.lower, date):
            raise TypeError(f"The lower date must be a date. Got {type(self.lower).__name__}")
        if not isinstance(self.include_lower, bool):
            raise TypeError(f"The lower date inclusion must be boolean. Got {type(self.include_lower).__name__}")

        if not isinstance(self.upper, date):
            raise TypeError(f"The upper date must be a date. Got {type(self.upper).__name__}")
        if not isinstance(self.include_upper, bool):
            raise TypeError(f"The upper date inclusion must be boolean. Got {type(self.include_upper).__name__}")

        if self.lower == self.upper and not all([self.include_lower, self.include_upper]):
            raise ValueError("Invalid date interval: no dates exist with given restriction")


class UniqueCSV(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not values:
            setattr(namespace, self.dest, [])
            return

        items = [item.strip() for item in values.split(",") if item.strip()]
        if len(set(items)) != len(items):
            raise argparse.ArgumentError(self, "The given list contains duplicates")
        setattr(namespace, self.dest, items)


class ParseDateRange(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", values):
            try:
                parsed_date = date.fromisoformat(values)
            except ValueError as exc:
                raise argparse.ArgumentError(self, "expected a valid date in YYYY-MM-DD format") from exc
            setattr(namespace, self.dest, DateInterval(
                lower=parsed_date, upper=parsed_date,
                include_lower=True, include_upper=True,
            ))
            return

        closed_range_pattern = (
            r"\A(?P<left>>=|>|=)(?P<lower>\d{4}-\d{2}-\d{2}),(?P<right><=|<|=)(?P<upper>\d{4}-\d{2}-\d{2})\Z"
        )
        open_range_pattern = (
            r"\A(?P<operator>>=|>|<=|<|=)(?P<date>\d{4}-\d{2}-\d{2})\Z"
        )

        if match := re.match(closed_range_pattern, values):
            groupdict = match.groupdict()
            try:
                lower, upper = date.fromisoformat(groupdict["lower"]), date.fromisoformat(groupdict["upper"])
                date_interval = DateInterval(lower=lower, upper=upper,
                                             include_lower=groupdict["left"] in (">=", "="),
                                             include_upper=groupdict["right"] in ("<=", "="))
            except (ValueError, TypeError) as exc:
                raise argparse.ArgumentError(self, str(exc)) from exc
        elif match := re.match(open_range_pattern, values):
            groupdict = match.groupdict()
            try:
                parsed_date = date.fromisoformat(groupdict["date"])
                operator = groupdict["operator"]
                if operator in ("<", "<="):
                    date_interval = DateInterval(upper=parsed_date, include_upper=operator == "<=")
                elif operator in (">", ">="):
                    date_interval = DateInterval(lower=parsed_date, include_lower=operator == ">=")
                else:
                    date_interval = DateInterval(lower=parsed_date, upper=parsed_date,
                                                 include_lower=True, include_upper=True)
            except (ValueError, TypeError) as exc:
                raise argparse.ArgumentError(self, str(exc)) from exc
        else:
            raise argparse.ArgumentError(self,
                                         "Invalid date range format."
                                         " Expected {<|<=|>|>=|=}YYYY-MM-DD,{<|<=|>|>=|=}YYYY-MM-DD or"
                                         " {<|<=|>|>=|=}YYYY-MM-DD."
                                         f"Got '{values}'"
                                         )

        setattr(namespace, self.dest, date_interval)
        return


class ParseDate(argparse.Action):
    """Parse the import command's single YYYY-MM-DD date."""

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            parsed = date.fromisoformat(values)
        except ValueError as exc:
            raise argparse.ArgumentError(self, "expected a date in YYYY-MM-DD format") from exc
        setattr(namespace, self.dest, parsed)


def _limited_text(value):
    if len(value) > 300:
        raise argparse.ArgumentTypeError("must be at most 300 characters")
    return value


class _CLIArgumentParser(argparse.ArgumentParser):
    """Normalize the two mutually-exclusive name forms after parsing."""

    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args, namespace)
        if hasattr(parsed, "name_positional") or hasattr(parsed, "name_option"):
            positional = getattr(parsed, "name_positional", None)
            option = getattr(parsed, "name_option", None)
            parsed.name = positional if positional is not None else option
            delattr(parsed, "name_positional")
            delattr(parsed, "name_option")
        return parsed


def _add_filters(parser, *, include_dry_run=True):
    name_group = parser.add_mutually_exclusive_group()
    name_group.add_argument("name_positional", nargs="?", metavar="name", help="file name")
    name_group.add_argument("--name", "-n", dest="name_option", help="file name")
    parser.add_argument("--id", type=int, default=None)
    parser.add_argument("--description-contains", type=_limited_text, default=None, metavar="TEXT")
    parser.add_argument("--date-created", "-dc", action=ParseDateRange, default=None, metavar="DATE[,...]")
    parser.add_argument("--tags", "-t", action=UniqueCSV, default=[])
    if include_dry_run:
        parser.add_argument("--dry-run", action="store_true", default=False)


arg_parser = _CLIArgumentParser(prog="docstorage", description="Local document storage")
commands = arg_parser.add_subparsers(dest="command", required=True)

import_parser = commands.add_parser("import", help="ingest a file")
import_parser.add_argument("--description", "-de", type=_limited_text, default=None, metavar="TEXT")
import_parser.add_argument("--date-created", "-dc", action=ParseDate, default=date.today(), metavar="DATE")
import_parser.add_argument("--tags", "-t", action=UniqueCSV, default=[])
import_parser.add_argument("filepath", help="path to the file")

fetch_parser = commands.add_parser("fetch", help="copy matching files to the landing directory")
_add_filters(fetch_parser)
fetch_parser.add_argument("--keep-existing", action="store_true", default=False)

overview_parser = commands.add_parser("overview", help="show a document overview")
overview_parser.set_defaults(overview=True)

delete_parser = commands.add_parser("delete", help="delete matching documents")
_add_filters(delete_parser)
delete_parser.add_argument("--all", "-a", action="store_true", default=False)

healthcheck_parser = commands.add_parser("healthcheck", help="check stored file hashes")
healthcheck_parser.set_defaults(healthcheck=True)

config_parser = commands.add_parser("config", help="manage configuration")
config_commands = config_parser.add_subparsers(dest="config_command", required=True)
config_commands.add_parser("list", help="show current configuration")
set_parser = config_commands.add_parser("set", help="set a configuration field")
set_parser.add_argument("field")
set_parser.add_argument("value")
