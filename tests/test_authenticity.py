import pytest
from PIL import Image
import numpy as np
from app.services.authenticity_service import ImageAuthenticityService


@pytest.fixture
def auth_service():
    return ImageAuthenticityService.get_instance()


def test_authentic_image_analysis(auth_service):
    # Simulated authentic camera photo (uniform subtle noise)
    np.random.seed(42)
    clean_arr = (np.random.normal(120, 10, (256, 256, 3))).clip(0, 255).astype(np.uint8)
    clean_img = Image.fromarray(clean_arr)

    result = auth_service.analyze_image(clean_img, claimed_category="Jalan Berlubang")
    assert "is_authentic" in result
    assert "authenticity_score" in result
    assert result["authenticity_score"] >= 0.65
    assert result["is_authentic"] is True
    assert result["tampering_detected"] is False


def test_tampered_image_detection(auth_service):
    # Create image with artificial zero-noise pasted patch
    np.random.seed(42)
    tampered_arr = (np.random.normal(120, 15, (256, 256, 3))).clip(0, 255).astype(np.uint8)
    # Artificial smooth patch in the center
    tampered_arr[60:180, 60:180] = 30
    tampered_img = Image.fromarray(tampered_arr)

    result = auth_service.analyze_image(tampered_img, claimed_category="Jalan Berlubang")
    assert "is_authentic" in result
    assert "tampering_detected" in result
    assert "noise_uniformity_score" in result
