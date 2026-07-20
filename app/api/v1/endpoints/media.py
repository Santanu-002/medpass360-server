import os
import uuid
import asyncio
from typing import List, Optional
from enum import Enum
from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, status
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.user import CamelModel

router = APIRouter()

UPLOAD_ROOT = "/workspace/uploads"
ALLOWED_PURPOSES = {"avatar", "medication", "care_person"}

class FileType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    ZIP = "zip"
    DOC = "doc"
    DYNAMIC = "dynamic"

# Allowed extensions mapped to FileType
ALLOWED_EXTENSIONS = {
    FileType.IMAGE: {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"},
    FileType.VIDEO: {".mp4", ".mov", ".avi", ".mkv"},
    FileType.ZIP: {".zip", ".rar", ".tar", ".gz"},
    FileType.DOC: {".pdf", ".doc", ".docx", ".txt", ".csv", ".xls", ".xlsx"},
}

class MedicationExtractRequest(CamelModel):
    images: List[str]

@router.post("/upload", response_model=ApiResponse)
async def upload_media(
    file: UploadFile = File(...),
    purpose: str = Form(...),
    file_type: FileType = Form(FileType.DYNAMIC),
    current_user: User = Depends(get_current_user)
):
    # Validate purpose
    if purpose not in ALLOWED_PURPOSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid upload purpose. Allowed values are: {', '.join(ALLOWED_PURPOSES)}"
        )

    # Validate file presence
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload file."
        )

    # Extract file extension
    file_ext = os.path.splitext(file.filename)[1].lower() or ".jpg"

    # Validate file type extension matches the enum
    if file_type != FileType.DYNAMIC:
        allowed_exts = ALLOWED_EXTENSIONS.get(file_type, set())
        if file_ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{file_ext}' is not allowed for file type '{file_type.value}'. Allowed extensions: {', '.join(allowed_exts)}"
            )

    # Create target directory depending on purpose
    target_dir = os.path.join(UPLOAD_ROOT, f"{purpose}s")
    os.makedirs(target_dir, exist_ok=True)

    # Generate unique filename using UUID
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(target_dir, unique_filename)

    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save uploaded file: {str(e)}"
        )

    # Construct and return the public URL path
    public_url = f"/uploads/{purpose}s/{unique_filename}"
    return ApiResponse(
        success=True,
        message="File uploaded successfully.",
        data={"url": public_url}
    )

@router.post("/medications/extract", response_model=ApiResponse)
async def extract_medications(
    request: MedicationExtractRequest,
    current_user: User = Depends(get_current_user)
):
    # Simulate text extraction processing delay
    await asyncio.sleep(2.0)
    
    image_count = len(request.images)
    
    # Mock data output aligned with complete and incomplete extraction cases
    mocked_meds = [
        {
            "title": "Metoprolol succinate",
            "slug": "metoprolol-succinate",
            "dosage": "25 mg",
            "timings": ["morning"],
            "instructions": "1 tablet every morning",
            "foodRelation": "after_breakfast",
            "frequency": "daily",
            "tags": ["Prescription"],
            "isIncomplete": False,
            "incompleteFields": []
        },
        {
            "title": "Furosemide",
            "slug": "furosemide",
            "dosage": "",  # Incomplete field: dosage was unreadable
            "timings": ["morning"],
            "instructions": "1 tablet every morning",
            "foodRelation": "after_breakfast",
            "frequency": "daily",
            "tags": ["Prescription"],
            "isIncomplete": True,
            "incompleteFields": ["dosage"],
            "unreadableReason": "Dosage label could not be read clearly from photo"
        },
        {
            "title": "Eliquis (apixaban)",
            "slug": "eliquis-apixaban",
            "dosage": "5 mg",
            "timings": ["morning", "evening"],
            "instructions": "1 tablet, morning & evening",
            "foodRelation": "after_meal",
            "frequency": "daily",
            "tags": ["CRITICAL"],
            "isIncomplete": False,
            "incompleteFields": []
        }
    ]
    
    unreadable_photos = []
    if image_count >= 3:
        # If >= 3 images, simulate both cases: incomplete medication + 1 unreadable photo
        unreadable_photos = [request.images[-1]]
        
    return ApiResponse(
        success=True,
        message="Medications extracted successfully.",
        data={
            "medications": mocked_meds,
            "unreadablePhotos": unreadable_photos
        }
    )
