from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerSplitView

from apps.api import views

urlpatterns = [
    path("countries/", views.CountryListView.as_view(), name="countries"),
    path("holidays/", views.HolidayListView.as_view(), name="holidays"),
    path("business-days/check/", views.CheckView.as_view(), name="business-days-check"),
    path("business-days/add/", views.AddView.as_view(), name="business-days-add"),
    path("business-days/between/", views.BetweenView.as_view(), name="business-days-between"),
    path("business-days/range/", views.RangeView.as_view(), name="business-days-range"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.orgs.urls")),
    path("", include("apps.notifications.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerSplitView.as_view(url_name="schema"), name="docs"),
]
