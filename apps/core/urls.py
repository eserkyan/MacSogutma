from __future__ import annotations

from django.urls import path

from apps.core.views import SettingsActionView, SettingsView
from apps.core.views_language import SetLanguageView

app_name = "core"

urlpatterns = [
    path("", SettingsView.as_view(), name="settings"),
    path("actions/", SettingsActionView.as_view(), name="settings_actions"),
    path("language/", SetLanguageView.as_view(), name="set_language"),
]
