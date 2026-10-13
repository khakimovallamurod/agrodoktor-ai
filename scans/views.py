"""
Views for scans app: New scan, Detail, History, Delete, and Sample runner.
"""

import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from scans.forms import ScanUploadForm
from scans.models import Scan
from scans.selectors import get_user_scan_by_id, get_user_scans
from scans.services.gemini import analyze_plant_image
from scans.services.image_utils import clean_and_resize_image, generate_thumbnail

logger = logging.getLogger(__name__)


class NewScanView(LoginRequiredMixin, View):
    """Handles plant image capture/upload and triggers AI analysis."""

    def get(self, request):
        form = ScanUploadForm()
        return render(request, "scans/new_scan.html", {"form": form})

    def post(self, request):
        form = ScanUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(
                request,
                "Rasm yuklashda xatolik yuz berdi. Iltimos, ma'lumotlarni tekshiring.",
            )
            return render(request, "scans/new_scan.html", {"form": form})

        raw_image = form.cleaned_data["image"]
        crop_type = form.cleaned_data.get("crop_type", "")
        field_name = form.cleaned_data.get("field_name", "")
        notes = form.cleaned_data.get("notes", "")

        try:
            # Clean EXIF/GPS, auto-orient, max 1280px
            clean_image = clean_and_resize_image(raw_image)
            clean_image.seek(0)
            image_bytes = clean_image.read()
            clean_image.seek(0)

            # Generate 400px thumbnail
            thumbnail_image = generate_thumbnail(clean_image)
            clean_image.seek(0)

            # Call AI analysis service
            ai_result = analyze_plant_image(
                image_bytes=image_bytes,
                mime_type="image/jpeg",
                crop_hint=crop_type,
            )

            # Handle service connection failure
            if ai_result.get("error"):
                scan = Scan.objects.create(
                    user=request.user,
                    image=clean_image,
                    thumbnail=thumbnail_image,
                    crop_type=crop_type,
                    field_name=field_name,
                    notes=notes,
                    status=Scan.STATUS_ERROR,
                    invalid_reason=ai_result.get(
                        "error_message", "AI xizmatiga ulanib bo'lmadi."
                    ),
                    raw_response=ai_result,
                )
                messages.error(
                    request,
                    ai_result.get(
                        "error_message",
                        "AI tahlilida xatolik yuz berdi. Qayta urinib ko'ring.",
                    ),
                )
                return redirect("scan_detail", scan_id=scan.id)

            # Handle invalid image (not a plant, too dark/blurry)
            if not ai_result.get("valid"):
                scan = Scan.objects.create(
                    user=request.user,
                    image=clean_image,
                    thumbnail=thumbnail_image,
                    crop_type=crop_type,
                    field_name=field_name,
                    notes=notes,
                    status=Scan.STATUS_INVALID,
                    invalid_reason=ai_result.get(
                        "invalid_reason",
                        "Rasmda o'simlik qismi aniqlanmadi. Iltimos, o'simlik bargi yoki mevasini aniqroq suratga oling.",
                    ),
                    raw_response=ai_result,
                )
                messages.warning(
                    request,
                    "Rasm talabga javob bermadi. Iltimos, yangi rasm oling.",
                )
                return redirect("scan_detail", scan_id=scan.id)

            # Valid scan
            scan = Scan.objects.create(
                user=request.user,
                image=clean_image,
                thumbnail=thumbnail_image,
                crop_type=crop_type or ai_result.get("plant_name", ""),
                field_name=field_name,
                notes=notes,
                status=Scan.STATUS_OK,
                result_class=ai_result.get("class", Scan.CLASS_SUSPICIOUS),
                plant_name=ai_result.get("plant_name", crop_type or "O'simlik"),
                disease_name=ai_result.get("disease_name", ""),
                disease_type=ai_result.get("disease_type", "none"),
                severity=ai_result.get("severity", "none"),
                confidence=ai_result.get("confidence", 0.85),
                summary=ai_result.get("summary", ""),
                observations=ai_result.get("observations", []),
                causes=ai_result.get("causes", []),
                treatment=ai_result.get("treatment", []),
                prevention=ai_result.get("prevention", []),
                when_to_call_agronomist=ai_result.get("when_to_call_agronomist", ""),
                raw_response=ai_result,
            )

            messages.success(request, "O'simlik tahlili muvaffaqiyatli yakunlandi!")
            return redirect("scan_detail", scan_id=scan.id)

        except Exception as exc:
            logger.exception("Rasm qayta ishlash yoki tahlil qilishda kutilmagan xatolik: %s", exc)
            messages.error(
                request,
                "Rasmni tahlil qilishda kutilmagan xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            )
            return render(request, "scans/new_scan.html", {"form": form})


class ScanDetailView(LoginRequiredMixin, View):
    """Detailed diagnostic view for a single scan."""

    def get(self, request, scan_id):
        scan = get_user_scan_by_id(request.user, scan_id)
        if not scan:
            raise Http404("Tekshiruv topilmadi.")

        context = {
            "scan": scan,
        }
        return render(request, "scans/scan_detail.html", context)


class ScanHistoryView(LoginRequiredMixin, View):
    """Paginated scan history with class filter chips."""

    def get(self, request):
        class_filter = request.GET.get("filter", "all")
        allowed_filters = {
            "all": None,
            "healthy": Scan.CLASS_HEALTHY,
            "suspicious": Scan.CLASS_SUSPICIOUS,
            "diseased": Scan.CLASS_DISEASED,
        }
        selected_class = allowed_filters.get(class_filter)

        scans_qs = get_user_scans(request.user, result_class=selected_class)
        paginator = Paginator(scans_qs, 10)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # Count per category for filter badges
        all_user_scans = Scan.objects.filter(user=request.user)
        counts = {
            "all": all_user_scans.count(),
            "healthy": all_user_scans.filter(result_class=Scan.CLASS_HEALTHY).count(),
            "suspicious": all_user_scans.filter(result_class=Scan.CLASS_SUSPICIOUS).count(),
            "diseased": all_user_scans.filter(result_class=Scan.CLASS_DISEASED).count(),
        }

        context = {
            "page_obj": page_obj,
            "current_filter": class_filter,
            "counts": counts,
        }
        return render(request, "scans/history.html", context)


class ScanDeleteView(LoginRequiredMixin, View):
    """Deletes a scan record and attached files."""

    def post(self, request, scan_id):
        scan = get_object_or_404(Scan, id=scan_id, user=request.user)
        scan.delete()
        messages.success(request, "Tekshiruv natijasi muvaffaqiyatli o'chirildi.")
        return redirect("scan_history")
