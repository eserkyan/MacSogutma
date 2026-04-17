from __future__ import annotations

from django.urls import path

from apps.tests.views import (
    ActiveTestView,
    TestDeleteView,
    TestDetailView,
    TestExcelDownloadView,
    TestHistoryView,
    TestReportDownloadView,
    TestStartView,
)

app_name = "tests"

urlpatterns = [
    path("start/", TestStartView.as_view(), name="start"),
    path("active/", ActiveTestView.as_view(), name="active"),
    path("history/", TestHistoryView.as_view(), name="history"),
    path("<int:pk>/", TestDetailView.as_view(), name="detail"),
    path("<int:pk>/report/download/", TestReportDownloadView.as_view(), name="download_report"),
    path("<int:pk>/excel/download/", TestExcelDownloadView.as_view(), name="download_excel"),
    path("<int:pk>/delete/", TestDeleteView.as_view(), name="delete"),
]
