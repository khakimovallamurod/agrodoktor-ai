"""
Views for accounts app: landing, demo login, logout, profile.
"""

import os
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.views import View


def get_slider_images():
    """
    Scans static/slider/ and media/slider/ for image files.
    Returns list of image dicts so the user can easily drop any images in static/slider/.
    """
    images = []
    valid_exts = (".jpg", ".jpeg", ".png", ".webp", ".svg")

    # 1. Scan static/slider/
    static_slider_dir = settings.BASE_DIR / "static" / "slider"
    if static_slider_dir.exists():
        for fname in sorted(os.listdir(static_slider_dir)):
            if fname.lower().endswith(valid_exts):
                title_clean = os.path.splitext(fname)[0].replace("_", " ").replace("-", " ").capitalize()
                images.append({
                    "url": f"{settings.STATIC_URL}slider/{fname}",
                    "title": title_clean,
                })

    # 2. Scan media/slider/
    media_slider_dir = settings.MEDIA_ROOT / "slider"
    if media_slider_dir.exists():
        for fname in sorted(os.listdir(media_slider_dir)):
            if fname.lower().endswith(valid_exts):
                title_clean = os.path.splitext(fname)[0].replace("_", " ").replace("-", " ").capitalize()
                images.append({
                    "url": f"{settings.MEDIA_URL}slider/{fname}",
                    "title": title_clean,
                })

    return images


class LandingView(View):
    """Public landing page. Authenticated users redirect to dashboard."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard")
        slider_images = get_slider_images()
        return render(request, "accounts/landing.html", {"slider_images": slider_images})


class DemoLoginView(View):
    """
    Instantly logs in the demo user on POST.
    No password typing required for testing/demo access.
    """

    def post(self, request):
        username = getattr(settings, "DEMO_USERNAME", "demo")
        first_name = getattr(settings, "DEMO_FIRST_NAME", "O'rolboy")
        last_name = getattr(settings, "DEMO_LAST_NAME", "Xakimov")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "is_active": True,
            },
        )
        if not user.first_name:
            user.first_name = first_name
            user.last_name = last_name
            user.save(update_fields=["first_name", "last_name"])

        login(request, user)
        messages.success(request, f"Xush kelibsiz, {user.first_name}!")
        return redirect("dashboard")


class LogoutView(View):
    """Logs out the current user and redirects to landing."""

    def post(self, request):
        logout(request)
        messages.info(request, "Tizimdan muvaffaqiyatli chiqdingiz.")
        return redirect("landing")


class ProfileView(LoginRequiredMixin, View):
    """Displays user profile details and summary metrics."""

    def get(self, request):
        user = request.user
        scans_qs = user.scans.all()
        total_scans = scans_qs.count()
        healthy_count = scans_qs.filter(result_class="healthy").count()
        suspicious_count = scans_qs.filter(result_class="suspicious").count()
        diseased_count = scans_qs.filter(result_class="diseased").count()

        context = {
            "total_scans": total_scans,
            "healthy_count": healthy_count,
            "suspicious_count": suspicious_count,
            "diseased_count": diseased_count,
        }
        return render(request, "accounts/profile.html", context)
