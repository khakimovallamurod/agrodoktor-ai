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


def _thinking_config(model_name: str):
    """
    Keep model "thinking" short: it dominates latency (~22s default vs ~10s low on Gemini 3 Flash).
    Gemini 3 models take a thinking level, Gemini 2.5 models a token budget.
    """
    level = getattr(settings, "GEMINI_THINKING_LEVEL", "low").upper()
    if model_name.startswith("gemini-2.5"):
        budgets = {"LOW": 512, "MEDIUM": 2048, "HIGH": -1}
        return genai_types.ThinkingConfig(thinking_budget=budgets.get(level, 512))
    return genai_types.ThinkingConfig(thinking_level=level)


def _is_overloaded(exc: Exception) -> bool:
    """True for transient capacity errors (503 / 429) where switching model beats waiting."""
    text = str(exc)
    return any(code in text for code in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"))


def _is_timeout(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(k in text for k in ("timeout", "timed out", "deadline", "504"))


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
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash")

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

    timeout_ms = int(getattr(settings, "GEMINI_TIMEOUT_SECONDS", 30) * 1000)
    client = genai.Client(api_key=api_key, http_options=genai_types.HttpOptions(timeout=timeout_ms))

    # Main model first, then fallbacks used immediately when a model is overloaded
    models = [model_name] + [
        m for m in getattr(settings, "GEMINI_FALLBACK_MODELS", []) if m and m != model_name
    ]
    current_model = models[0]
    max_attempts = len(models) + 1
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=[
                    genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    genai_types.Part.from_text(text=prompt_text),
                ],
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,
                    response_mime_type="application/json",
                    thinking_config=_thinking_config(current_model),
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

                # Fit model CharField limits (disease name now carries the Latin pathogen name)
                for text_field in ("plant_name", "disease_name"):
                    if isinstance(result.get(text_field), str):
                        result[text_field] = result[text_field].strip()[:120]

                if "confidence" in result and result["confidence"] is not None:
                    try:
                        result["confidence"] = float(result["confidence"])
                    except (ValueError, TypeError):
                        result["confidence"] = 0.85
                else:
                    result["confidence"] = 0.85

            result["model"] = current_model
            logger.info(
                "AI tahlil yakunlandi (%s): valid=%s, class=%s, plant=%s",
                current_model,
                result.get("valid"),
                result.get("class"),
                result.get("plant_name"),
            )
            return result

        except json.JSONDecodeError as exc:
            last_error = exc
            logger.warning("AI JSON tahlil xatosi (urinish %d): %s", attempt, exc)
            if attempt < max_attempts:
                time.sleep(0.5)

        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("AI API chaqiruv xatosi (%s, urinish %d): %s", current_model, attempt, exc)
            if attempt >= max_attempts:
                break
            # Model band yoki javob kechikdi: kutmasdan keyingi zaxira modelga o'tamiz
            next_index = models.index(current_model) + 1
            if (_is_overloaded(exc) or _is_timeout(exc)) and next_index < len(models):
                current_model = models[next_index]
                continue
            time.sleep(0.8)

    logger.error("AI tahlil muvaffaqiyatsiz bo'ldi: %s", last_error)
    return {
        "valid": False,
        "error": True,
        "error_message": (
            "Sun'iy intellekt tahlili jarayonida xatolik yuz berdi. "
            "Internet aloqasini tekshiring va qayta urinib ko'ring."
        ),
    }
