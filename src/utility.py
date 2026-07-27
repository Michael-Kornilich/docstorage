from datetime import date
from dataclasses import dataclass


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
