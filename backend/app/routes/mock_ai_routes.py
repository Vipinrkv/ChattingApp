from fastapi import APIRouter, File, UploadFile

router = APIRouter()


@router.post("/mock-ai-tagger")
async def mock_ai_tagger(file: UploadFile = File(...)):
    name = file.filename.lower()
    tags = []
    if any(ext in name for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]):
        tags.extend(["image", "mocked"])
    if any(ext in name for ext in [".mp4", ".mov", ".webm"]):
        tags.extend(["video", "mocked"])
    if not tags:
        tags = ["file", "mocked"]
    return {"tags": tags}
