"""
========================================================================================
Image Authenticity & Anti-Tampering Service for LaporKita
========================================================================================
Detects digital alterations, AI inpainting (e.g. fake potholes generated onto real roads),
and image tampering using:
1. Error Level Analysis (ELA) - JPEG compression artifact inconsistency.
2. Sensor Noise Variance - High-frequency noise distribution across grid tiles.
3. Edge & Texture Discontinuity - Unnatural boundary transitions around damages.
========================================================================================
"""

import io
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
from PIL import Image, ImageChops
import cv2

from app.core.logging import logger


class ImageAuthenticityService:
    _instance: Optional["ImageAuthenticityService"] = None

    @classmethod
    def get_instance(cls) -> "ImageAuthenticityService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def analyze_image(
        self,
        image: Image.Image,
        claimed_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Performs multi-heuristic digital forensics on the submitted image.
        
        Returns:
            {
                "is_authentic": bool,
                "authenticity_score": float,  # 0.0 (likely fake/tampered) to 1.0 (authentic)
                "tampering_detected": bool,
                "ela_max_difference": float,
                "noise_uniformity_score": float,
                "tampering_indicators": List[str],
                "assessment_summary": str
            }
        """
        # Ensure image is in RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        tampering_indicators: List[str] = []
        deductions: float = 0.0

        # 1. Error Level Analysis (ELA)
        ela_score, ela_max_diff, ela_flag = self._compute_ela(image)
        if ela_flag:
            tampering_indicators.append("Anomali kompresi lokal (Error Level Analysis) terdeteksi pada area kerusakan.")
            deductions += 0.30

        # 2. Sensor Noise Uniformity Analysis
        noise_uniformity_score, noise_flag = self._compute_noise_uniformity(image)
        if noise_flag:
            tampering_indicators.append("Inkonsistensi derau sensor kamera (noise pattern) mengindikasikan area editan/inpainting AI.")
            deductions += 0.35

        # 3. Frequency / Edge Discontinuity Check
        edge_score, edge_flag = self._compute_edge_discontinuity(image)
        if edge_flag:
            tampering_indicators.append("Ditemukan batas transisi piksel tidak alami di sekitar objek kerusakan.")
            deductions += 0.25

        # Compute final authenticity score (bounded 0.05 to 0.99)
        base_authenticity = max(0.05, 1.0 - deductions)
        composite_score = (
            base_authenticity * 0.5 +
            (1.0 - min(ela_max_diff / 70.0, 1.0)) * 0.25 +
            noise_uniformity_score * 0.25
        )
        authenticity_score = round(float(np.clip(composite_score, 0.05, 0.99)), 3)
        tampering_detected = authenticity_score < 0.65 or len(tampering_indicators) >= 1 or deductions >= 0.30
        is_authentic = not tampering_detected

        if is_authentic:
            assessment_summary = "Citra terverifikasi otentik: Tidak ditemukan anomali kompresi atau manipulasi digital AI."
        else:
            assessment_summary = "Peringatan: Citra terindikasi mengalami manipulasi digital atau hasil generate AI (Inpainting)."

        logger.info(
            f"Authenticity Analysis: score={authenticity_score}, tampered={tampering_detected}, "
            f"ela_diff={ela_max_diff:.1f}, indicators={len(tampering_indicators)}"
        )

        return {
            "is_authentic": is_authentic,
            "authenticity_score": authenticity_score,
            "tampering_detected": tampering_detected,
            "ela_max_difference": round(ela_max_diff, 2),
            "noise_uniformity_score": round(noise_uniformity_score, 3),
            "tampering_indicators": tampering_indicators,
            "assessment_summary": assessment_summary,
        }

    def _compute_ela(self, image: Image.Image, quality: int = 90) -> Tuple[float, float, bool]:
        """
        Calculates Error Level Analysis (ELA) by re-compressing JPEG and computing difference map.
        """
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        recompressed = Image.open(buf)

        diff = ImageChops.difference(image, recompressed)
        diff_arr = np.asarray(diff, dtype=np.float32)

        max_diff = float(np.max(diff_arr))

        h, w, _ = diff_arr.shape
        grid_size = 32
        tile_means = []
        for y in range(0, h - grid_size + 1, grid_size):
            for x in range(0, w - grid_size + 1, grid_size):
                tile = diff_arr[y : y + grid_size, x : x + grid_size]
                tile_means.append(np.mean(tile))

        if len(tile_means) > 0:
            tile_std = float(np.std(tile_means))
            avg_tile = float(np.mean(tile_means)) + 1e-5
            relative_std = tile_std / avg_tile
            is_anomalous = relative_std > 1.8 and max_diff > 45.0
        else:
            is_anomalous = False

        ela_score = round(float(np.clip(1.0 - (max_diff / 100.0), 0.0, 1.0)), 3)
        return ela_score, max_diff, is_anomalous

    def _compute_noise_uniformity(self, image: Image.Image) -> Tuple[float, bool]:
        """
        Measures sensor noise variance across spatial tiles.
        """
        img_np = np.asarray(image)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

        blurred = cv2.medianBlur(gray, 3)
        noise_residual = cv2.absdiff(gray, blurred)

        h, w = noise_residual.shape
        block_size = 32
        block_stds = []

        for y in range(0, h - block_size + 1, block_size):
            for x in range(0, w - block_size + 1, block_size):
                block = noise_residual[y : y + block_size, x : x + block_size]
                block_stds.append(np.std(block))

        if len(block_stds) < 4:
            return 0.95, False

        std_of_stds = float(np.std(block_stds))
        mean_std = float(np.mean(block_stds)) + 1e-5
        coefficient_of_variation = std_of_stds / mean_std

        is_suspicious = coefficient_of_variation > 0.88
        uniformity_score = round(float(np.clip(1.0 - coefficient_of_variation * 0.8, 0.1, 0.99)), 3)

        return uniformity_score, is_suspicious

    def _compute_edge_discontinuity(self, image: Image.Image) -> Tuple[float, bool]:
        """
        Detects unnatural hard edges or blur halos caused by copy-pasting or mask blending.
        """
        img_np = np.asarray(image)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        lap_var = float(laplacian.var())

        is_suspicious = lap_var < 15.0 or lap_var > 6500.0
        score = 0.9 if not is_suspicious else 0.4
        return score, is_suspicious
