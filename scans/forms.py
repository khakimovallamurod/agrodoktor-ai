"""
Forms for scans app: image upload and metadata validation.
"""

from django import forms
from PIL import Image

CROP_CHOICES = [
    ("", "Tanlang (ixtiyoriy)"),
    ("Pomidor", "Pomidor"),
    ("Kartoshka", "Kartoshka"),
    ("Bug'doy", "Bug'doy"),
    ("Paxta", "Paxta"),
    ("Uzum", "Uzum"),
    ("Olma", "Olma"),
    ("Bodring", "Bodring"),
    ("Boshqa", "Boshqa ekin"),
]


class ScanUploadForm(forms.Form):
    """Handles plant image upload with optional farm context."""

    image = forms.ImageField(
        required=True,
        error_messages={
            "required": "Iltimos, o'simlik rasmini tanlang yoki oling.",
            "invalid_image": "Yuklangan fayl yaroqli rasm emas.",
        },
    )
    crop_type = forms.ChoiceField(
        choices=CROP_CHOICES,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "w-full h-14 px-4 bg-white border border-slate-200 rounded-xl text-slate-800 text-base sm:text-lg focus:outline-none focus:ring-2 focus:ring-emerald-500",
            }
        ),
    )
    field_name = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Masalan: 1-dala, Issiqxona #2",
                "class": "w-full h-14 px-4 bg-white border border-slate-200 rounded-xl text-slate-800 text-base sm:text-lg focus:outline-none focus:ring-2 focus:ring-emerald-500",
            }
        ),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Qo'shimcha kuzatuvlar yoki izohlar...",
                "class": "w-full p-4 bg-white border border-slate-200 rounded-xl text-slate-800 text-base sm:text-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none",
            }
        ),
    )

    def clean_image(self):
        uploaded_image = self.cleaned_data.get("image")
        if not uploaded_image:
            raise forms.ValidationError("Rasm yuklanmadi.")

        if uploaded_image.size > 10 * 1024 * 1024:
            raise forms.ValidationError(
                "Rasm hajmi 10 MB dan oshmasligi kerak. Kichikroq rasm tanlang."
            )

        try:
            img = Image.open(uploaded_image)
            img.verify()
            uploaded_image.seek(0)
        except Exception as exc:
            raise forms.ValidationError(
                "Rasm fayli buzilgan yoki ochib bo'lmadi. Boshqa rasm tanlang."
            ) from exc

        return uploaded_image
