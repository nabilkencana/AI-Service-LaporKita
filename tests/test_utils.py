from datetime import datetime, timezone, timedelta
from app.utils.gps_validator import (
    is_valid_coordinate_range,
    is_within_malang_bbox,
    validate_report_coordinates,
    validate_report_timestamp,
)
from app.utils.scoring import (
    normalize_support_count,
    normalize_density_factor,
    calculate_urgency_score,
)
from app.core.config import settings


def test_gps_validation_inside_malang():
    # Malang center coords (-7.9826, 112.6308)
    lat, lon = -7.9826, 112.6308
    assert is_valid_coordinate_range(lat, lon) is True
    assert is_within_malang_bbox(lat, lon) is True
    valid, msg = validate_report_coordinates(lat, lon)
    assert valid is True


def test_gps_validation_exact_bbox_boundaries():
    # Test boundary edges of Malang BBox
    assert is_within_malang_bbox(settings.MALANG_BBOX_MIN_LAT, settings.MALANG_BBOX_MIN_LON) is True
    assert is_within_malang_bbox(settings.MALANG_BBOX_MAX_LAT, settings.MALANG_BBOX_MAX_LON) is True
    # Just outside bounds
    assert is_within_malang_bbox(settings.MALANG_BBOX_MIN_LAT - 0.001, 112.6308) is False
    assert is_within_malang_bbox(settings.MALANG_BBOX_MAX_LAT + 0.001, 112.6308) is False


def test_gps_validation_outside_malang():
    # Jakarta coords (-6.2088, 106.8456)
    lat, lon = -6.2088, 106.8456
    assert is_valid_coordinate_range(lat, lon) is True
    assert is_within_malang_bbox(lat, lon) is False
    valid, msg = validate_report_coordinates(lat, lon)
    assert valid is False


def test_gps_validation_invalid_range():
    assert is_valid_coordinate_range(95.0, 200.0) is False
    assert is_valid_coordinate_range(-95.0, 100.0) is False
    assert is_valid_coordinate_range(0.0, -185.0) is False
    valid, _ = validate_report_coordinates(95.0, 200.0)
    assert valid is False


def test_timestamp_validation_edge_cases():
    now = datetime.now(timezone.utc)

    # 1. Current time is valid
    valid, _ = validate_report_timestamp(now)
    assert valid is True

    # 2. None timestamp is invalid (RULES-1: must be provided per Rules.md §1.2)
    valid, msg = validate_report_timestamp(None)
    assert valid is False
    assert "tidak disertakan" in msg

    # 3. 4 minutes in future (within 5 min tolerance) -> Valid
    valid, _ = validate_report_timestamp(now + timedelta(minutes=4))
    assert valid is True

    # 4. 10 minutes in future (exceeds 5 min tolerance) -> Invalid
    valid, msg = validate_report_timestamp(now + timedelta(minutes=10))
    assert valid is False
    assert "masa depan" in msg

    # 5. 29 days past (within 30 days limit) -> Valid
    valid, _ = validate_report_timestamp(now - timedelta(days=29))
    assert valid is True

    # 6. 35 days past (exceeds 30 days limit) -> Invalid
    valid, msg = validate_report_timestamp(now - timedelta(days=35))
    assert valid is False
    assert "lampau" in msg


def test_scoring_normalization():
    assert normalize_support_count(0) == 0.0
    assert normalize_support_count(50) == 0.5
    assert normalize_support_count(200) == 1.0  # capped at 1.0

    assert normalize_density_factor(0) == 0.0
    assert normalize_density_factor(25) == 0.5
    assert normalize_density_factor(100) == 1.0  # capped at 1.0


def test_scoring_formula():
    score = calculate_urgency_score(
        damage_severity=0.8,
        support_count=20,
        report_density=10,
        category_name="Jalan Berlubang",
    )
    # Check that score is bounded between 0 and 1
    assert 0.0 <= score <= 1.0

    # Test with max parameters
    max_score = calculate_urgency_score(
        damage_severity=1.0,
        support_count=100,
        report_density=50,
        category_name="Jalan Berlubang",
    )
    assert max_score <= 1.0
    assert max_score > 0.8

    # Test fallback category urgency
    unknown_score = calculate_urgency_score(
        damage_severity=0.5,
        support_count=10,
        report_density=5,
        category_name="KategoriNonEksis",
    )
    assert 0.0 <= unknown_score <= 1.0
