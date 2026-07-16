import httpx
import os
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_health_profile_flow():
    print("[START] Starting Health Profile Integration Test...")
    
    device_headers = {
        "X-Device-ID": "test-health-device-uuid",
        "X-Device-Name": "Integration Test Runner",
        "X-Device-Model": "Python HTTP Client",
        "X-OS-Version": "Python 3.11",
        "X-Platform": "server",
        "X-App-Version": "1.0.0",
        "X-App-Build": "1"
    }
    
    with httpx.Client(headers=device_headers, timeout=30.0) as client:
        test_phone = f"+1555{int(time.time())}"
        print(f"1. Sending OTP to {test_phone}...")
        
        r = client.post(f"{BASE_URL}/auth/create-account", json={"identity": test_phone, "type": "phone"})
        assert r.status_code == 200, f"Failed create-account: {r.text}"
        otp_id = r.json()["data"]["otpId"]
        
        print("2. Verifying OTP...")
        r = client.post(
            f"{BASE_URL}/auth/verify-otp",
            json={"otpId": otp_id, "code": "123456"}
        )
        assert r.status_code == 200, f"Failed verify-otp: {r.text}"
        resp_data = r.json()
        access_token = resp_data["data"]["token"]["accessToken"]
        client.headers["Authorization"] = f"Bearer {access_token}"
        
        print("3. Registering user profile...")
        register_payload = {
            "firstName": "Alice",
            "lastName": "Smith",
            "gender": "Female",
            "dateOfBirth": "1990-08-20",
            "avatar": None,
            "phoneNumber": None,
            "email": None
        }
        r = client.post(f"{BASE_URL}/auth/register", json=register_payload)
        assert r.status_code == 200, f"Failed register: {r.text}"
        
        health_payload = {
            "profileTarget": "me",
            "vitals": {
                "bloodType": "B+",
                "height": {"value": "180", "unit": "cm"},
                "weight": {"value": "75", "unit": "kg"}
            },
            "emergencyContact": {
                "name": "Bob Smith",
                "phone": "+15559876543"
            },
            "allergies": {
                "drug": [{"uid": "", "displayName": "Penicillin"}],
                "food": [{"uid": "", "displayName": "Nuts"}],
                "environmental": [{"uid": "", "displayName": "Pollen"}]
            },
            "chronicConditions": [{"uid": "", "displayName": "Asthma"}],
            "syndromes": [{"uid": "", "displayName": "IBS"}],
            "durations": {"Asthma": "5+ years", "IBS": "1–3 years"},
            "lifestyle": {
                "smoking": "Never",
                "alcohol": "Occasional",
                "physicalActivity": "Moderate"
            },
            "recentHistory": {
                "lastDoctorVisit": "2026-06-01",
                "visitReason": "Annual Physical",
                "recentSurgeries": "None"
            },
            "familyHistory": [{"uid": "", "displayName": "Hypertension"}],
            "additionalNotes": "Takes inhaler when needed",
            "currentMedications": [
                {
                    "name": "Albuterol",
                    "slug": "albuterol",
                    "dosage": "2 puffs",
                    "frequency": "As needed",
                    "timings": ["morning"],
                    "instructions": "Use as needed",
                    "foodRelation": "none",
                    "tags": []
                }
            ]
        }
        
        r = client.put(f"{BASE_URL}/auth/profile", json=health_payload)
        assert r.status_code == 200, f"Failed to update health profile: {r.text}"
        update_resp = r.json()
        assert update_resp["success"] is True
        
        updated_profile = update_resp["data"]["profile"]
        assert updated_profile["vitals"]["bloodType"] == "B+"
        assert updated_profile["vitals"]["height"]["value"] == "180"
        assert updated_profile["vitals"]["height"]["unit"] == "cm"
        assert updated_profile["vitals"]["weight"]["value"] == "75"
        assert updated_profile["vitals"]["weight"]["unit"] == "kg"
        assert updated_profile["emergencyContact"]["name"] == "Bob Smith"
        assert updated_profile["emergencyContact"]["phone"] == "+15559876543"
        assert updated_profile["allergies"]["drug"] == [{"uid": "", "displayName": "Penicillin"}]
        assert updated_profile["chronicConditions"] == [{"uid": "", "displayName": "Asthma"}]
        assert updated_profile["currentMedications"][0]["name"] == "Albuterol"
        assert updated_profile["currentMedications"][0]["timings"] == ["morning"]
        print("[SUCCESS] Health Profile updated successfully. Values returned match request.")
        
        # 5. Fetch GET /auth/profile to ensure database persistence
        print("5. Getting profile from database via GET /auth/profile to verify persistence...")
        r = client.get(f"{BASE_URL}/auth/profile")
        assert r.status_code == 200, f"Failed GET profile: {r.text}"
        get_resp = r.json()
        persisted_profile = get_resp["data"]["profile"]
        assert persisted_profile["vitals"]["bloodType"] == "B+"
        assert persisted_profile["emergencyContact"]["name"] == "Bob Smith"
        assert persisted_profile["allergies"]["food"] == [{"uid": "", "displayName": "Nuts"}]
        assert persisted_profile["lifestyle"]["smoking"] == "Never"
        print("[SUCCESS] Database persistence verified. All details saved correctly.")
        
        # 6. Test 'Someone I Care For' flow
        print("\n6. Testing 'Someone I Care For' flow...")
        care_phone = f"+1555{int(time.time()) + 1}"
        print(f"Creating a new primary user A ({care_phone})...")
        r = client.post(f"{BASE_URL}/auth/create-account", json={"identity": care_phone, "type": "phone"})
        assert r.status_code == 200, f"Failed user A create-account: {r.text}"
        otp_id_2 = r.json()["data"]["otpId"]
        
        r = client.post(f"{BASE_URL}/auth/verify-otp", json={"otpId": otp_id_2, "code": "123456"})
        assert r.status_code == 200, f"Failed user A verify-otp: {r.text}"
        access_token_2 = r.json()["data"]["token"]["accessToken"]
        
        # Build client headers for user A
        user_a_client = httpx.Client(headers={**device_headers, "Authorization": f"Bearer {access_token_2}"}, timeout=30.0)
        
        print("Registering user A...")
        r = user_a_client.post(f"{BASE_URL}/auth/register", json={
            "firstName": "John",
            "lastName": "Doe",
            "gender": "Male",
            "dateOfBirth": "1985-05-15",
            "avatar": None,
            "phoneNumber": None,
            "email": None
        })
        assert r.status_code == 200, f"Failed user A register: {r.text}"
        user_a_uid = r.json()["data"]["uid"]
        
        print("Submitting health profile for 'Someone I Care For' (Spouse)...")
        care_person_identity = f"+1555{int(time.time()) + 100}"
        care_payload = {
            "profileTarget": "other",
            "carePerson": {
                "name": "Mary Doe",
                "identity": care_person_identity,
                "gender": "Female",
                "dob": "1987-10-10",
                "relation": "Spouse",
                "avatar": "/uploads/mary.jpg"
            },
            "vitals": {
                "bloodType": "A-",
                "height": {"value": "165", "unit": "cm"},
                "weight": {"value": "60", "unit": "kg"}
            },
            "emergencyContact": {
                "name": "John Doe",
                "phone": care_phone
            },
            "allergies": {
                "drug": [{"uid": "", "displayName": "Sulfa"}],
                "food": [],
                "environmental": []
            },
            "chronicConditions": [],
            "syndromes": [],
            "durations": {},
            "lifestyle": {
                "smoking": "Never",
                "alcohol": "Never",
                "physicalActivity": "Sedentary"
            },
            "recentHistory": {
                "lastDoctorVisit": "2026-05-01",
                "visitReason": "Checkup",
                "recentSurgeries": "None"
            },
            "familyHistory": [],
            "additionalNotes": "",
            "currentMedications": []
        }
        
        r = user_a_client.put(f"{BASE_URL}/auth/profile", json=care_payload)
        assert r.status_code == 200, f"Failed to update care profile: {r.text}"
        res = r.json()
        assert res["success"] is True
        assert res["data"]["isHealthProfileCompleted"] is True
        
        print("7. Verifying care person can log in and see their profile...")
        r = client.post(f"{BASE_URL}/auth/login/otp", json={"identity": care_person_identity, "type": "phone"})
        assert r.status_code == 200, f"Failed login otp for care person: {r.text}"
        otp_id_3 = r.json()["data"]["otpId"]
        
        r = client.post(f"{BASE_URL}/auth/verify-otp", json={"otpId": otp_id_3, "code": "123456"})
        assert r.status_code == 200, f"Failed verify-otp for care person: {r.text}"
        access_token_3 = r.json()["data"]["token"]["accessToken"]
        
        # Get Mary's profile
        mary_client = httpx.Client(headers={**device_headers, "Authorization": f"Bearer {access_token_3}"}, timeout=30.0)
        r = mary_client.get(f"{BASE_URL}/auth/profile")
        assert r.status_code == 200, f"Failed to get Mary's profile: {r.text}"
        mary_profile = r.json()["data"]["profile"]
        
        assert mary_profile["firstName"] == "Mary"
        assert mary_profile["lastName"] == "Doe"
        assert mary_profile["gender"] == "Female"
        assert mary_profile["relation"] == "Spouse"
        assert mary_profile["createdBy"] == user_a_uid
        assert mary_profile["vitals"]["bloodType"] == "A-"
        assert mary_profile["allergies"]["drug"] == [{"uid": "", "displayName": "Sulfa"}]
        print("[SUCCESS] Care person profile successfully retrieved and verified.")
        
        print("\n[SUCCESS] HEALTH PROFILE INTEGRATION TEST COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    test_health_profile_flow()

