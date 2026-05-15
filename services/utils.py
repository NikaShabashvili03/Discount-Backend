import logging
import os
import uuid
from PIL import Image
from io import BytesIO
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.files import File

logger = logging.getLogger(__name__)

# Accept images of any pixel count. Default Pillow raises DecompressionBombError
# around 178 megapixels — disabling that is required to allow every image.
Image.MAX_IMAGE_PIXELS = None

def image_upload(instance, filename, dir):
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4()}.{ext}'
    return os.path.join(dir, filename)

def validate_image(image_field, max_size_kb=None, compress_quality=75, path=''):
    """Transcode the upload to WEBP and store it. No size or dimension limits
    are enforced — every image is accepted at its original resolution. The
    `max_size_kb` argument is kept for backwards compatibility with existing
    callers but is intentionally unused."""
    try:
        img = Image.open(image_field)
        img = img.convert('RGB')

        buffer = BytesIO()
        img.save(buffer, format='WEBP', quality=compress_quality, optimize=True)
        buffer.seek(0)

        webp_filename = f"{uuid.uuid4()}.webp"
        file_path = os.path.join(settings.MEDIA_ROOT, path, webp_filename)

        logger.debug("Saving image at: %s", file_path)
        with default_storage.open(file_path, 'wb') as f:
            f.write(buffer.read())

        return f"{path}{webp_filename}"

    except Exception as e:
        raise ValidationError(f"Image compression failed: {str(e)}")