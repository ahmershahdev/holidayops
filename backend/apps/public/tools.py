"""Who is off today (world and per country), the embeddable widget and the overlap tool."""

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone, translation
from django.utils.html import escape
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_page
from django.views.decorators.clickjacking import xframe_options_exempt

from apps.core import list_countries
from apps.public.content import LANGUAGES, PREFIX, country_name, find_country, page_path
from apps.public.landing import reason_label
from apps.public.overlap import MAX_COUNTRIES, overlap, parse
from apps.public.seo import breadcrumbs, fit_title
from apps.public.today import country_today, local_today, today_path, world_today
from apps.public.views import PUBLIC_POLICY, _meta, public_page

FORM_POLICY = PUBLIC_POLICY.replace("form-action 'none'", "form-action 'self'")
# Other sites may frame the widget; it has no forms, scripts or user data.
WIDGET_POLICY = (
    "default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; "
    "form-action 'none'; frame-ancestors *"
)


@public_page
def today_index(request: HttpRequest, lang: str) -> HttpResponse:
    world = world_today(lang)
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/today/"),
        **breadcrumbs(request, lang, [(_("Who is off today"), f"{PREFIX[lang]}/today/")]),
        "title": _("Who is off today?"),
        "head_title": fit_title(_("Public holidays today around the world")),
        "description": _(
            "Countries on a public holiday or their weekend right now, each on its own local "
            "date, updated every hour."
        ),
        "world": world,
        "now": timezone.now(),
    }
    return render(request, "public/today.html", context)


@public_page
def country_today_view(request: HttpRequest, country: str, lang: str) -> HttpResponse:
    info = find_country(country)
    if info is None:
        raise Http404
    page = country_today(info, lang, local_today(info.code))
    name = page.name
    widget_url = request.build_absolute_uri(f"/widget/{info.code.lower()}/")
    context = {
        **_meta(request, lang, lambda code: today_path(code, info.code)),
        **breadcrumbs(
            request,
            lang,
            [
                (_("Holidays"), f"{PREFIX[lang]}/holidays/"),
                (name, page_path(lang, info.code, page.today.day.year)),
                (_("Today"), today_path(lang, info.code)),
            ],
        ),
        "title": _("Is today a working day in %(country)s?") % {"country": name},
        "head_title": fit_title(
            _("Is today a holiday in %(country)s?") % {"country": name},
            _("%(country)s today") % {"country": name},
        ),
        "description": _(
            "Today in %(country)s: working day or day off, the reason, this week at a glance "
            "and the next public holiday."
        )
        % {"country": name},
        "page": page,
        "reason": reason_label(page.today.reason),
        "week_reasons": [reason_label(d.reason) for d in page.week],
        "embed": (
            f'<iframe src="{escape(widget_url)}" title="{escape(name)}" width="320" height="150" '
            'style="border:0;border-radius:16px" loading="lazy"></iframe>'
        ),
        "widget_url": widget_url,
    }
    response = render(request, "public/country_today.html", context)
    # The page previews its own widget.
    response["Content-Security-Policy"] = PUBLIC_POLICY + "; frame-src 'self'"
    return response


@cache_page(15 * 60)
@xframe_options_exempt
def widget(request: HttpRequest, country: str) -> HttpResponse:
    info = find_country(country)
    if info is None:
        raise Http404
    lang = request.GET.get("lang", "en")
    lang = lang if lang in LANGUAGES else "en"
    theme = "dark" if request.GET.get("theme") == "dark" else "light"
    with translation.override(lang):
        page = country_today(info, lang, local_today(info.code))
        context = {
            "lang": lang,
            "dir": "rtl" if lang in {"ur", "ar"} else "ltr",
            "theme": theme,
            "page": page,
            "reason": reason_label(page.today.reason),
            "link": request.build_absolute_uri(today_path(lang, info.code)),
        }
        response = render(request, "public/widget.html", context)
    response["Content-Security-Policy"] = WIDGET_POLICY
    return response


@public_page
def overlap_view(request: HttpRequest, lang: str) -> HttpResponse:
    today = timezone.now().date()
    codes, first, error = parse(request.GET.getlist("c"), request.GET.get("month", ""), today)
    result = overlap(codes, first, lang) if len(codes) >= 2 else None
    choices = sorted(((c, country_name(c, lang)) for c in list_countries()), key=lambda c: c[1])
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/tools/overlap/"),
        **breadcrumbs(
            request, lang, [(_("Working-day overlap"), f"{PREFIX[lang]}/tools/overlap/")]
        ),
        "title": _("When do our offices all work?"),
        "head_title": fit_title(_("Working-day overlap between countries")),
        "description": _(
            "Compare up to four countries and see which days everyone works, and who is off on "
            "the others, holidays and weekends included."
        ),
        "choices": choices,
        "slots": [codes[i] if i < len(codes) else "" for i in range(MAX_COUNTRIES)],
        "month_value": first.strftime("%Y-%m"),
        "error": error,
        "result": result,
    }
    response = render(request, "public/overlap.html", context)
    response["Content-Security-Policy"] = FORM_POLICY
    return response
