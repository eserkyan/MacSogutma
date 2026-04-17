from __future__ import annotations

from django.urls import path

from apps.dashboard.consumers import DashboardConsumer

websocket_urlpatterns = [
    path("ws/dashboard/", DashboardConsumer.as_asgi()),
]
