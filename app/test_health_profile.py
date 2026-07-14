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
        form_data = {
            "firstName": "Alice",
            "lastName": "Smith",
            "gender": "Female",
            "dateOfBirth": "1990-08-20"
        }
        r = client.post(f"{BASE_URL}/auth/register", data=form_data)
        assert r.status_code == 200, f"Failed register: {r.text}"
        
        # 4. Save Health Profile
        print("4. Updating Health Profile details via PUT /auth/profile...")
        health_payload = {
            "bloodType": "B+",
            "emergencyContactName": "Bob Smith",
            "emergencyContactPhone": "+15559876543",
            "allergies": {
                "drug": ["Penicillin"],
                "food": ["Nuts"],
                "environmental": ["Pollen"]
            },
            "medicalConditions": {
                "chronicConditions": ["Asthma"],
                "syndromes": ["IBS"],
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
                "familyHistory": ["Hypertension"],
                "additionalNotes": "Takes inhaler when needed",
                "currentMedications": [
                    {"name": "Albuterol", "dosage": "2 puffs", "frequency": "As needed"}
                ]
            }
        }
        
        r = client.put(f"{BASE_URL}/auth/profile", json=health_payload)
        assert r.status_code == 200, f"Failed to update health profile: {r.text}"
        update_resp = r.json()
        assert update_resp["success"] is True
        
        updated_profile = update_resp["data"]["profile"]
        assert updated_profile["bloodType"] == "B+"
        assert updated_profile["emergencyContactName"] == "Bob Smith"
        assert updated_profile["emergencyContactPhone"] == "+15559876543"
        assert updated_profile["allergies"]["drug"] == ["Penicillin"]
        assert updated_profile["medicalConditions"]["chronicConditions"] == ["Asthma"]
        assert updated_profile["medicalConditions"]["currentMedications"][0]["name"] == "Albuterol"
        print("[SUCCESS] Health Profile updated successfully. Values returned match request.")
        
        # 5. Fetch GET /auth/profile to ensure database persistence
        print("5. Getting profile from database via GET /auth/profile to verify persistence...")
        r = client.get(f"{BASE_URL}/auth/profile")
        assert r.status_code == 200, f"Failed GET profile: {r.text}"
        get_resp = r.json()
        persisted_profile = get_resp["data"]["profile"]
        assert persisted_profile["bloodType"] == "B+"
        assert persisted_profile["emergencyContactName"] == "Bob Smith"
        assert persisted_profile["allergies"]["food"] == ["Nuts"]
        assert persisted_profile["medicalConditions"]["lifestyle"]["smoking"] == "Never"
        print("[SUCCESS] Database persistence verified. All details saved correctly.")
        
        print("\n[SUCCESS] HEALTH PROFILE INTEGRATION TEST COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    test_health_profile_flow()
