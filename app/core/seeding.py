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
    # 1. Seed Allergies
    for category in ["drug_allergy", "food_allergy", "environmental_allergy"]:
        allergy_type = category.split("_")[0]
        for name in DEFAULTS[category]:
            slug = slugify(name)
            exists = db.query(Allergy).filter_by(
                allergy_type=allergy_type, slug=slug, created_by=None
            ).first()
            if not exists:
                item = Allergy(
                    allergy_type=allergy_type, slug=slug, display_name=name, created_by=None, status="active"
                )
                db.add(item)

    # 2. Seed Medical Conditions
    for category in ["chronic_condition", "syndrome"]:
        condition_type = "chronic" if category == "chronic_condition" else "syndrome"
        for name in DEFAULTS[category]:
            slug = slugify(name)
            exists = db.query(MedicalCondition).filter_by(
                condition_type=condition_type, slug=slug, created_by=None
            ).first()
            if not exists:
                item = MedicalCondition(
                    condition_type=condition_type, slug=slug, display_name=name, created_by=None, status="active"
                )
                db.add(item)

    # 3. Seed Family History
    for name in DEFAULTS["family_history"]:
        slug = slugify(name)
        exists = db.query(FamilyHistory).filter_by(
            slug=slug, created_by=None
        ).first()
        if not exists:
            item = FamilyHistory(
                slug=slug, display_name=name, created_by=None, status="active"
            )
            db.add(item)

    db.commit()

