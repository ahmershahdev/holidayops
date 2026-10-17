from collections.abc import Iterable
from datetime import date

from babel.dates import format_date
from django import template
from django.utils import translation

from apps.public.content import join_list

register = template.Library()


@register.filter
def cldr(day: date, pattern: str) -> str:
    """CLDR day and month names, the same the web app gets from Intl: Django's own differ in
    places (Urdu Saturday as ھفتہ instead of ہفتہ). Digits stay Latin, as elsewhere."""
    return format_date(day, pattern, locale=translation.get_language() or "en")


@register.filter
def as_list(items: Iterable[str]) -> str:
    return join_list(items, translation.get_language() or "en")
