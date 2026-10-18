from django.contrib.sitemaps import views as sitemap_views
from django.urls import path, register_converter
from django.views.decorators.cache import cache_page

from apps.public import discovery, pages, tools, views
from apps.public.landing import landing
from apps.public.sitemaps import sitemaps
from apps.public.theme import set_theme


class LanguagePrefix:
    """`ur` or `ar`; English pages have no prefix."""

    regex = "ur|ar"

    def to_python(self, value: str) -> str:
        return value

    def to_url(self, value: str) -> str:
        return value


register_converter(LanguagePrefix, "lang")

SITEMAP_CACHE = 24 * 3600
SECTIONS = sitemaps()

_pages = [
    path("", landing),
    path("holidays/", views.country_index),
    path("holidays/<slug:country>/", views.country_latest),
    path("holidays/<slug:country>/today/", tools.country_today_view),
    path("holidays/<slug:country>/<int:year>/", views.year_view),
    path("holidays/<slug:country>/<str:subdiv>/<int:year>/", views.year_view),
    path("pricing/", views.pricing),
    path("today/", tools.today_index),
    path("tools/overlap/", tools.overlap_view),
    path("about/", pages.about),
    path("contact/", pages.contact),
    path("style/", views.style_guide),
]

urlpatterns = [
    *_pages,
    *[path(f"<lang:lang>/{p.pattern}", p.callback) for p in _pages],
    path("widget/<slug:country>/", tools.widget, name="widget"),
    path("privacy/", pages.privacy),
    path("terms/", pages.terms),
    path("offline/", pages.offline),
    path("robots.txt", discovery.robots, name="robots"),
    path("llms.txt", discovery.llms, name="llms"),
    path("llms-full.txt", discovery.llms_full, name="llms-full"),
    path("manifest.webmanifest", discovery.manifest, name="manifest"),
    path("sw.js", discovery.service_worker, name="service-worker"),
    path("theme/<str:choice>/", set_theme, name="theme"),
    path(
        "sitemap.xml",
        cache_page(SITEMAP_CACHE)(sitemap_views.index),
        {"sitemaps": SECTIONS, "sitemap_url_name": "sitemap-section"},
        name="sitemap",
    ),
    path(
        "sitemap-<section>.xml",
        cache_page(SITEMAP_CACHE)(sitemap_views.sitemap),
        {"sitemaps": SECTIONS},
        name="sitemap-section",
    ),
]
