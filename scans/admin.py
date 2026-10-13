"""
Django admin registration for scans app.
"""

from django.contrib import admin
from scans.models import Scan


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "plant_name",
        "crop_type",
        "result_class",
        "status",
        "confidence",
        "created_at",
    )
    list_filter = ("result_class", "status", "crop_type", "created_at")
    search_fields = ("user__username", "plant_name", "disease_name", "field_name", "notes")
    readonly_fields = ("created_at",)
