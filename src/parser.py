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
        if not isinstance(self.upper, date):
            raise TypeError(f"The upper date must be a date. Got {type(self.upper).__name__}")
        if not isinstance(self.lower, date):
            raise TypeError(f"The lower date must be a date. Got {type(self.lower).__name__}")

        if not isinstance(self.include_upper, bool):
            raise TypeError(f"The upper date inclusion must be boolean. Got {type(self.include_upper).__name__}")
        if not isinstance(self.include_lower, bool):
            raise TypeError(f"The lower date inclusion must be boolean. Got {type(self.include_lower).__name__}")

        if self.lower > self.upper:
            raise ValueError("Invalid date interval: the lower bound is bigger than the upper bound")
        if (self.lower == self.upper) and not all([self.include_lower, self.include_upper]):
            raise ValueError("Invalid date interval: no dates exist with given restriction")
        return


class UniqueCSV(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not values:
            return set()

        raw_items = values.split(",")
        items = [i for i in raw_items if i]
        if len(set(items)) != len(items):
            raise ValueError(f"The given list has duplicates in it")
        setattr(namespace, self.dest, set(items))


class ParseDateRange(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        closed_range_pattern = (
            r"\A(?P<lower_operator>>=)(?P<lower>\d{4}-\d{2}-\d{2}),"
            r"(?P<upper_operator><=)(?P<upper>\d{4}-\d{2}-\d{2})\Z"
        )
        open_range_pattern = (
            r"\A(?P<operator>>=|>|<=|<)(?P<date>\d{4}-\d{2}-\d{2})\Z"
        )

        if match := re.match(closed_range_pattern, values):
            groupdict = match.groupdict()
            date_interval = DateInterval(
                lower=groupdict["lower"],
                upper=groupdict["upper"],
                include_lower=True if "=" in groupdict["lower_operator"] else False,
                include_upper=True if "=" in groupdict["upper_operator"] else False
            )
        elif match := re.match(open_range_pattern, values):
            groupdict = match.groupdict()
            match groupdict["operator"]:
                case "<":
                    date_interval = DateInterval(upper=groupdict["date"], include_lower=False)
                case "<=":
                    date_interval = DateInterval(upper=groupdict["date"], include_lower=True)
                case ">":
                    date_interval = DateInterval(lower=groupdict["date"], include_lower=False)
                case ">=":
                    date_interval = DateInterval(lower=groupdict["date"], include_lower=True)
        else:
            raise ValueError(
                "Invalid date range format."
                "Expected {>|>=}YYYY-MM-DD,{<|<=}YYYY-MM-DD or {<|<=|>|>=|=}YYYY-MM-DD"
                f"Got '{values}'"
            )

        setattr(namespace, self.dest, date_interval)
        return
