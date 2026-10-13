"""
Core unit and integration tests for AgroDoktor.
Covers: demo login, user isolation, image processing, AI service mocks (healthy/diseased/invalid/error).
"""

import io
import json
from unittest.mock import MagicMock, patch
from PIL import Image

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from scans.models import Scan
from scans.services.gemini import analyze_plant_image
from scans.services.image_utils import (
    clean_and_resize_image,
    create_placeholder_leaf_image,
    generate_thumbnail,
)


def _make_dummy_image(name="test.jpg", size=(200, 200), color=(0, 200, 0)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color)
    img.save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


class DemoLoginTests(TestCase):
    """Test demo user automatic login."""

    def test_demo_login_creates_and_logs_in(self):
        client = Client()
        response = client.post(reverse("demo_login"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("dashboard"))

        # Verify demo user was created
        demo_user = User.objects.get(username="demo")
        self.assertEqual(demo_user.first_name, "O'rolboy")
        self.assertEqual(demo_user.last_name, "Xakimov")
        self.assertTrue(demo_user.is_authenticated)


class UserIsolationTests(TestCase):
    """Test that users can only see their own scans."""

    def setUp(self):
        self.user_a = User.objects.create_user("user_a", "a@test.uz", "pass123")
        self.user_b = User.objects.create_user("user_b", "b@test.uz", "pass123")

        img_file = _make_dummy_image()
        self.scan_a = Scan.objects.create(
            user=self.user_a,
            image=img_file,
            result_class=Scan.CLASS_HEALTHY,
            plant_name="Pomidor",
        )

    def test_user_b_cannot_view_scan_a(self):
        client = Client()
        client.force_login(self.user_b)

        response = client.get(reverse("scan_detail", args=[self.scan_a.id]))
        self.assertEqual(response.status_code, 404)

    def test_user_a_can_view_own_scan(self):
        client = Client()
        client.force_login(self.user_a)

        response = client.get(reverse("scan_detail", args=[self.scan_a.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pomidor")


class ImageProcessingTests(TestCase):
    """Test EXIF stripping, resizing and 400px thumbnail generation."""

    def test_clean_and_resize_image(self):
        large_img = _make_dummy_image(size=(1600, 1400))
        cleaned = clean_and_resize_image(large_img)
        self.assertIsNotNone(cleaned)

        # Check dimensions reduced to max 1280
        img = Image.open(cleaned)
        self.assertLessEqual(max(img.size), 1280)

    def test_generate_thumbnail(self):
        src_img = _make_dummy_image(size=(800, 600))
        thumb = generate_thumbnail(src_img)
        self.assertIsNotNone(thumb)

        img = Image.open(thumb)
        self.assertLessEqual(max(img.size), 400)


class AIServiceMockedTests(TestCase):
    """Test AI analysis service under various response scenarios."""

    @patch("scans.services.gemini.genai")
    def test_ai_service_healthy(self, mock_genai):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "valid": True,
            "invalid_reason": "",
            "plant_name": "Pomidor",
            "class": "healthy",
            "disease_name": "",
            "disease_type": "none",
            "severity": "none",
            "confidence": 0.96,
            "summary": "Pomidor bargi toza va sog'lom.",
            "observations": ["Yashil yagona rang", "Dog'lar yo'q"],
            "causes": [],
            "treatment": ["Rejali sug'orish"],
            "prevention": ["Profilaktika"],
            "when_to_call_agronomist": "Hozircha zarurat yo'q",
        })

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        result = analyze_plant_image(b"fake_image_bytes")
        self.assertTrue(result["valid"])
        self.assertEqual(result["class"], "healthy")
        self.assertEqual(result["plant_name"], "Pomidor")
        self.assertAlmostEqual(result["confidence"], 0.96)

    @patch("scans.services.gemini.genai")
    def test_ai_service_diseased(self, mock_genai):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "valid": True,
            "invalid_reason": "",
            "plant_name": "Kartoshka",
            "class": "diseased",
            "disease_name": "Alternarioz",
            "disease_type": "fungal",
            "severity": "medium",
            "confidence": 0.89,
            "summary": "Kartoshka bargida alternarioz belgilari kuzatilmoqda.",
            "observations": ["Barglarda to'q jigar rang dog'lar"],
            "causes": ["Yuqori namlik"],
            "treatment": ["Zararlangan barglarni uzish", "Yorliqdagi ko'rsatmaga amal qiling"],
            "prevention": ["Almashlab ekish"],
            "when_to_call_agronomist": "Dog'lar poyaga o'tsa",
        })

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        result = analyze_plant_image(b"fake_image_bytes")
        self.assertTrue(result["valid"])
        self.assertEqual(result["class"], "diseased")
        self.assertEqual(result["disease_name"], "Alternarioz")

    @patch("scans.services.gemini.genai")
    def test_ai_service_invalid_image(self, mock_genai):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "valid": False,
            "invalid_reason": "Rasmda o'simlik qismi aniqlanmadi.",
        })

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        result = analyze_plant_image(b"fake_image_bytes")
        self.assertFalse(result["valid"])
        self.assertIn("aniqlanmadi", result["invalid_reason"])

    @patch("scans.services.gemini.genai")
    def test_ai_service_api_error_graceful(self, mock_genai):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API ulanishida uzilish")
        mock_genai.Client.return_value = mock_client

        result = analyze_plant_image(b"fake_image_bytes")
        self.assertFalse(result["valid"])
        self.assertTrue(result.get("error"))
        self.assertIn("xatolik", result.get("error_message", ""))
