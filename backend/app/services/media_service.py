import asyncio
import uuid
import shutil
import subprocess
from pathlib import Path
from typing import Tuple

import boto3
import httpx
from PIL import Image

from app.core.task_queue import task_queue
from app.core.config import settings

ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = ROOT / "uploads" / "media"
TMP_DIR = ROOT / "uploads" / "tmp"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)


def _ext_from_filename(name: str) -> str:
    return Path(name).suffix.lower()


async def assemble_chunks(upload_id: str, filename: str) -> Path:
    dest = UPLOAD_DIR / f"{upload_id}{_ext_from_filename(filename)}"
    tmpdir = TMP_DIR / upload_id
    parts = sorted(tmpdir.glob("chunk_*"))
    # assemble
    with dest.open("wb") as wfd:
        for p in parts:
            with p.open("rb") as fd:
                shutil.copyfileobj(fd, wfd)

    # cleanup tmp
    try:
        shutil.rmtree(tmpdir)
    except Exception:
        pass
    return dest


async def _upload_to_s3(file_path: Path) -> str:
    # returns public URL
    s3_bucket = settings.AWS_S3_BUCKET
    if not s3_bucket:
        raise RuntimeError("S3 bucket not configured")
    client = boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )
    key = f"media/{file_path.name}"
    client.upload_file(str(file_path), s3_bucket, key)
    if settings.CDN_URL:
        return settings.CDN_URL.rstrip("/") + f"/{key}"
    # fallback S3 URL
    region = settings.AWS_S3_REGION or ""
    return f"https://{s3_bucket}.s3.{region}.amazonaws.com/{key}"


async def store_file(file_path: Path) -> str:
    """Store file to S3 if configured, else return local URL path served by /uploads."""
    if settings.AWS_S3_BUCKET:
        try:
            return await _upload_to_s3(file_path)
        except Exception:
            # fallback to local
            pass
    # local URL served by StaticFiles mount at /uploads
    return f"/uploads/media/{file_path.name}"


def _run_ffmpeg(args: list[str]) -> None:
    # synchronous call wrapped by thread executor in callers
    subprocess.run(["ffmpeg", "-y", *args], check=False)


async def transcode_video(input_path: Path, output_path: Path, preset: str = "libx264") -> None:
    args = ["-i", str(input_path), "-c:v", preset, "-preset", "fast", str(output_path)]
    await asyncio.to_thread(_run_ffmpeg, args)


async def extract_video_thumbnail(input_path: Path, thumb_path: Path, time_offset: float = 1.0) -> None:
    args = ["-ss", str(time_offset), "-i", str(input_path), "-frames:v", "1", str(thumb_path)]
    await asyncio.to_thread(_run_ffmpeg, args)


async def generate_image_thumbnail(input_path: Path, thumb_path: Path, size: Tuple[int, int] = (320, 180)) -> None:
    with Image.open(input_path) as img:
        img.thumbnail(size)
        img.save(thumb_path, format="WEBP", quality=80)


async def optimize_image(input_path: Path) -> Path:
    # convert to webp (lossy) and return new path
    out = input_path.with_suffix(".webp")
    def _convert():
        with Image.open(input_path) as img:
            img.save(out, format="WEBP", quality=80)
    await asyncio.to_thread(_convert)
    return out


async def ai_tag_media(file_path: Path) -> list[str]:
    # Placeholder - schedule background AI tagging. For now return basic heuristics.
    tags = []
    ext = file_path.suffix.lower()
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
        tags.append("image")
    if ext in [".mp4", ".mov", ".webm", ".ogg"]:
        tags.append("video")
    # if AI_TAGGER_URL is configured call remote tagger synchronously
    if settings.AI_TAGGER_URL:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                files = {"file": (file_path.name, file_path.open("rb"), "application/octet-stream")}
                resp = await client.post(settings.AI_TAGGER_URL, files=files)
                if resp.status_code == 200:
                    data = resp.json()
                    remote_tags = data.get("tags") or data.get("predictions")
                    if isinstance(remote_tags, list):
                        tags.extend([str(t) for t in remote_tags])
        except Exception:
            pass

    # schedule background enrichment (placeholder)
    async def _background_tag(p: Path):
        return

    await task_queue.schedule(_background_tag, file_path)
    return tags


