from app.utils.gps_validator import (
    is_valid_coordinate_range,
    is_within_malang_bbox,
    validate_report_coordinates,
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


def test_gps_validation_outside_malang():
    # Jakarta coords (-6.2088, 106.8456)
    lat, lon = -6.2088, 106.8456
    assert is_valid_coordinate_range(lat, lon) is True
    assert is_within_malang_bbox(lat, lon) is False
    valid, msg = validate_report_coordinates(lat, lon)
    assert valid is False


def test_gps_validation_invalid_range():
    assert is_valid_coordinate_range(95.0, 200.0) is False
    valid, _ = validate_report_coordinates(95.0, 200.0)
    assert valid is False


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
