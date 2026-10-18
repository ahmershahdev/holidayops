from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.holiday_kind_enum import HolidayKindEnum

T = TypeVar("T", bound="Holiday")


@_attrs_define
class Holiday:
    """
    Attributes:
        date (datetime.date):
        name (str):
        kind (HolidayKindEnum): * `holiday` - holiday
            * `closure` - closure
            * `half_day` - half_day
        sources (list[str]): Source countries (with subdivision) that contribute this holiday.
    """

    date: datetime.date
    name: str
    kind: HolidayKindEnum
    sources: list[str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        date = self.date.isoformat()

        name = self.name

        kind = self.kind.value

        sources = self.sources

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "date": date,
                "name": name,
                "kind": kind,
                "sources": sources,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        date = isoparse(d.pop("date")).date()

        name = d.pop("name")

        kind = HolidayKindEnum(d.pop("kind"))

        sources = cast(list[str], d.pop("sources"))

        holiday = cls(
            date=date,
            name=name,
            kind=kind,
            sources=sources,
        )

        holiday.additional_properties = d
        return holiday

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
