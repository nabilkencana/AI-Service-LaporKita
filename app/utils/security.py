"""
Security utilities for LaporKita AI Service:
- SSRF Protection (blocks private, loopback, link-local, and internal metadata IP ranges)
- Image payload validation & dimension/size constraints (Rules.md §2.1)
"""

import io
import socket
import ipaddress
import urllib.parse
from typing import Optional
from PIL import Image
import requests

from app.core.config import settings
from app.core.logging import logger

# Set global PIL pixel limit to prevent decompression bombs (e.g. 10000x10000 images)
Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS


def is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address belongs to private, loopback, link-local, or reserved ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return True


def validate_url_for_ssrf(url: str) -> str:
    """
    Validate URL to protect against Server-Side Request Forgery (SSRF).
    Ensures URL scheme is http/https and resolved IP does not point to internal network.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Skema URL tidak didukung: '{parsed.scheme}'. Hanya http/https yang diperbolehkan.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL tidak memiliki hostname yang valid.")

    # Block localhost & common internal aliases directly
    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "metadata.google.internal"):
        raise ValueError(f"Akses ke host internal '{hostname}' dilarang (SSRF Protection).")

    # Resolve all IPs for the hostname and verify each
    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        for addr_info in addr_infos:
            ip_str = addr_info[4][0]
            if is_ip_blocked(ip_str):
                raise ValueError(
                    f"Akses ke host '{hostname}' (IP: {ip_str}) dilarang karena berada dalam jaringan privat/internal (SSRF Protection)."
                )
    except socket.gaierror as e:
        raise ValueError(f"Gagal me-resolve host '{hostname}': {e}") from e

    return url


def safe_fetch_image_from_url(url: str, max_bytes: Optional[int] = None, timeout: int = 10) -> bytes:
    """Safely fetch image from URL with SSRF validation and byte size enforcement."""
    validated_url = validate_url_for_ssrf(url)
    max_size = max_bytes or settings.MAX_IMAGE_SIZE_BYTES

    headers = {"User-Agent": "LaporKita-AI-Service/1.0"}
    try:
        with requests.get(validated_url, headers=headers, timeout=timeout, stream=True) as resp:
            resp.raise_for_status()

            # Check Content-Length header if present
            cl = resp.headers.get("Content-Length")
            if cl and int(cl) > max_size:
                raise ValueError(
                    f"Ukuran gambar ({int(cl) / (1024*1024):.2f} MB) melebihi batas maksimum {max_size / (1024*1024):.1f} MB (Rules.md §2.1)"
                )

            downloaded = 0
            chunks = []
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                downloaded += len(chunk)
                if downloaded > max_size:
                    raise ValueError(
                        f"Ukuran gambar yang diunduh melebihi batas maksimum {max_size / (1024*1024):.1f} MB (Rules.md §2.1)"
                    )
                chunks.append(chunk)

            return b"".join(chunks)
    except requests.RequestException as e:
        raise ValueError(f"Gagal mengunduh gambar dari URL: {e}") from e


def compute_image_sharpness(img: Image.Image) -> float:
    """
    Compute image sharpness score via variance of Laplacian on luminance channel.
    Calibrated thresholds:
    - variance < 15.0: extreme blur / out-of-focus / illegible image
    - variance >= 15.0: acceptable clarity for YOLO classification
    """
    import numpy as np
    gray = np.array(img.convert("L"), dtype=np.float64)
    # 3x3 Discrete Laplacian kernel
    lap = (
        np.roll(gray, 1, axis=0)
        + np.roll(gray, -1, axis=0)
        + np.roll(gray, 1, axis=1)
        + np.roll(gray, -1, axis=1)
        - 4.0 * gray
    )
    lap_inner = lap[1:-1, 1:-1]
    return float(np.var(lap_inner))


def validate_and_decode_image(img_bytes: bytes) -> Image.Image:
    """
    Validate image byte payload:
    - Enforces max size limit (8MB per Rules.md §2.1)
    - Verifies valid image format via PIL magic bytes
    - Enforces minimum resolution (longest edge >= 480px per RES-480)
    - Enforces maximum image dimension pixels
    """
    if len(img_bytes) > settings.MAX_IMAGE_SIZE_BYTES:
        raise ValueError(
            f"Ukuran file gambar ({len(img_bytes) / (1024*1024):.2f} MB) melebihi batas maksimum {settings.MAX_IMAGE_SIZE_BYTES / (1024*1024):.1f} MB (Rules.md §2.1)"
        )

    try:
        img_io = io.BytesIO(img_bytes)
        img = Image.open(img_io)
        img.verify()  # Verify header and integrity

        # Re-open after verify()
        img_io.seek(0)
        img = Image.open(img_io).convert("RGB")

        # Check dimensions: longest side must be at least MIN_IMAGE_DIMENSION (200px)
        longest_edge = max(img.width, img.height)
        if longest_edge < settings.MIN_IMAGE_DIMENSION:
            raise ValueError(
                f"Resolusi gambar ({img.width}x{img.height}) terlalu rendah. Sisi terpanjang minimal {settings.MIN_IMAGE_DIMENSION}px untuk menjamin akurasi klasifikasi."
            )

        if (img.width * img.height) > settings.MAX_IMAGE_PIXELS:
            raise ValueError(
                f"Resolusi gambar ({img.width}x{img.height}) terlalu besar (melebihi {settings.MAX_IMAGE_PIXELS} total piksel)."
            )

        return img
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Gambar tidak dapat dimuat: format file tidak valid atau rusak ({e})") from e
