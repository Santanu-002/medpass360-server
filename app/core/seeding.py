from sqlalchemy.orm import Session
from app.models.medical_option import MedicalOption
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
    for category, names in DEFAULTS.items():
        for name in names:
            slug = slugify(name)
            exists = db.query(MedicalOption).filter_by(category=category, slug=slug, created_by=None).first()
            if not exists:
                item = MedicalOption(category=category, slug=slug, display_name=name, created_by=None, status="active")
                db.add(item)
    db.commit()
