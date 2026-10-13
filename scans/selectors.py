"""
Database selectors and analytics aggregations for scans app.
Encapsulates all queryset logic and user isolation.
"""

from collections import Counter
from datetime import timedelta
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from scans.models import Scan


def get_user_scans(user: User, result_class: str = None, limit: int = None):
    """Return scans for a specific user, optionally filtered by result class."""
    qs = Scan.objects.filter(user=user)
    if result_class and result_class in (Scan.CLASS_HEALTHY, Scan.CLASS_SUSPICIOUS, Scan.CLASS_DISEASED):
        qs = qs.filter(result_class=result_class)
    if limit:
        qs = qs[:limit]
    return qs


def get_user_scan_by_id(user: User, scan_id: int):
    """Retrieve a single scan ensuring user ownership."""
    try:
        return Scan.objects.get(id=scan_id, user=user)
    except Scan.DoesNotExist:
        return None


def get_dashboard_stats(user: User) -> dict:
    """Computes headline metrics, charts data, and recent items for the dashboard."""
    user_scans = Scan.objects.filter(user=user)
    total_scans = user_scans.count()

    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_scans = user_scans.filter(created_at__gte=start_of_month).count()

    healthy_count = user_scans.filter(result_class=Scan.CLASS_HEALTHY).count()
    suspicious_count = user_scans.filter(result_class=Scan.CLASS_SUSPICIOUS).count()
    diseased_count = user_scans.filter(result_class=Scan.CLASS_DISEASED).count()

    last_scan = user_scans.order_by("-created_at").first()
    recent_scans = user_scans.order_by("-created_at")[:5]

    # Top 5 most frequent diseases
    diseased_scans = user_scans.filter(
        result_class=Scan.CLASS_DISEASED
    ).exclude(disease_name="").values("disease_name", "crop_type").annotate(
        count=Count("id")
    ).order_by("-count")[:5]

    top_diseases = []
    for item in diseased_scans:
        top_diseases.append({
            "name": item["disease_name"],
            "crop": item["crop_type"] or "O'simlik",
            "count": item["count"],
        })

    # Last 6 months trend
    monthly_trend = []
    month_names_uz = [
        "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
        "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"
    ]
    for i in range(5, -1, -1):
        # approximate monthly bins
        m_date = now - timedelta(days=30 * i)
        m_start = m_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # next month start
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1)

        c = user_scans.filter(created_at__gte=m_start, created_at__lt=m_end).count()
        label = month_names_uz[m_start.month - 1]
        monthly_trend.append({"label": label, "count": c})

    return {
        "total_scans": total_scans,
        "month_scans": month_scans,
        "diseased_count": diseased_count,
        "healthy_count": healthy_count,
        "suspicious_count": suspicious_count,
        "last_scan": last_scan,
        "recent_scans": recent_scans,
        "top_diseases": top_diseases,
        "monthly_trend": monthly_trend,
    }


def get_detailed_statistics(user: User) -> dict:
    """Detailed analytics for the statistics page."""
    stats = get_dashboard_stats(user)
    user_scans = Scan.objects.filter(user=user)
    total = stats["total_scans"]

    # Calculate class percentages
    healthy_pct = round((stats["healthy_count"] / total * 100)) if total > 0 else 0
    suspicious_pct = round((stats["suspicious_count"] / total * 100)) if total > 0 else 0
    diseased_pct = round((stats["diseased_count"] / total * 100)) if total > 0 else 0

    # Calculate average confidence
    valid_scans = user_scans.exclude(confidence=None)
    avg_conf = 0
    if valid_scans.exists():
        conf_sum = sum(s.confidence_percent for s in valid_scans if s.confidence_percent is not None)
        avg_conf = round(conf_sum / valid_scans.count())

    # Breakdown by crop
    crop_counts = (
        user_scans.exclude(crop_type="")
        .values("crop_type")
        .annotate(total=Count("id"))
        .order_by("-total")[:8]
    )

    crop_breakdown = []
    for item in crop_counts:
        crop_name = item["crop_type"]
        c_total = item["total"]
        pct = round(c_total / total * 100) if total > 0 else 0
        crop_breakdown.append({
            "name": crop_name,
            "count": c_total,
            "pct": pct,
        })

    stats.update({
        "healthy_pct": healthy_pct,
        "suspicious_pct": suspicious_pct,
        "diseased_pct": diseased_pct,
        "avg_confidence": avg_conf,
        "crop_breakdown": crop_breakdown,
    })
    return stats
