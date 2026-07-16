from sqlalchemy.orm import Session
from app.models.profile import Allergy, MedicalCondition, FamilyHistory
from app.core.utils import slugify

DEFAULTS = {
    "chronic_condition": ["Hypertension", "Type 2 Diabetes", "Asthma", "Chronic Kidney Disease", "COPD", "Thyroid Disorder"],
    "syndrome": ["Down Syndrome", "Irritable Bowel Syndrome (IBS)", "Polycystic Ovary Syndrome (PCOS)", "Chronic Fatigue Syndrome"],
    "drug_allergy": ["Penicillin", "Sulfa drugs", "Aspirin", "Ibuprofen"],
    "food_allergy": ["Peanuts", "Shellfish", "Milk", "Eggs", "Soy", "Wheat"],
    "environmental_allergy": ["Pollen", "Dust Mites", "Mold", "Pet Dander"],
    "family_history": ["Heart Disease", "Stroke", "Cancer", "Hypertension", "Diabetes"]
}

def seed_default_medical_options(db: Session):
    # 1. Chronic conditions
    for name in DEFAULTS["chronic_condition"]:
        slug = slugify(name)
        exists = db.query(MedicalCondition).filter_by(
            profile_id=None, condition_type="chronic", slug=slug, created_by=None
        ).first()
        if not exists:
            item = MedicalCondition(
                profile_id=None, condition_type="chronic", slug=slug, display_name=name, created_by=None, status="active"
            )
            db.add(item)

    # 2. Syndromes
    for name in DEFAULTS["syndrome"]:
        slug = slugify(name)
        exists = db.query(MedicalCondition).filter_by(
            profile_id=None, condition_type="syndrome", slug=slug, created_by=None
        ).first()
        if not exists:
            item = MedicalCondition(
                profile_id=None, condition_type="syndrome", slug=slug, display_name=name, created_by=None, status="active"
            )
            db.add(item)

    # 3. Drug allergies
    for name in DEFAULTS["drug_allergy"]:
        slug = slugify(name)
        exists = db.query(Allergy).filter_by(
            profile_id=None, allergy_type="drug", slug=slug, created_by=None
        ).first()
        if not exists:
            item = Allergy(
                profile_id=None, allergy_type="drug", slug=slug, display_name=name, created_by=None, status="active"
            )
            db.add(item)

    # 4. Food allergies
    for name in DEFAULTS["food_allergy"]:
        slug = slugify(name)
        exists = db.query(Allergy).filter_by(
            profile_id=None, allergy_type="food", slug=slug, created_by=None
        ).first()
        if not exists:
            item = Allergy(
                profile_id=None, allergy_type="food", slug=slug, display_name=name, created_by=None, status="active"
            )
            db.add(item)

    # 5. Environmental allergies
    for name in DEFAULTS["environmental_allergy"]:
        slug = slugify(name)
        exists = db.query(Allergy).filter_by(
            profile_id=None, allergy_type="environmental", slug=slug, created_by=None
        ).first()
        if not exists:
            item = Allergy(
                profile_id=None, allergy_type="environmental", slug=slug, display_name=name, created_by=None, status="active"
            )
            db.add(item)

    # 6. Family history
    for name in DEFAULTS["family_history"]:
        slug = slugify(name)
        exists = db.query(FamilyHistory).filter_by(
            profile_id=None, slug=slug, created_by=None
        ).first()
        if not exists:
            item = FamilyHistory(
                profile_id=None, slug=slug, display_name=name, created_by=None, status="active"
            )
            db.add(item)

    db.commit()
