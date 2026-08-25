import pytest
from app.services.streetview_service import StreetViewVerificationService


@pytest.fixture
def streetview_service():
    return StreetViewVerificationService.get_instance()


@pytest.mark.asyncio
async def test_malang_coordinate_verification(streetview_service):
    # Lowokwaru (Suhat), Malang
    result = await streetview_service.verify_location(-7.9431, 112.6148, "Jalan Berlubang")
    assert result["is_location_consistent"] is True
    assert result["location_match_confidence"] >= 0.70
    assert "Malang" in result["verified_address"]
    assert result["street_view_available"] is True


@pytest.mark.asyncio
async def test_outside_malang_coordinate_rejection(streetview_service):
    # Surabaya coordinates (outside Malang)
    result = await streetview_service.verify_location(-7.2575, 112.7521, "Jalan Berlubang")
    assert result["is_location_consistent"] is False
    assert result["location_match_confidence"] <= 0.10
    assert "Luar" in result["verified_address"] or "Luar" in result["location_audit_notes"]
