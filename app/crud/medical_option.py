from sqlalchemy.orm import Session
from sqlalchemy import case
from app.models.profile import Allergy, MedicalCondition, FamilyHistory
from typing import Dict, List, Any

def get_grouped_medical_options(db: Session, user_uid: str, status: str = "active") -> Dict[str, List[Any]]:
    # 1. Fetch allergy options (profile_id is NULL)
    allergies = (
        db.query(Allergy)
        .filter(
            Allergy.profile_id == None,
            Allergy.status == status,
            (Allergy.created_by == None) | (Allergy.created_by == user_uid)
        )
        .order_by(
            case((Allergy.created_by == None, 0), else_=1),
            Allergy.display_name.asc()
        )
        .all()
    )

    # 2. Fetch medical condition options (profile_id is NULL)
    conditions = (
        db.query(MedicalCondition)
        .filter(
            MedicalCondition.profile_id == None,
            MedicalCondition.status == status,
            (MedicalCondition.created_by == None) | (MedicalCondition.created_by == user_uid)
        )
        .order_by(
            case((MedicalCondition.created_by == None, 0), else_=1),
            MedicalCondition.display_name.asc()
        )
        .all()
    )

    # 3. Fetch family history options (profile_id is NULL)
    family_history = (
        db.query(FamilyHistory)
        .filter(
            FamilyHistory.profile_id == None,
            FamilyHistory.status == status,
            (FamilyHistory.created_by == None) | (FamilyHistory.created_by == user_uid)
        )
        .order_by(
            case((FamilyHistory.created_by == None, 0), else_=1),
            FamilyHistory.display_name.asc()
        )
        .all()
    )

    # Group in Python
    categories = {
        "chronic_condition": [c for c in conditions if c.condition_type == "chronic"],
        "syndrome": [c for c in conditions if c.condition_type == "syndrome"],
        "drug_allergy": [a for a in allergies if a.allergy_type == "drug"],
        "food_allergy": [a for a in allergies if a.allergy_type == "food"],
        "environmental_allergy": [a for a in allergies if a.allergy_type == "environmental"],
        "family_history": family_history
    }
    
    return categories

def get_allergy_options(db: Session, user_uid: str, status: str = "active") -> List[Allergy]:
    return (
        db.query(Allergy)
        .filter(
            Allergy.profile_id == None,
            Allergy.status == status,
            (Allergy.created_by == None) | (Allergy.created_by == user_uid)
        )
        .order_by(
            case((Allergy.created_by == None, 0), else_=1),
            Allergy.display_name.asc()
        )
        .all()
    )

def get_condition_options(db: Session, user_uid: str, status: str = "active") -> List[MedicalCondition]:
    return (
        db.query(MedicalCondition)
        .filter(
            MedicalCondition.profile_id == None,
            MedicalCondition.status == status,
            (MedicalCondition.created_by == None) | (MedicalCondition.created_by == user_uid)
        )
        .order_by(
            case((MedicalCondition.created_by == None, 0), else_=1),
            MedicalCondition.display_name.asc()
        )
        .all()
    )

def get_family_history_options(db: Session, user_uid: str, status: str = "active") -> List[FamilyHistory]:
    return (
        db.query(FamilyHistory)
        .filter(
            FamilyHistory.profile_id == None,
            FamilyHistory.status == status,
            (FamilyHistory.created_by == None) | (FamilyHistory.created_by == user_uid)
        )
        .order_by(
            case((FamilyHistory.created_by == None, 0), else_=1),
            FamilyHistory.display_name.asc()
        )
        .all()
    )
