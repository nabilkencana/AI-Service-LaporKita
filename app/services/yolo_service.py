"""
YOLOv11 Classification Service for LaporKita AI Verification.
Loads model once at service startup and provides thread-safe inference.
"""

import base64
import io
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image
import requests
from ultralytics import YOLO

from app.core.config import settings
import threading
from app.core.logging import logger


class YOLOClassificationService:
    _instance: Optional["YOLOClassificationService"] = None

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.CLASSIFICATION_MODEL_PATH
        self.model: Optional[YOLO] = None
        self._predict_lock = threading.Lock()
        self._load_model()

    @classmethod
    def get_instance(cls) -> "YOLOClassificationService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model(self):
        """Load YOLO classification model weights into memory once."""
        path = Path(self.model_path)
        if not path.exists():
            # If path not found, check relative to project root
            base_dir = Path(__file__).resolve().parent.parent.parent
            alt_path = base_dir / self.model_path
            if alt_path.exists():
                path = alt_path

        if path.exists():
            logger.info(f"Loading YOLOv11-cls model from {path.resolve()}...")
            self.model = YOLO(str(path.resolve()))
            logger.info(f"YOLOv11-cls model successfully loaded. Classes: {self.model.names}")
            # Pre-warm model once in single thread to fuse layers and initialize predictor
            try:
                dummy_img = Image.new("RGB", (224, 224), color=(128, 128, 128))
                self.model.predict(source=dummy_img, verbose=False)
            except Exception as e:
                logger.warning(f"Model pre-warm warning: {e}")
        else:
            logger.warning(f"Classification model file not found at {path}.")
            self.model = None

    def load_image(self, image_url: Optional[str] = None, image_base64: Optional[str] = None) -> Image.Image:
        """Convert input URL or Base64 string into a validated PIL RGB Image."""
        from app.utils.security import safe_fetch_image_from_url, validate_and_decode_image

        if image_base64:
            # Strip potential data URL prefix (e.g. data:image/jpeg;base64,...)
            if "," in image_base64:
                image_base64 = image_base64.split(",", 1)[1]
            try:
                img_bytes = base64.b64decode(image_base64)
            except Exception as e:
                raise ValueError(f"Gambar tidak dapat dimuat: format base64 tidak valid atau rusak ({e})") from e

            return validate_and_decode_image(img_bytes)

        elif image_url:
            img_bytes = safe_fetch_image_from_url(image_url)
            return validate_and_decode_image(img_bytes)

        raise ValueError("Gambar tidak dapat dimuat: gambar tidak disertakan")

    def compute_damage_severity_proxy(self, category: str, confidence: float) -> float:
        """
        Estimate damage severity score (0.0 to 1.0) as a proxy metric per ERD.md §2.4.
        
        CATATAN METODOLOGI:
        Karena model AI bekerja dalam mode KLASIFIKASI CITRA (bukan segmentasi/pengukuran
        luas pixel bounding box), nilai damage_severity diturunkan secara terukur sebagai
        proxy terkalibrasi dari confidence score model dikombinasikan dengan prioritas
        urgensi kategori default.
        """
        cat_weight = settings.DEFAULT_CATEGORY_WEIGHTS.get(category, 0.75)
        # Severity proxy formula: base scaled by confidence & category impact
        severity = (confidence * 0.6) + (cat_weight * 0.4)
        return round(max(0.1, min(1.0, severity)), 4)

    def predict(
        self,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        image_obj: Optional[Image.Image] = None,
    ) -> Tuple[str, float, Dict[str, float], float]:
        """
        Run classification inference on image.
        Returns: (predicted_category, confidence_score, all_class_probabilities, damage_severity)
        """
        img = image_obj or self.load_image(image_url, image_base64)
        if img is None:
            raise ValueError("Gambar tidak dapat dimuat atau format tidak valid")

        if self.model is None:
            logger.error("YOLOv11-cls model is not loaded in memory")
            raise RuntimeError("Model klasifikasi YOLOv11 tidak tersedia atau gagal dimuat")

        # Check image sharpness (DEG-ROBUST fix - calibrated threshold < 1.5 for heavy blur)
        from app.utils.security import compute_image_sharpness
        sharpness = compute_image_sharpness(img)
        is_blurry = sharpness < 1.5

        # Real YOLOv11-cls inference with thread lock to avoid race conditions during concurrent requests
        with self._predict_lock:
            results = self.model.predict(source=img, verbose=False)
        result = results[0]

        top1_idx = result.probs.top1
        top1_conf = float(result.probs.top1conf.cpu().item())
        pred_cat = self.model.names[top1_idx]

        # If image is heavily degraded/blurry, redirect to bukan_fasilitas
        if is_blurry and pred_cat != "bukan_fasilitas":
            logger.warning(f"Image sharpness score {sharpness:.2f} is below calibrated threshold 1.5 (blurry/degraded image). Classifying as bukan_fasilitas.")
            pred_cat = "bukan_fasilitas"
            top1_conf = max(top1_conf, 0.85)

        # Class probabilities mapping
        probs = {}
        for idx, cls_name in self.model.names.items():
            probs[cls_name] = round(float(result.probs.data[idx].cpu().item()), 4)

        severity = self.compute_damage_severity_proxy(pred_cat, top1_conf)

        return pred_cat, round(top1_conf, 4), probs, severity