async def schedule_post_processing(file_path: Path) -> None:
    # generate thumbnail, optimize image/video as background tasks
    ext = file_path.suffix.lower()

    async def _process(p: Path):
        try:
            thumb = p.with_name(p.stem + "_thumb.webp")
            if ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                await generate_image_thumbnail(p, thumb)
                await optimize_image(p)
                # optionally produce AVIF
                if settings.ENABLE_AVIF:
                    avif_out = p.with_suffix('.avif')
                    try:
                        await asyncio.to_thread(_run_ffmpeg, ["-i", str(p), str(avif_out)])
                    except Exception:
                        pass
            else:
                # treat as video
                await extract_video_thumbnail(p, thumb)
                # transcode to mp4
                out = p.with_suffix('.mp4')
                await transcode_video(p, out)
        except Exception:
            pass

    await task_queue.schedule(_process, file_path)
import re
import uuid
from pathlib import Path
from io import BytesIO
import os

from fastapi import UploadFile

try:
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    _PIL_AVAILABLE = True
except Exception:
    _PIL_AVAILABLE = False

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    _S3_AVAILABLE = True
except Exception:
    _S3_AVAILABLE = False


UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"
MAX_MEDIA_BYTES = 15 * 1024 * 1024
ALLOWED_MEDIA_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "video/mp4",
    "video/webm",
    "audio/mpeg",
    "audio/wav",
    "audio/webm",
    "application/pdf",
    "text/plain",
}


class MediaError(Exception):
    pass


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", filename).strip("._")
    return cleaned or "upload"


def _upload_to_s3(bucket: str, key: str, data: bytes, content_type: str) -> str:
    try:
        region = os.getenv("AWS_S3_REGION") or os.getenv("AWS_REGION")
        client = boto3.client("s3", region_name=region) if region else boto3.client("s3")
        client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type, ACL="public-read")

        cdn = os.getenv("CDN_URL") or os.getenv("CLOUDFRONT_URL")
        if cdn:
            return cdn.rstrip("/") + "/" + key

        # Construct a best-effort S3 public URL
        if region and region != "us-east-1":
            return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    except (BotoCoreError, ClientError) as e:
        raise MediaError(f"S3 upload failed: {e}")


async def store_chat_upload(file: UploadFile) -> dict:
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MEDIA_TYPES:
        raise MediaError("Unsupported file type")

    data = await file.read()
    if not data:
        raise MediaError("Uploaded file is empty")
    if len(data) > MAX_MEDIA_BYTES:
        raise MediaError("Uploaded file is larger than 15 MB")

    # Attempt lightweight image validation and compression for common image types
    if content_type.startswith("image/") and _PIL_AVAILABLE:
        try:
            img = Image.open(BytesIO(data))
            img.verify()
            img = Image.open(BytesIO(data))
            fmt = (img.format or "JPEG").upper()
            output = BytesIO()

            # Only recompress standard raster formats; skip animated GIFs
            if fmt in ("JPEG", "JPG"):
                img = img.convert("RGB")
                img.save(output, format="JPEG", quality=75, optimize=True)
            elif fmt == "PNG":
                img.save(output, format="PNG", optimize=True, compress_level=6)
            elif fmt == "WEBP":
                img.save(output, format="WEBP", quality=80, method=6)
            else:
                # Unknown/unsupported formats (GIF, etc.) — skip compression
                output.write(data)

            compressed = output.getvalue()
            # Use compressed bytes only when smaller
            if compressed and len(compressed) < len(data):
                data = compressed
        except Exception:
            raise MediaError("Uploaded image file failed validation")

    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    original_name = _safe_filename(file.filename or "upload")
    storage_name = f"{uuid.uuid4()}-{original_name}"

    # If environment indicates S3 bucket, attempt upload to S3 (CDN-ready)
    s3_bucket = os.getenv("AWS_S3_BUCKET") or os.getenv("S3_BUCKET")
    if s3_bucket:
        if not _S3_AVAILABLE:
            raise MediaError("S3 upload requested but boto3 is not installed")
        try:
            url = _upload_to_s3(s3_bucket, storage_name, data, content_type)
            return {
                "url": url,
                "content_type": content_type,
                "name": original_name,
                "size": len(data),
                "storage": "s3",
            }
        except MediaError:
            # On S3 failure, fall back to local storage
            pass

    # Fallback: write to local uploads folder
    target = UPLOAD_ROOT / storage_name
    target.write_bytes(data)

    return {
        "url": f"/uploads/{storage_name}",
        "content_type": content_type,
        "name": original_name,
        "size": len(data),
        "storage": "local",
    }
