from typing import Tuple
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
