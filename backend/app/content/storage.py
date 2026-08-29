from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import AppError

FORMAT_CONFIG = {
    "JPEG": ("jpg", "image/jpeg", "JPEG"),
    "MPO": ("jpg", "image/jpeg", "JPEG"),
    "PNG": ("png", "image/png", "PNG"),
    "WEBP": ("webp", "image/webp", "WEBP"),
}


class LocalImageStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or get_settings().upload_dir).resolve()

    def save(self, content: bytes) -> tuple[str, int, int, str]:
        settings = get_settings()
        if not content or len(content) > settings.upload_max_bytes:
            max_megabytes = settings.upload_max_bytes // (1024 * 1024)
            raise AppError(
                "INVALID_IMAGE_SIZE",
                f"图片为空或超过 {max_megabytes}MB",
                status_code=413,
            )
        try:
            source = Image.open(BytesIO(content))
            source.verify()
            source = Image.open(BytesIO(content))
            source.load()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise AppError(
                "INVALID_IMAGE",
                "仅支持有效的 JPG、JPEG、iPhone HDR 照片、PNG 或 WEBP 图片",
                status_code=400,
            ) from exc
        if source.format not in FORMAT_CONFIG:
            raise AppError(
                "INVALID_IMAGE_TYPE",
                "仅支持 JPG、JPEG、iPhone HDR 照片、PNG 或 WEBP 图片",
                status_code=400,
            )
        width, height = source.size
        if width > 12000 or height > 12000:
            raise AppError("IMAGE_TOO_LARGE", "图片尺寸不能超过 12000×12000", status_code=400)
        source_format = source.format
        extension, content_type, output_format = FORMAT_CONFIG[source_format]
        self.root.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex}.{extension}"
        target = (self.root / filename).resolve()
        if target.parent != self.root:
            raise AppError("INVALID_UPLOAD_PATH", "上传路径无效", status_code=400)
        if source_format == "MPO":
            source.seek(0)
            save_image = source.copy()
        else:
            save_image = source
        if output_format == "JPEG" and save_image.mode not in ("RGB", "L"):
            save_image = save_image.convert("RGB")
        save_image.save(target, format=output_format, optimize=True)
        return f"/uploads/{filename}", width, height, content_type
