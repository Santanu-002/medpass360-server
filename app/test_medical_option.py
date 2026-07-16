import httpx
import time
from app.core.database import SessionLocal
from app.models.medical_option import MedicalOption
from app.core.utils import slugify

BASE_URL = "http://localhost:8000/api/v1"

def test_medical_options_flow():
    print("[START] Starting Medical Options Integration Test...")
    
    # Configure required device headers to bypass DeviceHeaderMiddleware
    device_headers = {
        "X-Device-ID": "test-device-uuid-medical-options",
        "X-Device-Name": "Integration Test Runner",
        "X-Device-Model": "Python HTTP Client",
        "X-OS-Version": "Python 3.11",
        "X-Platform": "server",
        "X-App-Version": "1.0.0",
        "X-App-Build": "1"
    }
    
    with httpx.Client(headers=device_headers) as client:
        # 1. Create a test user via OTP flow
        test_phone = f"+1555{int(time.time())}"
        print(f"1. Creating test user with phone {test_phone}...")
        
        # Send OTP
        r = client.post(f"{BASE_URL}/auth/create-account", json={"identity": test_phone, "type": "phone"})
        assert r.status_code == 200, f"Failed create-account: {r.text}"
        resp_data = r.json()
        assert resp_data["success"] is True
        otp_id = resp_data["data"]["otpId"]
        
        # Verify OTP
        r = client.post(
            f"{BASE_URL}/auth/verify-otp",
            json={"otpId": otp_id, "code": "123456"}  # "123456" is dev OTP
        )
        assert r.status_code == 200, f"Failed verify-otp: {r.text}"
        resp_data = r.json()
        assert resp_data["success"] is True
        
        token_data = resp_data["data"]["token"]
        user_data = resp_data["data"]["user"]
        access_token = token_data["accessToken"]
        user_uid = user_data["uid"]
        print(f"[SUCCESS] Test user created. UID: {user_uid}")
        
        # Set Authorization header in the client
        client.headers["Authorization"] = f"Bearer {access_token}"
        
        # 2. Add a custom user-added medical option directly to the database
        print("2. Inserting user-specific custom medical option into database...")
        db = SessionLocal()
        custom_display_name = "My Custom Penicillin Allergy"
        custom_slug = slugify(custom_display_name)
        try:
            custom_item = MedicalOption(
                category="drug_allergy",
                slug=custom_slug,
                display_name=custom_display_name,
                created_by=user_uid,
                status="active"
            )
            db.add(custom_item)
            db.commit()
            db.refresh(custom_item)
            custom_uid = custom_item.uid
            print(f"[SUCCESS] Custom option inserted. UID: {custom_uid}")
        finally:
            db.close()
            
        # 3. Call GET /medical-options
        print("3. Querying GET /medical-options endpoint...")
        r = client.get(f"{BASE_URL}/medical-options")
        assert r.status_code == 200, f"Failed GET /medical-options: {r.text}"
        resp_data = r.json()
        assert resp_data["success"] is True
        
        data = resp_data["data"]
        # Verify camelCase keys are returned
        assert "chronicConditions" in data
        assert "syndromes" in data
        assert "drugAllergies" in data
        assert "foodAllergies" in data
        assert "environmentalAllergies" in data
        assert "familyHistory" in data
        
        print("[SUCCESS] Grouping keys confirmed: chronicConditions, syndromes, drugAllergies, foodAllergies, environmentalAllergies, familyHistory")
        
        # Verify that default seeded options are returned
        chronic_conditions = data["chronicConditions"]
        assert len(chronic_conditions) > 0
        default_names = [item["displayName"] for item in chronic_conditions]
        assert "Hypertension" in default_names
        print(f"[SUCCESS] Found seeded default chronic condition: Hypertension")
        
        # Verify that the custom user-added option is returned in drugAllergies
        drug_allergies = data["drugAllergies"]
        assert len(drug_allergies) > 0
        custom_items_found = [item for item in drug_allergies if item["slug"] == custom_slug]
        assert len(custom_items_found) == 1, "Custom option was not found in the response"
        
        custom_response_item = custom_items_found[0]
        assert custom_response_item["displayName"] == custom_display_name
        assert custom_response_item["createdBy"] == user_uid
        assert custom_response_item["status"] == "active"
        print(f"[SUCCESS] Found custom option: {custom_display_name}")
        
        # Verify sorting: defaults (createdBy is null) should be first, user-added second
        # The query should place created_by = NULL (0) before created_by = user_uid (1)
        created_by_values = [item["createdBy"] for item in drug_allergies]
        
        # Ensure that no user-specific options appear before any default options
        # In other words, once we see a non-null createdBy, all subsequent ones must be non-null (or the list is sorted by nulls first)
        seen_non_null = False
        for cb in created_by_values:
            if cb is not None:
                seen_non_null = True
            else:
                assert not seen_non_null, "Seeding/sorting error: default option (createdBy=null) appeared after a user-specific option!"
        print("[SUCCESS] Sorting order validated: defaults appear first, followed by user-created options.")
        
        # 4. Filter by status=inactive
        print("4. Testing status=inactive filter...")
        r = client.get(f"{BASE_URL}/medical-options?status=inactive")
        assert r.status_code == 200, f"Failed GET /medical-options?status=inactive: {r.text}"
        inactive_data = r.json()["data"]
        
        # No defaults or active options should be here since we haven't deactivated any
        for category_key in inactive_data:
            assert len(inactive_data[category_key]) == 0, f"Inactive list for {category_key} should be empty"
        print("[SUCCESS] Inactive filter validated (returned 0 options).")
        
        print("[FINISH] All checks passed successfully!")

if __name__ == "__main__":
    test_medical_options_flow()
