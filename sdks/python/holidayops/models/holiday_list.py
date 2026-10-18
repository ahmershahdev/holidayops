from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.holiday import Holiday


T = TypeVar("T", bound="HolidayList")


@_attrs_define
class HolidayList:
    """
    Attributes:
        country (None | str):
        calendar (None | UUID):
        subdiv (None | str):
        year (int):
        language (None | str):
        categories (list[str]):
        holidays (list[Holiday]):
    """

    country: None | str
    calendar: None | UUID
    subdiv: None | str
    year: int
    language: None | str
    categories: list[str]
    holidays: list[Holiday]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        country: None | str
        country = self.country

        calendar: None | str
        if isinstance(self.calendar, UUID):
            calendar = str(self.calendar)
        else:
            calendar = self.calendar

        subdiv: None | str
        subdiv = self.subdiv

        year = self.year

        language: None | str
        language = self.language

        categories = self.categories

        holidays = []
        for holidays_item_data in self.holidays:
            holidays_item = holidays_item_data.to_dict()
            holidays.append(holidays_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "country": country,
                "calendar": calendar,
                "subdiv": subdiv,
                "year": year,
                "language": language,
                "categories": categories,
                "holidays": holidays,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.holiday import Holiday

        d = dict(src_dict)

        def _parse_country(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        country = _parse_country(d.pop("country"))

        def _parse_calendar(data: object) -> None | UUID:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                calendar_type_0 = UUID(data)

                return calendar_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | UUID, data)

        calendar = _parse_calendar(d.pop("calendar"))

        def _parse_subdiv(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        subdiv = _parse_subdiv(d.pop("subdiv"))

        year = d.pop("year")

        def _parse_language(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        language = _parse_language(d.pop("language"))

        categories = cast(list[str], d.pop("categories"))

        holidays = []
        _holidays = d.pop("holidays")
        for holidays_item_data in _holidays:
            holidays_item = Holiday.from_dict(holidays_item_data)

            holidays.append(holidays_item)

        holiday_list = cls(
            country=country,
            calendar=calendar,
            subdiv=subdiv,
            year=year,
            language=language,
            categories=categories,
            holidays=holidays,
        )

        holiday_list.additional_properties = d
        return holiday_list

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
