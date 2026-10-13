"""
URL routing for dashboard app.
"""

from django.urls import path
from dashboard import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("statistics/", views.StatisticsView.as_view(), name="statistics"),
]
