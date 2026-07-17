# Implementation Plan: Separate Catalog Tables + Single Profile Selection Table

## Goal Description

Refactor the database schema to use **separate catalog tables** but **exactly one single profile selection table** (junction table) to store selections.

Under this design:
1. **Catalog Tables** (master vocabulary containing default seeded data and user-added custom items):
   - `allergies` (holds drug, food, environmental allergies)
   - `medical_conditions` (holds chronic conditions and syndromes)
   - `family_histories` (holds family history items)
   
   These tables store the `display_name`, `slug`, `created_by`, and `status`. They have **no** profile columns.

2. **Single Profile Selection Table** (`profile_medical_selections`):
   - A single table containing profile selections for all categories.
   - Maps `profile_id` to catalog item `item_uid` along with the item's `category`.
   - Contains `duration` (used for conditions) and `created_at`.
   - Does **not** contain `created_by`, `display_name`, or `slug` (those belong to the catalog tables).

---

## Proposed Database Schema

### 1. Catalog Models (No Profile Columns)

```python
class Allergy(Base):
    __tablename__ = "allergies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    allergy_type = Column(String(50), nullable=False)  # 'drug', 'food', 'environmental'
    slug = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="active")
    
    __table_args__ = (
        UniqueConstraint('allergy_type', 'slug', name='uq_allergies_type_slug'),
    )

class MedicalCondition(Base):
    __tablename__ = "medical_conditions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    condition_type = Column(String(50), nullable=False)  # 'chronic', 'syndrome'
    slug = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="active")

    __table_args__ = (
        UniqueConstraint('condition_type', 'slug', name='uq_conditions_type_slug'),
    )

class FamilyHistory(Base):
    __tablename__ = "family_histories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    created_by = Column(String(36), ForeignKey("users.uid", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="active")

    __table_args__ = (
        UniqueConstraint('slug', name='uq_family_histories_slug'),
    )
```

### 2. Single Unified Profile Selection Model

```python
class ProfileMedicalSelection(Base):
    __tablename__ = "profile_medical_selections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    item_uid = Column(String(36), nullable=False, index=True) # Point to catalog item UID
    category = Column(String(50), nullable=False, index=True)  # 'drug_allergy', 'food_allergy', 'environmental_allergy', 'chronic_condition', 'syndrome', 'family_history'
    duration = Column(String(100), nullable=True) # Only used for conditions
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    profile = relationship("Profile", back_populates="medical_selections_rel")
```

---

## User Review Required

> [!NOTE]
> Storing `item_uid` (String UUID) + `category` inside the single `profile_medical_selections` table allows us to easily lookup catalog entries across the separate catalog tables (`allergies`, `medical_conditions`, `family_histories`) dynamically using their unique UUIDs, avoiding multiple junction tables.

---

## Proposed Changes

### 1. `app/models/profile.py`
- Define separate catalog models: `Allergy`, `MedicalCondition`, `FamilyHistory`.
- Define a single junction model: `ProfileMedicalSelection`.
- Add `medical_selections_rel` relationship to `Profile`.
- Implement serialization properties on `Profile` to load catalog details dynamically by looking up `item_uid` from the respective catalog tables.

### 2. `app/models/__init__.py`
- Expose the new/updated classes and remove old references.

### 3. `app/crud/medical_option.py`
- Update get queries to load from the separate catalog tables (`Allergy`, `MedicalCondition`, `FamilyHistory`).

### 4. `app/api/v1/endpoints/medical_option.py`
- Adapt option mapping logic to map from separate catalog models.

### 5. `app/crud/user.py`
- Update `update_profile` save logic:
  - Find/create catalog entries in `Allergy`, `MedicalCondition`, and `FamilyHistory`.
  - Save links to the single table `ProfileMedicalSelection` using the item's `uid` and its category.

### 6. `app/core/seeding.py`
- Update seeding script to seed default options back into `Allergy`, `MedicalCondition`, and `FamilyHistory`.

### 7. Database Migration
- Generate a new Alembic migration script to drop the old database structures, create the new tables, migrate existing data, and update Alembic history.

---

## Verification Plan

### Automated Tests
1. Run `.venv\Scripts\python.exe -m app.reset_db` to ensure schema creation and seeding runs successfully.
2. Run `test_endpoints.py` to confirm that verification, profile saving, and login profiles retrieval all work perfectly.
