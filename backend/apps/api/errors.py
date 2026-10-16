from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from apps.core import (
    CoreError,
    UnsupportedCategory,
    UnsupportedCountry,
    UnsupportedLanguage,
    UnsupportedSubdivision,
    YearNotCovered,
    YearOutOfRange,
)

MESSAGES: dict[type[CoreError], Promise] = {
    UnsupportedCountry: _("Country %(value)s is not supported."),
    UnsupportedSubdivision: _("Subdivision %(value)s is not supported for %(country)s."),
    UnsupportedLanguage: _("Language %(value)s is not supported for %(country)s."),
    UnsupportedCategory: _("Categories not supported for %(country)s: %(value)s."),
    YearOutOfRange: _("Years must be between %(min)s and %(max)s."),
    YearNotCovered: _("Result falls outside the supported year range."),
}


def core_error_message(exc: CoreError) -> str:
    template = MESSAGES.get(type(exc))
    return str(template) % exc.params if template is not None else str(exc)
