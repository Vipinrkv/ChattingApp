from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid
from pathlib import Path

from app.core.auth import get_current_user as get_current_user_dep
from app.core.errors import NotFoundError
from app.database.connection import get_db_session
from app.services import media_service

router = APIRouter()


@router.post("/upload/initiate")
async def initiate_upload(filename: str = Form(...)):
    upload_id = str(uuid.uuid4())
    tmp = Path(media_service.TMP_DIR) / upload_id
    tmp.mkdir(parents=True, exist_ok=True)
    return {"upload_id": upload_id}


@router.post("/upload/{upload_id}/chunk")
async def upload_chunk(upload_id: str, chunk_index: int = Form(...), file: UploadFile = File(...)):
    tmpdir = Path(media_service.TMP_DIR) / upload_id
    if not tmpdir.exists():
        raise NotFoundError("Upload session not found", code="media_upload_session_not_found")
    dest = tmpdir / f"chunk_{chunk_index:06d}"
    with dest.open("wb") as fd:
        while True:
            chunk = await file.read(2_000_000)
            if not chunk:
                break
            fd.write(chunk)
    return {"status": "ok", "index": chunk_index}


@router.post("/upload/{upload_id}/complete")
async def complete_upload(upload_id: str, filename: str = Form(...), current_user=Depends(get_current_user_dep)):
    tmpdir = Path(media_service.TMP_DIR) / upload_id
    if not tmpdir.exists():
        raise NotFoundError("Upload session not found", code="media_upload_session_not_found")
    assembled = await media_service.assemble_chunks(upload_id, filename)
    # schedule post processing
    await media_service.schedule_post_processing(assembled)
    tags = await media_service.ai_tag_media(assembled)
    url = await media_service.store_file(assembled)
    return {"url": url, "tags": tags}


@router.post("/transcode")
async def transcode_endpoint(path: str = Form(...)):
    p = Path(path)
    if not p.exists():
        raise NotFoundError("File not found", code="media_file_not_found")
    out = p.with_suffix('.mp4')
    await media_service.transcode_video(p, out)
    return {"output": str(out)}


@router.post("/optimize")
async def optimize_endpoint(path: str = Form(...)):
    p = Path(path)
    if not p.exists():
        raise NotFoundError("File not found", code="media_file_not_found")
    out = await media_service.optimize_image(p)
    return {"output": str(out)}


@router.post("/tag")
async def tag_endpoint(path: str = Form(...)):
    p = Path(path)
    if not p.exists():
        raise NotFoundError("File not found", code="media_file_not_found")
    tags = await media_service.ai_tag_media(p)
    return {"tags": tags}
