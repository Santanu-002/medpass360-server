from sqlalchemy.orm import Session
from sqlalchemy import case
from app.models.profile import Allergy, MedicalCondition, FamilyHistory
from typing import Dict, List, Any

def get_grouped_medical_options(db: Session, user_uid: str, status: str = "active") -> Dict[str, List[Any]]:
    # 1. Fetch Allergies
    allergies = (
        db.query(Allergy)
        .filter(
            Allergy.status == status,
            (Allergy.created_by == None) | (Allergy.created_by == user_uid)
        )
        .order_by(
            case((Allergy.created_by == None, 0), else_=1),
            Allergy.display_name.asc()
        )
        .all()
    )
    for a in allergies:
        a.category = f"{a.allergy_type}_allergy"

    # 2. Fetch Conditions
    conditions = (
        db.query(MedicalCondition)
        .filter(
            MedicalCondition.status == status,
            (MedicalCondition.created_by == None) | (MedicalCondition.created_by == user_uid)
        )
        .order_by(
            case((MedicalCondition.created_by == None, 0), else_=1),
            MedicalCondition.display_name.asc()
        )
        .all()
    )
    for c in conditions:
        c.category = "chronic_condition" if c.condition_type == "chronic" else "syndrome"

    # 3. Fetch Family History
    histories = (
        db.query(FamilyHistory)
        .filter(
            FamilyHistory.status == status,
            (FamilyHistory.created_by == None) | (FamilyHistory.created_by == user_uid)
        )
        .order_by(
            case((FamilyHistory.created_by == None, 0), else_=1),
            FamilyHistory.display_name.asc()
        )
        .all()
    )
    for h in histories:
        h.category = "family_history"

    return {
        "chronic_condition": [c for c in conditions if c.category == "chronic_condition"],
        "syndrome": [c for c in conditions if c.category == "syndrome"],
        "drug_allergy": [a for a in allergies if a.category == "drug_allergy"],
        "food_allergy": [a for a in allergies if a.category == "food_allergy"],
        "environmental_allergy": [a for a in allergies if a.category == "environmental_allergy"],
        "family_history": histories
    }

def get_allergy_options(db: Session, user_uid: str, status: str = "active") -> List[Allergy]:
    allergies = (
        db.query(Allergy)
        .filter(
            Allergy.status == status,
            (Allergy.created_by == None) | (Allergy.created_by == user_uid)
        )
        .order_by(
            case((Allergy.created_by == None, 0), else_=1),
            Allergy.display_name.asc()
        )
        .all()
    )
    for a in allergies:
        a.category = f"{a.allergy_type}_allergy"
    return allergies

def get_condition_options(db: Session, user_uid: str, status: str = "active") -> List[MedicalCondition]:
    conditions = (
        db.query(MedicalCondition)
        .filter(
            MedicalCondition.status == status,
            (MedicalCondition.created_by == None) | (MedicalCondition.created_by == user_uid)
        )
        .order_by(
            case((MedicalCondition.created_by == None, 0), else_=1),
            MedicalCondition.display_name.asc()
        )
        .all()
    )
    for c in conditions:
        c.category = "chronic_condition" if c.condition_type == "chronic" else "syndrome"
    return conditions

def get_family_history_options(db: Session, user_uid: str, status: str = "active") -> List[FamilyHistory]:
    histories = (
        db.query(FamilyHistory)
        .filter(
            FamilyHistory.status == status,
            (FamilyHistory.created_by == None) | (FamilyHistory.created_by == user_uid)
        )
        .order_by(
            case((FamilyHistory.created_by == None, 0), else_=1),
            FamilyHistory.display_name.asc()
        )
        .all()
    )
    for h in histories:
        h.category = "family_history"
    return histories


