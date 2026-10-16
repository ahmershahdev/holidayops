from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.api import views

urlpatterns = [
    path("countries/", views.CountryListView.as_view(), name="countries"),
    path("holidays/", views.HolidayListView.as_view(), name="holidays"),
    path("business-days/check/", views.CheckView.as_view(), name="business-days-check"),
    path("business-days/add/", views.AddView.as_view(), name="business-days-add"),
    path("business-days/between/", views.BetweenView.as_view(), name="business-days-between"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
