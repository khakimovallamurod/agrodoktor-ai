"""
URL routes for scans app.
"""

from django.urls import path
from scans import views

urlpatterns = [
    path("new/", views.NewScanView.as_view(), name="new_scan"),
    path("history/", views.ScanHistoryView.as_view(), name="scan_history"),
    path("<int:scan_id>/", views.ScanDetailView.as_view(), name="scan_detail"),
    path("<int:scan_id>/delete/", views.ScanDeleteView.as_view(), name="scan_delete"),
]
