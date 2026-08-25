"""
========================================================================================
Active Learning & Continuous Training Ingestion Service for LaporKita
========================================================================================
Collects and structures verified citizen report images into categorized training datasets.
Features:
1. Ingest verified samples from operator actions (Human-in-the-Loop ground truth).
2. Organize into standard classification directory format (YOLOv11-cls compatible).
3. Log audit metadata in JSONL for tracking data lineage and model drift.
4. Provide real-time dataset statistics.
========================================================================================
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from PIL import Image
import io

from app.core.logging import logger
from app.core.config import settings
from app.utils.security import validate_and_decode_image, safe_fetch_image_from_url


class ActiveLearningService:
    _instance: Optional["ActiveLearningService"] = None

    def __init__(self, base_dataset_dir: Optional[str] = None):
        if base_dataset_dir:
            self.base_dir = Path(base_dataset_dir)
        else:
            # Default to data/active_learning in ai-service directory
            self.base_dir = Path(__file__).resolve().parent.parent.parent / "data" / "active_learning"
        
        self.labeled_dir = self.base_dir / "labeled"
        self.metadata_file = self.base_dir / "dataset_metadata.jsonl"
        self._ensure_directories()

    @classmethod
    def get_instance(cls) -> "ActiveLearningService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_directories(self):
        """Creates dataset directories for all valid classes."""
        self.labeled_dir.mkdir(parents=True, exist_ok=True)
        valid_classes = [
            "Jalan_Berlubang",
            "Trotoar",
            "Drainase",
            "Lampu_Jalan",
            "Rambu_Lalu_Lintas",
            "bukan_fasilitas",
        ]
        for cls_name in valid_classes:
            (self.labeled_dir / cls_name).mkdir(parents=True, exist_ok=True)

    def _sanitize_class_name(self, category: str) -> str:
        """Converts user-friendly category name into a directory-safe string."""
        mapping = {
            "Jalan Berlubang": "Jalan_Berlubang",
            "Trotoar": "Trotoar",
            "Drainase": "Drainase",
            "Lampu Jalan": "Lampu_Jalan",
            "Rambu Lalu Lintas": "Rambu_Lalu_Lintas",
            "bukan_fasilitas": "bukan_fasilitas",
        }
        return mapping.get(category, category.replace(" ", "_"))

    def ingest_sample(
        self,
        image_base64: Optional[str] = None,
        image_url: Optional[str] = None,
        verified_category: str = "Jalan Berlubang",
        original_prediction: Optional[str] = None,
        confidence_score: float = 0.0,
        report_id: Optional[str] = None,
        operator_notes: Optional[str] = None,
        source: str = "operator_verified"
    ) -> Dict[str, Any]:
        """
        Saves a verified sample into the active learning dataset pool.
        """
        # 1. Load and validate image
        pil_img: Image.Image
        if image_base64:
            if "," in image_base64:
                image_base64 = image_base64.split(",", 1)[1]
            raw_bytes = base64.b64decode(image_base64)
            pil_img = validate_and_decode_image(raw_bytes)
        elif image_url:
            raw_bytes = safe_fetch_image_from_url(image_url)
            pil_img = validate_and_decode_image(raw_bytes)
        else:
            raise ValueError("image_base64 atau image_url wajib disertakan")

        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        # 2. Determine target file path
        sanitized_cls = self._sanitize_class_name(verified_category)
        target_folder = self.labeled_dir / sanitized_cls
        target_folder.mkdir(parents=True, exist_ok=True)

        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_report_id = (report_id or "sample").replace("/", "_").replace("\\", "_")
        filename = f"{timestamp_str}_{safe_report_id}.jpg"
        save_path = target_folder / filename

        # Standardize size (e.g. max 640px) to save storage & match YOLO resolution
        pil_img.thumbnail((640, 640), Image.Resampling.LANCZOS)
        pil_img.save(save_path, format="JPEG", quality=90)

        # 3. Append to JSONL metadata ledger
        metadata_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "report_id": report_id,
            "filename": filename,
            "relative_path": f"labeled/{sanitized_cls}/{filename}",
            "verified_category": verified_category,
            "sanitized_class": sanitized_cls,
            "original_prediction": original_prediction,
            "initial_confidence": confidence_score,
            "operator_notes": operator_notes,
            "source": source,
            "is_correction": original_prediction != verified_category if original_prediction else False,
        }

        with open(self.metadata_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(metadata_entry, ensure_ascii=False) + "\n")

        logger.info(f"Ingested active learning sample: {save_path.name} -> {sanitized_cls}")

        return {
            "success": True,
            "saved_file": str(save_path.name),
            "target_category": verified_category,
            "is_correction": metadata_entry["is_correction"],
            "total_samples_in_class": len(list(target_folder.glob("*.jpg"))),
        }

    def get_dataset_statistics(self) -> Dict[str, Any]:
        """Returns the distribution and count of samples in the active dataset."""
        stats = {}
        total_samples = 0

        for class_dir in self.labeled_dir.iterdir():
            if class_dir.is_dir():
                count = len(list(class_dir.glob("*.jpg")) + list(class_dir.glob("*.png")) + list(class_dir.glob("*.jpeg")))
                stats[class_dir.name] = count
                total_samples += count

        corrections_count = 0
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            if data.get("is_correction"):
                                corrections_count += 1
            except Exception as e:
                logger.warning(f"Error reading metadata: {e}")

        return {
            "total_samples": total_samples,
            "corrections_from_human_operators": corrections_count,
            "class_distribution": stats,
            "dataset_directory": str(self.base_dir),
            "ready_for_retraining": total_samples >= 20,
        }

    def create_dataset_zip(self) -> io.BytesIO:
        """Packages the labeled dataset directory and metadata into a zip in memory."""
        import zipfile
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(self.base_dir):
                for file in files:
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.base_dir)
                    zip_file.write(file_path, arcname=str(rel_path))
        zip_buffer.seek(0)
        return zip_buffer
