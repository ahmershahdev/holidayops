from enum import Enum


class ReasonEnum(str, Enum):
    CLOSURE = "closure"
    CUSTOM_WORKING_DAY = "custom_working_day"
    HALF_DAY = "half_day"
    HOLIDAY = "holiday"
    WEEKEND = "weekend"
    WEEKEND_WORKDAY = "weekend_workday"
    WORKING_DAY = "working_day"

    def __str__(self) -> str:
        return str(self.value)
