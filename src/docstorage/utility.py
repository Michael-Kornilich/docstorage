from datetime import date
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DateInterval:
    include_upper: bool = True
    include_lower: bool = True
    # Includes both to simplify handling of an open bound
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

        if self.lower > self.upper:
            raise ValueError("Invalid date interval: no dates exist with given restriction")

        if self.upper == date(9999, 12, 31) and self.lower == date(1, 1, 1):
            from warnings import warn
            warn("Degenerate date interval")

    def __contains__(self, date_: date) -> bool:
        if not isinstance(date_, date):
            raise TypeError(f"The date must be a date. Got {type(date_).__name__}")

        if self.lower < date_ < self.upper:
            return True
        if (self.include_lower and date_ == self.lower) or (not self.include_upper and date_ == self.upper):
            return True

        return False


def freeze(it: Iterable, /):
    """Recursively turns lists and sets into tuples"""
    res = []
    for i in it:
        if hasattr(i, "__iter__") and not isinstance(i, str):
            i = freeze(i)
        res.append(i)
    return tuple(res)


def tabulate_fileset(file_set: tuple[tuple[str, ...], ...]) -> str:
    """Create a table display of the given file set.
    Each tuple in the file set is expected to have the following properties in the order:
        file id
        hash
        name
        description
        date_created
        date_added
        tuple[tags]
    """
    if len(file_set) == 0:
        return ""

    display_rows = []
    for file_id, hash_, name_, description, date_created_, date_added_, tags_ in file_set:
        if len(description) > 23:
            description = f"{description[:10]}...{description[-10:]}"
        display_rows.append((
            f"({file_id})",
            name_ or "-",
            description,
            date.fromisoformat(date_created_).strftime("%Y.%m.%d") if date_created_ else "",
            date.fromisoformat(date_added_).strftime("%Y.%m.%d") if date_added_ else "",
            ", ".join(tags_),
        ))

    if display_rows:
        from tabulate import tabulate

        table = tabulate(display_rows, headers=("Id", "Name", "Description", "Created on", "Added on"))
    else:
        table = ""

    return table.strip()
