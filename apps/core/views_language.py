from __future__ import annotations

from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.views import View

from apps.core.ui_translations import LANGUAGE_OPTIONS


class SetLanguageView(View):
    def post(self, request: HttpRequest) -> HttpResponseRedirect:
        language = request.POST.get("language", "tr")
        allowed = {code for code, _ in LANGUAGE_OPTIONS}
        request.session["ui_language"] = language if language in allowed else "tr"
        next_url = request.POST.get("next") or reverse("dashboard:index")
        return HttpResponseRedirect(next_url)
