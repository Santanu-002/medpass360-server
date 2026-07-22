import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path so it finds app package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.models.user import User
from app.models.profile import Profile
from app.models.profile_access import ProfileAccess
from app.crud import user as crud_user
from app.schemas.user import ProfileUpdate
from app.schemas.profile_access import ProfileAccessLevel

def test_permissions_flow():
    print("Connecting to database...")
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 1. Setup clean data for test
        print("Cleaning up old test users...")
        db.query(ProfileAccess).delete()
        db.query(Profile).delete()
        db.query(User).delete()
        db.commit()

        # 2. Create Father (userA)
        print("Creating Father user...")
        father_user = User(uid="father-uid", phone_number="+911111111111", email="father@test.com")
        db.add(father_user)
        db.commit()

        # 3. Create Father's profile (self relation)
        print("Creating Father's profile...")
        father_profile = crud_user.create_profile(
            db=db,
            user_uid=father_user.uid,
            first_name="Father",
            last_name="One",
            gender="Male",
            date_of_birth="1980-01-01",
            relation="self"
        )
        
        # Verify Father's profile has owner access record
        access_father = db.query(ProfileAccess).filter(
            ProfileAccess.profile_id == father_profile.id,
            ProfileAccess.user_id == father_user.uid
        ).first()
        assert access_father is not None
        assert access_father.access_level == "owner"
        assert access_father.relation == "self"
        print("[OK] Father's profile access verified as owner/self.")

        # 4. Father creates Son's profile
        print("Father creating Son's profile...")
        profile_update_data = ProfileUpdate(
            first_name="Son",
            last_name="One",
            phone_number="+912222222222",
            email="son@test.com",
            relation="son",
            date_of_birth="2010-05-15",
            gender="Male"
        )
        
        son_profile = crud_user.update_profile(
            db=db,
            user_uid=father_user.uid,
            profile_update=profile_update_data
        )
        assert son_profile is not None
        print(f"[OK] Son's profile created with UID: {son_profile.uid}")

        # Verify access mappings for the care profile
        # a. Son (the owner) must have owner access to self
        access_son_owner = db.query(ProfileAccess).filter(
            ProfileAccess.profile_id == son_profile.id,
            ProfileAccess.user_id == son_profile.user_id
        ).first()
        assert access_son_owner is not None
        assert access_son_owner.access_level == "owner"
        assert access_son_owner.relation == "self"
        print("[OK] Son's owner access mapped to self.")

        # b. Father must have full_access to son
        access_father_son = db.query(ProfileAccess).filter(
            ProfileAccess.profile_id == son_profile.id,
            ProfileAccess.user_id == father_user.uid
        ).first()
        assert access_father_son is not None
        assert access_father_son.access_level == "full_access"
        assert access_father_son.relation == "son"
        print("[OK] Father's access mapped to full_access/son.")

        # 5. Fetch profiles list relative to Son (representing Son logging in)
        print("Retrieving profiles for Son...")
        son_user = db.query(User).filter(User.uid == son_profile.user_id).first()
        assert son_user is not None
        
        son_profiles = son_user.profiles
        assert len(son_profiles) == 1
        assert son_profiles[0].relation == "self"
        assert son_profiles[0].access_level == "owner"
        print("[OK] Son logs in and sees their relation is dynamically resolved to 'self' and level 'owner'!")

        # 6. Fetch profiles list relative to Father (representing Father logging in)
        print("Retrieving profiles for Father...")
        father_profiles = father_user.profiles
        assert len(father_profiles) == 2
        # Father sees himself first
        assert father_profiles[0].relation == "self"
        assert father_profiles[0].access_level == "owner"
        # Father sees son next
        assert father_profiles[1].relation == "son"
        assert father_profiles[1].access_level == "full_access"
        print("[OK] Father logs in and sees himself as 'self' and son dynamically resolved to 'son'!")

        # 7. Son revokes Father's access
        print("Son revoking Father's access...")
        access_to_revoke = db.query(ProfileAccess).filter(
            ProfileAccess.profile_id == son_profile.id,
            ProfileAccess.user_id == father_user.uid,
            ProfileAccess.revoked_at.is_(None)
        ).first()
        assert access_to_revoke is not None
        
        from datetime import datetime
        access_to_revoke.revoked_at = datetime.utcnow()
        access_to_revoke.revoked_by = son_user.uid
        db.add(access_to_revoke)
        db.commit()

        # 8. Re-evaluate profiles list for Father
        print("Re-evaluating profiles for Father after revoke...")
        db.refresh(father_user)
        father_profiles_after = father_user.profiles
        assert len(father_profiles_after) == 1
        assert father_profiles_after[0].uid == father_profile.uid
        print("[OK] Father no longer sees Son in their profile list after revoke!")

        print("\n=== ALL ACCESS PERMISSION TESTS PASSED SUCCESSFULLY! ===")

    finally:
        db.close()

if __name__ == "__main__":
    test_permissions_flow()
