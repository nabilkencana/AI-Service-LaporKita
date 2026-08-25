import io
import base64
import pytest
from PIL import Image
from httpx import AsyncClient
from app.services.active_learning_service import ActiveLearningService


def create_dummy_base64_image(color=(100, 100, 100)) -> str:
    img = Image.new("RGB", (224, 224), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@pytest.fixture
def clean_service(tmp_path):
    svc = ActiveLearningService(base_dataset_dir=str(tmp_path / "dataset"))
    return svc


def test_ingest_sample_unit(clean_service):
    b64 = create_dummy_base64_image((120, 120, 120))
    res = clean_service.ingest_sample(
        image_base64=b64,
        verified_category="Jalan Berlubang",
        original_prediction="Trotoar",
        confidence_score=0.55,
        report_id="rep-001",
        operator_notes="Petugas DPUPR mengoreksi bahwa objek adalah lubang aspal.",
    )
    assert res["success"] is True
    assert res["is_correction"] is True
    assert res["target_category"] == "Jalan Berlubang"

    stats = clean_service.get_dataset_statistics()
    assert stats["total_samples"] == 1
    assert stats["corrections_from_human_operators"] == 1
    assert stats["class_distribution"]["Jalan_Berlubang"] == 1


@pytest.mark.asyncio
async def test_active_learning_api_endpoints(client: AsyncClient):
    b64 = create_dummy_base64_image((80, 80, 80))
    payload = {
        "image_base64": b64,
        "verified_category": "Drainase",
        "original_prediction": "Drainase",
        "confidence_score": 0.92,
        "report_id": "rep-test-api",
        "operator_notes": "Sumbatan drainase terkonfirmasi",
        "source": "operator_verified"
    }

    # Test Ingestion Endpoint
    resp = await client.post("/v1/training/ingest-sample", json=payload)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["target_category"] == "Drainase"
    assert data["is_correction"] is False

    # Test Stats Endpoint
    stats_resp = await client.get("/v1/training/dataset-stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()["data"]
    assert stats_data["total_samples"] >= 1
    assert "Drainase" in stats_data["class_distribution"]
