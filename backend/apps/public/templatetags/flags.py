from django import template
from django.utils.html import format_html
from django.utils.safestring import SafeString

from apps.public.flags import flag_url

register = template.Library()


@register.simple_tag
def flag(code: str, width: int = 24, lazy: bool = True) -> SafeString:
    """Decorative: the country's name is always next to it, so the image has empty alt text."""
    return format_html(
        '<img class="flag" src="{}" alt="" width="{}" height="{}" loading="{}" decoding="async">',
        flag_url(code),
        width,
        width * 3 // 4,
        "lazy" if lazy else "eager",
    )
