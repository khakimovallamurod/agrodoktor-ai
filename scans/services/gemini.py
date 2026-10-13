"""
AI plant health analysis service for AgroDoktor.
Uses the official google-genai SDK strictly in backend.
"""

import json
import logging
import time
from django.conf import settings
from scans.services.prompts import SYSTEM_PROMPT, ANALYSIS_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# Module-level import so tests can patch 'scans.services.gemini.genai'
try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]


def _build_crop_hint_info(crop_hint: str = None) -> str:
    """Format optional farmer-provided crop hint."""
    if crop_hint and crop_hint.strip() and crop_hint.strip() != "Boshqa":
        return f"Fermer ko'rsatgan ekin turi: {crop_hint.strip()}."
    return ""


def _parse_response(text: str) -> dict:
    """Parse JSON response text, safely stripping markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


def analyze_plant_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    crop_hint: str = None,
) -> dict:
    """
    Sends plant image bytes to the AI backend and returns structured analysis dictionary.

    Returns dict matching schema:
    {
      "valid": bool,
      "invalid_reason": str,
      "plant_name": str,
      "class": "healthy" | "suspicious" | "diseased",
      "disease_name": str,
      "disease_type": str,
      "severity": str,
      "confidence": float,
      "summary": str,
      "observations": list,
      "causes": list,
      "treatment": list,
      "prevention": list,
      "when_to_call_agronomist": str,
      "raw_text": str,
    }
    On error returns dict with: {"valid": False, "error": True, "error_message": str}
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

    if not api_key:
        logger.error("GEMINI_API_KEY sozlanmagan.")
        return {
            "valid": False,
            "error": True,
            "error_message": "AI xizmati kaliti sozlanmagan. Iltimos, administratorga murojaat qiling.",
        }

    if genai is None:
        logger.error("google-genai kutubxonasi yuklanmadi.")
        return {
            "valid": False,
            "error": True,
            "error_message": "AI xizmati tizimda mavjud emas. Qayta urinib ko'ring.",
        }

    crop_hint_info = _build_crop_hint_info(crop_hint)
    prompt_text = ANALYSIS_PROMPT_TEMPLATE.format(crop_hint_info=crop_hint_info)

    client = genai.Client(api_key=api_key)

    max_attempts = 3
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    genai_types.Part.from_text(text=prompt_text),
                ],
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )

            raw_text = response.text or ""
            result = _parse_response(raw_text)
            result["raw_text"] = raw_text

            # Enforce required schema defaults
            if "valid" not in result:
                result["valid"] = True

            if result.get("valid"):
                valid_classes = {"healthy", "suspicious", "diseased"}
                if result.get("class") not in valid_classes:
                    result["class"] = "suspicious"

                # Ensure lists
                for list_field in ("observations", "causes", "treatment", "prevention"):
                    if not isinstance(result.get(list_field), list):
                        result[list_field] = []

                if "confidence" in result and result["confidence"] is not None:
                    try:
                        result["confidence"] = float(result["confidence"])
                    except (ValueError, TypeError):
                        result["confidence"] = 0.85
                else:
                    result["confidence"] = 0.85

            logger.info(
                "AI tahlil yakunlandi: valid=%s, class=%s, plant=%s",
                result.get("valid"),
                result.get("class"),
                result.get("plant_name"),
            )
            return result

        except json.JSONDecodeError as exc:
            last_error = exc
            logger.warning("AI JSON tahlil xatosi (urinish %d): %s", attempt, exc)
            if attempt < max_attempts:
                time.sleep(1.2 * attempt)

        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("AI API chaqiruv xatosi (urinish %d): %s", attempt, exc)
            if attempt < max_attempts:
                time.sleep(1.5 * attempt)

    logger.error("AI tahlil muvaffaqiyatsiz bo'ldi: %s", last_error)
    return {
        "valid": False,
        "error": True,
        "error_message": (
            "Sun'iy intellekt tahlili jarayonida xatolik yuz berdi. "
            "Internet aloqasini tekshiring va qayta urinib ko'ring."
        ),
    }
