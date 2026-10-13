"""
Views for dashboard app: overview metrics and statistics.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from scans.selectors import get_dashboard_stats, get_detailed_statistics


class DashboardView(LoginRequiredMixin, View):
    """Main dashboard displaying headline KPIs, quick actions, charts, and recent scans."""

    def get(self, request):
        stats = get_dashboard_stats(request.user)
        return render(request, "dashboard/dashboard.html", {"stats": stats})


class StatisticsView(LoginRequiredMixin, View):
    """Dedicated analytics page with detailed breakdown and historical trends."""

    def get(self, request):
        stats = get_detailed_statistics(request.user)
        return render(request, "dashboard/statistics.html", {"stats": stats})
