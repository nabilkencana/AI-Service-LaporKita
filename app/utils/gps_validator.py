from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from app.core.config import settings


def is_valid_coordinate_range(latitude: float, longitude: float) -> bool:
    """Validate that latitude and longitude are in valid geographical bounds."""
    return -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0


def is_within_malang_bbox(latitude: float, longitude: float) -> bool:
    """Check if GPS coordinate is within the pilot bounding box of Kota Malang (Rules.md §2.1)."""
    if not is_valid_coordinate_range(latitude, longitude):
        return False

    return (
        settings.MALANG_BBOX_MIN_LAT <= latitude <= settings.MALANG_BBOX_MAX_LAT
        and settings.MALANG_BBOX_MIN_LON <= longitude <= settings.MALANG_BBOX_MAX_LON
    )


def validate_report_coordinates(latitude: float, longitude: float) -> Tuple[bool, str]:
    """Validate report coordinates and return (is_valid, reason)."""
    if not is_valid_coordinate_range(latitude, longitude):
        return False, "Koordinat latitude atau longitude tidak valid secara geografis"

    if not is_within_malang_bbox(latitude, longitude):
        return False, "Lokasi berada di luar wilayah pilot Kota Malang"

    return True, "Lokasi valid di Kota Malang"


def validate_report_timestamp(
    report_time: Optional[datetime],
    max_age_days: int = 30,
    max_future_minutes: int = 5,
) -> Tuple[bool, str]:
    """
    Validate report capture timestamp per Rules.md §1.2:
    - Must not be in the future (with 5-minute clock drift tolerance).
    - Must not be excessively old (default max 30 days).
    """
    if report_time is None:
        return False, "Timestamp tidak disertakan (wajib disertakan sesuai Rules.md §1.2)"

    now = datetime.now(timezone.utc)
    if report_time.tzinfo is None:
        # If naive datetime, assume UTC or local converted
        dt_target = report_time.replace(tzinfo=timezone.utc)
    else:
        dt_target = report_time

    future_limit = now + timedelta(minutes=max_future_minutes)
    if dt_target > future_limit:
        return False, "Timestamp foto berada di masa depan (anomali metadata)"

    past_limit = now - timedelta(days=max_age_days)
    if dt_target < past_limit:
        return False, f"Timestamp foto terlalu lampau (> {max_age_days} hari)"

    return True, "Timestamp foto valid"
