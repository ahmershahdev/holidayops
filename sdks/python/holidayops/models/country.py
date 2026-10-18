from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="Country")


@_attrs_define
class Country:
    """
    Attributes:
        code (str):
        name (str):
        subdivisions (list[str]):
        languages (list[str]):
        default_language (None | str):
        categories (list[str]):
        weekend (list[int]): Weekday numbers, Monday = 0.
    """

    code: str
    name: str
    subdivisions: list[str]
    languages: list[str]
    default_language: None | str
    categories: list[str]
    weekend: list[int]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        code = self.code

        name = self.name

        subdivisions = self.subdivisions

        languages = self.languages

        default_language: None | str
        default_language = self.default_language

        categories = self.categories

        weekend = self.weekend

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "code": code,
                "name": name,
                "subdivisions": subdivisions,
                "languages": languages,
                "default_language": default_language,
                "categories": categories,
                "weekend": weekend,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        code = d.pop("code")

        name = d.pop("name")

        subdivisions = cast(list[str], d.pop("subdivisions"))

        languages = cast(list[str], d.pop("languages"))

        def _parse_default_language(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        default_language = _parse_default_language(d.pop("default_language"))

        categories = cast(list[str], d.pop("categories"))

        weekend = cast(list[int], d.pop("weekend"))

        country = cls(
            code=code,
            name=name,
            subdivisions=subdivisions,
            languages=languages,
            default_language=default_language,
            categories=categories,
            weekend=weekend,
        )

        country.additional_properties = d
        return country

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
