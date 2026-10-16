class CoreError(ValueError):
    field = "non_field_errors"


class UnsupportedCountry(CoreError):
    field = "country"


class UnsupportedSubdivision(CoreError):
    field = "subdiv"


class UnsupportedLanguage(CoreError):
    field = "language"


class UnsupportedCategory(CoreError):
    field = "categories"


class YearOutOfRange(CoreError):
    field = "year"


class YearNotCovered(CoreError):
    pass
