from enum import Enum


class HolidayKindEnum(str, Enum):
    CLOSURE = "closure"
    HALF_DAY = "half_day"
    HOLIDAY = "holiday"

    def __str__(self) -> str:
        return str(self.value)
