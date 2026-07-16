from sqlalchemy.orm import Session
from sqlalchemy import case
from app.models.medical_option import MedicalOption
from typing import Dict, List

def get_grouped_medical_options(db: Session, user_uid: str, status: str = "active") -> Dict[str, List[MedicalOption]]:
    # Fetch all items matching the filter, ordered by:
    # 1. Defaults first (created_by is NULL) then user-created
    # 2. display_name alphabetically
    items = (
        db.query(MedicalOption)
        .filter(
            MedicalOption.status == status,
            (MedicalOption.created_by == None) | (MedicalOption.created_by == user_uid)
        )
        .order_by(
            case((MedicalOption.created_by == None, 0), else_=1),
            MedicalOption.display_name.asc()
        )
        .all()
    )

    # Group in Python
    categories = {
        "chronic_condition": [],
        "syndrome": [],
        "drug_allergy": [],
        "food_allergy": [],
        "environmental_allergy": [],
        "family_history": []
    }
    
    for item in items:
        if item.category in categories:
            categories[item.category].append(item)
            
    return categories
