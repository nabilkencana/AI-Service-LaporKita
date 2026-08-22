"""
========================================================================================
Google Gemini LLM Policy Simulator Service for LaporKita
========================================================================================
Implements PRD.md §4.2 & ERD.md §2.13:
- Provides structured executive policy analysis and quantitative impact projections.
- Enforces strict JSON output via Gemini response_mime_type="application/json".
- Validates output using Pydantic schemas before returning to client.
- Implements strict timeout and error handling.
========================================================================================
"""

import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, List
from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import logger
from app.schemas.policy_simulator import PolicySimulateData, PolicyProjectionData

SYSTEM_INSTRUCTION = """
Anda adalah AI Konsultan Perencanaan Tata Kota & Analis Kebijakan Publik untuk Pemerintah Kota Malang (LaporKita Policy Simulator).
Tugas Anda adalah mensimulasikan dampak kebijakan publik/intervensi infrastruktur perkotaan berdasarkan skenario yang diajukan oleh pengambil kebijakan (Dinas PUPR, Dishub, atau Bappeda Kota Malang).

Anda WAJIB memberikan respons dalam format JSON valid dengan struktur persis berikut:
{
  "result_narrative": "Narasi analisis komprehensif (3-5 paragraf) mencakup latar belakang, dampak operasional di Kota Malang, efektivitas intervensi, mitigasi risiko sosial, dan proyeksi jangka menengah/panjang.",
  "result_data": {
    "estimated_incident_reduction_pct": 35.5,
    "budget_estimate_idr": 450000000.0,
    "time_to_impact_weeks": 6,
    "target_department": "Dinas Pekerjaan Umum, Penataan Ruang, Perumahan dan Kawasan Permukiman (DPUPRPKP) Kota Malang",
    "public_satisfaction_increase_pct": 28.0,
    "risk_mitigations": [
      "Sosialisasi rekayasa lalu lintas berkala kepada warga",
      "Pemasangan rambu keselamatan kerja pada zona proyek"
    ]
  },
  "key_recommendations": [
    "Langkah rekomendasi konkret 1",
    "Langkah rekomendasi konkret 2",
    "Langkah rekomendasi konkret 3"
  ]
}

Aturan:
1. Angka proyeksi pada 'result_data' harus realistis untuk skala kota tingkat dua di Indonesia (Kota Malang).
2. Bahasa pengantar adalah Bahasa Indonesia formal dan profesional.
3. Seluruh output harus murni JSON tanpa markdown enclosure seperti ```json di luar format.
"""


class GeminiServiceError(Exception):
    def __init__(self, code: str, message: str, details: Optional[Any] = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class GeminiPolicyService:
    _instance: Optional["GeminiPolicyService"] = None
    _executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=4)

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL_NAME
        self.client: Optional[genai.Client] = None
        self._init_client()

    @classmethod
    def get_instance(cls) -> "GeminiPolicyService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_client(self):
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini API client initialized successfully with model '{self.model_name}'")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")
                self.client = None
        else:
            logger.warning("GEMINI_API_KEY is not configured. Policy Simulator will return fallback structure.")
            self.client = None

    async def simulate_policy(
        self,
        prompt_text: str,
        zone_id: Optional[str] = None,
        time_horizon_months: int = 6,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 20.0,
    ) -> PolicySimulateData:
        """
        Execute Policy Simulation with Gemini LLM and parse into strictly validated Pydantic model.
        """
        if not self.client:
            raise GeminiServiceError(
                code="GEMINI_KEY_NOT_CONFIGURED",
                message="Gemini API Key belum dikonfigurasi di environment server.",
            )

        # Construct contextual prompt
        context_lines = [
            f"Skenario / Usulan Kebijakan: {prompt_text}",
            f"Horizon Waktu Proyeksi: {time_horizon_months} bulan",
        ]
        if zone_id:
            context_lines.append(f"Zona Wilayah Spesifik: {zone_id}")
        if parameters:
            context_lines.append(f"Parameter Konteks Tambahan: {json.dumps(parameters, ensure_ascii=False)}")

        full_prompt = "\n".join(context_lines)

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.25,
            system_instruction=SYSTEM_INSTRUCTION,
        )

        def _call_gemini_sync():
            return self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=config,
            )

        # Asynchronously run with strict timeout
        loop = asyncio.get_running_loop()
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(self._executor, _call_gemini_sync),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(f"Gemini API timed out after {timeout_seconds}s")
            raise GeminiServiceError(
                code="GEMINI_TIMEOUT",
                message=f"Permintaan simulasi kebijakan ke Gemini API melebihi batas waktu ({timeout_seconds}s).",
            )
        except Exception as e:
            logger.error(f"Gemini API request failed: {e}")
            raise GeminiServiceError(
                code="GEMINI_API_ERROR",
                message=f"Terjadi kesalahan saat memanggil Gemini API: {str(e)}",
            )

        # Parse & Validate Output
        raw_text = response.text or ""
        return self._parse_and_validate_response(raw_text)

    def _parse_and_validate_response(self, raw_text: str) -> PolicySimulateData:
        """Parse raw LLM output into JSON and validate through Pydantic."""
        try:
            clean_text = raw_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()

            parsed_json = json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode Gemini JSON response: {e}. Raw text snippet: {raw_text[:200]}")
            raise GeminiServiceError(
                code="GEMINI_PARSE_ERROR",
                message="Output dari Gemini API bukan merupakan format JSON yang valid.",
                details={"raw_snippet": raw_text[:300]},
            )

        try:
            # Validate projection data schema
            result_data_raw = parsed_json.get("result_data", {})
            projection_obj = PolicyProjectionData(**result_data_raw)

            data = PolicySimulateData(
                result_narrative=parsed_json.get("result_narrative", ""),
                result_data=projection_obj.model_dump(),
                key_recommendations=parsed_json.get("key_recommendations", []),
                model_used=self.model_name,
                is_placeholder=False,
            )
            return data
        except ValidationError as ve:
            logger.error(f"Gemini output failed Pydantic schema validation: {ve}")
            raise GeminiServiceError(
                code="GEMINI_SCHEMA_ERROR",
                message="Struktur data proyeksi dari Gemini tidak memenuhi skema Pydantic yang ditentukan.",
                details=ve.errors(),
            )
