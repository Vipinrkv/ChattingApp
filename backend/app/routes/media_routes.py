from fastapi import APIRouter, Depends, UploadFile, File, Form, Header, HTTPException, status
from fastapi import Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid
import io
import mimetypes
from pathlib import Path

from app.core.auth import get_current_user as get_current_user_dep
from app.core.errors import NotFoundError
from app.database.connection import get_db_session
from app.services import media_service
from app.services.encrypted_media_service import EncryptedMediaService

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
async def complete_upload(
    upload_id: str,
    filename: str = Form(...),
    encrypt: Optional[bool] = Form(False),
    current_user=Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    tmpdir = Path(media_service.TMP_DIR) / upload_id
    if not tmpdir.exists():
        raise NotFoundError("Upload session not found", code="media_upload_session_not_found")
    assembled = await media_service.assemble_chunks(upload_id, filename)
    
    # schedule post processing
    await media_service.schedule_post_processing(assembled)
    tags = await media_service.ai_tag_media(assembled)
    
    # Resolve mime type or media type
    media_type, _ = mimetypes.guess_type(filename)
    if not media_type:
        media_type = "application/octet-stream"

    if encrypt:
        # Encrypt and store in database
        media_id = await EncryptedMediaService.encrypt_and_store_media(
            session=session,
            file_path=assembled,
            filename=filename,
            media_type=media_type,
        )
        # Delete the temporary assembled local file
        try:
            assembled.unlink()
        except Exception:
            pass
            
        url = f"/api/v1/media/encrypted/{media_id}"
    else:
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


@router.get("/encrypted/{media_id}")
async def get_encrypted_media(
    media_id: uuid.UUID,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_db_session),
):
    """Serve decrypted database-stored media on the fly."""
    auth_token = token
    if not auth_token and authorization:
        auth_token = (
            authorization.replace("Bearer ", "")
            if authorization.startswith("Bearer ")
            else authorization
        )

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    from app.core.firebase import FirebaseService
    from app.services.user_service import UserService

    FirebaseService.initialize()
    decoded_token = FirebaseService.verify_token(auth_token)
    if not decoded_token or "uid" not in decoded_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    firebase_uid = decoded_token["uid"]
    user = await UserService.get_user_by_firebase_uid(session, firebase_uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user profile not found",
        )

    try:
        bytes_data, filename, media_type = await EncryptedMediaService.retrieve_and_decrypt_media(
            session, media_id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        ) from exc

    return StreamingResponse(
        io.BytesIO(bytes_data),
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        }
    )
