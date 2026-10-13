"""
Image processing utilities for AgroDoktor.
Handles EXIF orientation, GPS stripping, downscaling to max 1280px,
and generating 400px fast thumbnails.
"""

import io
from PIL import Image, ImageDraw, ImageOps
from django.core.files.uploadedfile import InMemoryUploadedFile


def clean_and_resize_image(uploaded_file, max_size=(1280, 1280), quality=85):
    """
    Reads an uploaded image file, applies orientation from EXIF (if any),
    strips all EXIF metadata (including GPS), downsizes to max_size preserving aspect ratio,
    and returns a clean JPEG as InMemoryUploadedFile.
    """
    img = Image.open(uploaded_file)

    # Automatically rotate image if EXIF orientation is present
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # Convert to RGB mode if RGBA, P, etc.
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if larger than max_size
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    output = io.BytesIO()
    # Saving without EXIF completely strips GPS and device data
    img.save(output, format="JPEG", quality=quality, optimize=True)
    output.seek(0)

    filename = getattr(uploaded_file, "name", "scan.jpg")
    clean_name = filename.rsplit(".", 1)[0] + ".jpg"

    return InMemoryUploadedFile(
        file=output,
        field_name="image",
        name=clean_name,
        content_type="image/jpeg",
        size=output.getbuffer().nbytes,
        charset=None,
    )


def generate_thumbnail(image_file, thumb_size=(400, 400), quality=80):
    """
    Generates a 400px thumbnail from an image file.
    Returns an InMemoryUploadedFile.
    """
    image_file.seek(0)
    img = Image.open(image_file)

    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    img.thumbnail(thumb_size, Image.Resampling.LANCZOS)

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    output.seek(0)

    filename = getattr(image_file, "name", "thumb.jpg")
    clean_name = "thumb_" + filename.rsplit(".", 1)[0] + ".jpg"

    return InMemoryUploadedFile(
        file=output,
        field_name="thumbnail",
        name=clean_name,
        content_type="image/jpeg",
        size=output.getbuffer().nbytes,
        charset=None,
    )


def create_placeholder_leaf_image(
    crop_name="Pomidor",
    result_class="healthy",
    size=(800, 600),
):
    """
    Creates a realistic flat drawn leaf illustration for demo seeding and tests.
    Uses pure flat Pillow rendering with NO gradients.
    """
    # Background slate-100
    bg_color = (241, 245, 249)
    img = Image.new("RGB", size, bg_color)
    draw = ImageDraw.Draw(img)

    cx, cy = size[0] // 2, size[1] // 2

    # Leaf colors based on state
    if result_class == "healthy":
        leaf_body = (16, 185, 129)       # emerald-500
        leaf_vein = (5, 150, 105)         # emerald-600
        stem_color = (4, 120, 87)         # emerald-700
    elif result_class == "suspicious":
        leaf_body = (217, 119, 6)         # amber-600
        leaf_vein = (180, 83, 9)          # amber-700
        stem_color = (146, 64, 14)        # amber-800
    else:
        leaf_body = (185, 28, 28)         # rose-700 / brownish rust
        leaf_vein = (153, 27, 27)         # dark rust
        stem_color = (127, 29, 29)        # deep dark red

    # Draw stem
    draw.line([(cx, cy + 220), (cx, cy + 120)], fill=stem_color, width=12)

    # Draw primary leaf polygon
    leaf_poly = [
        (cx, cy - 200),           # tip
        (cx + 160, cy - 80),      # right upper
        (cx + 200, cy + 40),      # right mid
        (cx + 120, cy + 160),     # right base
        (cx, cy + 180),           # base
        (cx - 120, cy + 160),     # left base
        (cx - 200, cy + 40),      # left mid
        (cx - 160, cy - 80),      # left upper
    ]
    draw.polygon(leaf_poly, fill=leaf_body)

    # Draw central vein
    draw.line([(cx, cy + 180), (cx, cy - 180)], fill=leaf_vein, width=6)

    # Side veins
    draw.line([(cx, cy + 100), (cx + 100, cy + 40)], fill=leaf_vein, width=4)
    draw.line([(cx, cy + 100), (cx - 100, cy + 40)], fill=leaf_vein, width=4)
    draw.line([(cx, cy + 20), (cx + 120, cy - 40)], fill=leaf_vein, width=4)
    draw.line([(cx, cy + 20), (cx - 120, cy - 40)], fill=leaf_vein, width=4)
    draw.line([(cx, cy - 60), (cx + 90, cy - 110)], fill=leaf_vein, width=3)
    draw.line([(cx, cy - 60), (cx - 90, cy - 110)], fill=leaf_vein, width=3)

    # If suspicious or diseased, draw spots
    if result_class == "suspicious":
        # Amber/yellow spots
        spot_color = (245, 158, 11)
        draw.ellipse([cx + 40, cy - 30, cx + 70, cy], fill=spot_color)
        draw.ellipse([cx - 80, cy + 50, cx - 50, cy + 80], fill=spot_color)
        draw.ellipse([cx - 50, cy - 90, cx - 25, cy - 65], fill=spot_color)
    elif result_class == "diseased":
        # Dark fungal / blight lesions
        dark_spot = (69, 10, 10)
        halo_spot = (220, 38, 38)
        draw.ellipse([cx + 30, cy - 50, cx + 80, cy], fill=halo_spot)
        draw.ellipse([cx + 45, cy - 35, cx + 65, cy - 15], fill=dark_spot)
        draw.ellipse([cx - 90, cy + 20, cx - 40, cy + 70], fill=halo_spot)
        draw.ellipse([cx - 75, cy + 35, cx - 55, cy + 55], fill=dark_spot)
        draw.ellipse([cx + 70, cy + 60, cx + 110, cy + 100], fill=dark_spot)

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=85)
    output.seek(0)

    filename = f"sample_{crop_name.lower()}_{result_class}.jpg"
    return InMemoryUploadedFile(
        file=output,
        field_name="image",
        name=filename,
        content_type="image/jpeg",
        size=output.getbuffer().nbytes,
        charset=None,
    )
