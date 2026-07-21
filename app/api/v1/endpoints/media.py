import os
import uuid
import asyncio
import random
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

MEDICATION_CATALOG = [
    {
        "title": "Metoprolol succinate",
        "slug": "metoprolol-succinate",
        "dosage": "25 mg",
        "timings": ["morning"],
        "instructions": "1 tablet every morning",
        "foodRelation": "after_breakfast",
        "frequency": "daily",
        "tags": ["Prescription"],
    },
    {
        "title": "Furosemide",
        "slug": "furosemide",
        "dosage": "40 mg",
        "timings": ["morning"],
        "instructions": "1 tablet every morning",
        "foodRelation": "after_breakfast",
        "frequency": "daily",
        "tags": ["Prescription"],
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
    },
    {
        "title": "Atorvastatin",
        "slug": "atorvastatin",
        "dosage": "20 mg",
        "timings": ["night"],
        "instructions": "1 tablet before sleep",
        "foodRelation": "none",
        "frequency": "daily",
        "tags": ["Statins"],
    },
    {
        "title": "Lisinopril",
        "slug": "lisinopril",
        "dosage": "10 mg",
        "timings": ["morning"],
        "instructions": "1 tablet daily",
        "foodRelation": "on_empty_stomach",
        "frequency": "daily",
        "tags": ["Blood Pressure"],
    },
]

@router.post("/medications/extract", response_model=ApiResponse)
async def extract_medications(
    request: MedicationExtractRequest,
    current_user: User = Depends(get_current_user)
):
    # Simulate text extraction processing delay
    await asyncio.sleep(2.0)
    
    unreadable_photos = []
    medications = []
    
    # Process each uploaded image probabilistically
    for idx, img_path in enumerate(request.images):
        # Roll probabilities for this photo
        # ~30% chance for photo to be blurry / unreadable
        is_blurry = random.random() < 0.30
        
        # ~35% chance for extracted medication to be incomplete (missing dosage)
        is_incomplete = random.random() < 0.35
        
        if is_blurry:
            unreadable_photos.append(img_path)
            
        # If photo is not blurry OR with a small probability (15%) even if blurry it extracted a partial med
        if not is_blurry or (is_blurry and random.random() < 0.15):
            # Select a medication from catalog
            base_med = dict(MEDICATION_CATALOG[idx % len(MEDICATION_CATALOG)])
            
            if is_incomplete:
                base_med["isIncomplete"] = True
                # Roll whether missing field is 'title' (name) OR 'dosage' (dose) - mutually exclusive
                missing_field = random.choice(["title", "dosage"])
                if missing_field == "title":
                    base_med["title"] = ""
                    base_med["slug"] = ""
                    base_med["incompleteFields"] = ["title"]
                    base_med["unreadableReason"] = "Medication name label could not be read clearly from photo"
                else:
                    base_med["dosage"] = ""
                    base_med["incompleteFields"] = ["dosage"]
                    base_med["unreadableReason"] = "Dosage label could not be read clearly from photo"
            else:
                base_med["isIncomplete"] = False
                base_med["incompleteFields"] = []
                
            medications.append(base_med)
            
    return ApiResponse(
        success=True,
        message="Medications extracted successfully.",
        data={
            "medications": medications,
            "unreadablePhotos": unreadable_photos
        }
    )
