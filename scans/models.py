"""
Scan model for AgroDoktor.
Stores plant health analysis records, image references, and AI diagnostics.
"""

import os
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


def scan_upload_path(instance, filename):
    """Upload plant images under media/scans/<user_id>/<YYYY-MM>/<filename>."""
    now = timezone.now()
    clean_name = os.path.basename(filename)
    return f"scans/{instance.user_id}/{now.strftime('%Y-%m')}/{clean_name}"


def scan_thumb_upload_path(instance, filename):
    """Upload plant thumbnails under media/scans/<user_id>/<YYYY-MM>/thumbs/<filename>."""
    now = timezone.now()
    clean_name = os.path.basename(filename)
    return f"scans/{instance.user_id}/{now.strftime('%Y-%m')}/thumbs/{clean_name}"


class Scan(models.Model):
    """Represents a single plant health analysis record."""

    STATUS_OK = "ok"
    STATUS_INVALID = "invalid"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_OK, "Muvaffaqiyatli"),
        (STATUS_INVALID, "Noto'g'ri rasm"),
        (STATUS_ERROR, "Xatolik"),
    ]

    CLASS_HEALTHY = "healthy"
    CLASS_SUSPICIOUS = "suspicious"
    CLASS_DISEASED = "diseased"
    CLASS_CHOICES = [
        (CLASS_HEALTHY, "Sog'lom"),
        (CLASS_SUSPICIOUS, "Kuzatuv talab etadi"),
        (CLASS_DISEASED, "Kasallik aniqlandi"),
    ]

    DISEASE_TYPE_CHOICES = [
        ("fungal", "Zamburug'li"),
        ("bacterial", "Bakteriyali"),
        ("viral", "Virusli"),
        ("pest", "Zararkunanda"),
        ("nutrient", "Oziqa yetishmovchiligi"),
        ("other", "Boshqa"),
        ("none", "Mavjud emas"),
    ]

    SEVERITY_CHOICES = [
        ("none", "Mavjud emas"),
        ("low", "Past daraja"),
        ("medium", "O'rta daraja"),
        ("high", "Yuqori daraja"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scans")
    image = models.ImageField(upload_to=scan_upload_path)
    thumbnail = models.ImageField(upload_to=scan_thumb_upload_path, blank=True, null=True)

    crop_type = models.CharField(max_length=60, blank=True)
    field_name = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OK)
    result_class = models.CharField(
        max_length=20, choices=CLASS_CHOICES, null=True, blank=True
    )
    plant_name = models.CharField(max_length=120, blank=True)
    disease_name = models.CharField(max_length=120, blank=True)
    disease_type = models.CharField(
        max_length=30, choices=DISEASE_TYPE_CHOICES, default="none", blank=True
    )
    severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES, default="none", blank=True
    )
    confidence = models.FloatField(null=True, blank=True)

    summary = models.TextField(blank=True)
    observations = models.JSONField(default=list, blank=True)
    causes = models.JSONField(default=list, blank=True)
    treatment = models.JSONField(default=list, blank=True)
    prevention = models.JSONField(default=list, blank=True)
    when_to_call_agronomist = models.TextField(blank=True)
    invalid_reason = models.TextField(blank=True)

    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]
        verbose_name = "O'simlik tekshiruvi"
        verbose_name_plural = "O'simlik tekshiruvlari"

    def __str__(self):
        plant = self.plant_name or self.crop_type or "O'simlik"
        label = self.class_label_uz
        return f"Scan #{self.pk} – {plant}: {label} ({self.created_at:%Y-%m-%d})"

    def delete(self, *args, **kwargs):
        """Remove physical image and thumbnail files when deleting record."""
        image_path = None
        thumb_path = None
        if self.image:
            try:
                image_path = self.image.path
            except Exception:
                pass
        if self.thumbnail:
            try:
                thumb_path = self.thumbnail.path
            except Exception:
                pass

        super().delete(*args, **kwargs)

        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass
        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except OSError:
                pass

    @property
    def class_color(self):
        """Return the semantic color key: emerald, amber, rose, or slate."""
        return {
            self.CLASS_HEALTHY: "emerald",
            self.CLASS_SUSPICIOUS: "amber",
            self.CLASS_DISEASED: "rose",
        }.get(self.result_class, "slate")

    @property
    def class_label_uz(self):
        """Human-readable Uzbek label for result class."""
        return {
            self.CLASS_HEALTHY: "Sog'lom",
            self.CLASS_SUSPICIOUS: "Kuzatuv talab etadi",
            self.CLASS_DISEASED: "Kasallik aniqlandi",
        }.get(self.result_class, "Noma'lum")

    @property
    def confidence_percent(self):
        """Safe 0-100 integer confidence percentage."""
        if self.confidence is None:
            return None
        if self.confidence <= 1.0:
            return round(self.confidence * 100)
        return round(self.confidence)
