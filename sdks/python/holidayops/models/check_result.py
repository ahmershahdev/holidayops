from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.reason_enum import ReasonEnum

T = TypeVar("T", bound="CheckResult")


@_attrs_define
class CheckResult:
    """
    Attributes:
        date (datetime.date):
        is_business_day (bool):
        reason (ReasonEnum): * `working_day` - working_day
            * `weekend` - weekend
            * `holiday` - holiday
            * `weekend_workday` - weekend_workday
            * `closure` - closure
            * `half_day` - half_day
            * `custom_working_day` - custom_working_day
        holidays (list[str]):
        half_day (bool):
    """

    date: datetime.date
    is_business_day: bool
    reason: ReasonEnum
    holidays: list[str]
    half_day: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        date = self.date.isoformat()

        is_business_day = self.is_business_day

        reason = self.reason.value

        holidays = self.holidays

        half_day = self.half_day

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "date": date,
                "is_business_day": is_business_day,
                "reason": reason,
                "holidays": holidays,
                "half_day": half_day,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        date = isoparse(d.pop("date")).date()

        is_business_day = d.pop("is_business_day")

        reason = ReasonEnum(d.pop("reason"))

        holidays = cast(list[str], d.pop("holidays"))

        half_day = d.pop("half_day")

        check_result = cls(
            date=date,
            is_business_day=is_business_day,
            reason=reason,
            holidays=holidays,
            half_day=half_day,
        )

        check_result.additional_properties = d
        return check_result

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
