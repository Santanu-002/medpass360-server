import httpx
import os
import io

BASE_URL = "http://localhost:8000/api/v1"
STATIC_URL = "http://localhost:8000"

def test_registration_flow():
    print("[START] Starting Registration and Avatar Upload Integration Test...")
    
    # Configure required device headers to bypass DeviceHeaderMiddleware
    device_headers = {
        "X-Device-ID": "test-device-uuid",
        "X-Device-Name": "Integration Test Runner",
        "X-Device-Model": "Python HTTP Client",
        "X-OS-Version": "Python 3.11",
        "X-Platform": "server",
        "X-App-Version": "1.0.0",
        "X-App-Build": "1"
    }
    
    # Create httpx.Client with default headers
    with httpx.Client(headers=device_headers) as client:
        # Use a unique test phone number (e.g., timestamp based)
        import time
        test_phone = f"+1555{int(time.time())}"
        print(f"1. Sending OTP to {test_phone}...")
        
        # 1. Send OTP
        r = client.post(f"{BASE_URL}/auth/create-account", json={"identity": test_phone, "type": "phone"})
        assert r.status_code == 200, f"Failed create-account: {r.text}"
        resp_data = r.json()
        assert resp_data["success"] is True
        otp_id = resp_data["data"]["otpId"]
        print(f"[SUCCESS] OTP sent successfully. Session OTP ID: {otp_id}")
        
        # 2. Verify OTP
        print("2. Verifying OTP...")
        r = client.post(
            f"{BASE_URL}/auth/verify-otp",
            json={"otpId": otp_id, "code": "123456"}  # "123456" is a valid dev OTP
        )
        assert r.status_code == 200, f"Failed verify-otp: {r.text}"
        resp_data = r.json()
        assert resp_data["success"] is True
        
        token_data = resp_data["data"]["token"]
        user_data = resp_data["data"]["user"]
        access_token = token_data["accessToken"]
        user_uid = user_data["uid"]
        
        # Check that profiles list is empty for new users
        assert len(user_data["profiles"]) == 0, "Profiles list should be empty for a new user"
        print("[SUCCESS] OTP verified. User created with no profile (as expected).")
        
        # Set Authorization header in the client
        client.headers["Authorization"] = f"Bearer {access_token}"
        
        # 3. Register user (Upload avatar via /media/upload first, then call /auth/register with json)
        print("3. Uploading avatar first via media upload...")
        mock_file = io.BytesIO(b"fake image data")
        files = {
            "file": ("test_avatar.jpg", mock_file, "image/jpeg")
        }
        form_fields = {
            "purpose": "avatar"
        }
        r = client.post(
            f"{BASE_URL}/media/upload",
            data=form_fields,
            files=files
        )
        assert r.status_code == 200, f"Failed upload: {r.text}"
        upload_resp = r.json()
        uploaded_avatar_url = upload_resp["data"]["url"]

        print("3b. Registering user with basic details and avatar url JSON...")
        register_payload = {
            "firstName": "John",
            "lastName": "Doe",
            "gender": "Male",
            "dateOfBirth": "1995-10-15",
            "avatar": uploaded_avatar_url
        }
        r = client.post(
            f"{BASE_URL}/auth/register",
            json=register_payload
        )
        assert r.status_code == 200, f"Failed register: {r.text}"
        resp_data = r.json()
        assert resp_data["success"] is True
        
        profile_data = next(p for p in resp_data["data"]["profiles"] if p["relation"] == "self")
        assert profile_data is not None
        assert profile_data["firstName"] == "John"
        assert profile_data["lastName"] == "Doe"
        assert profile_data["gender"] == "Male"
        assert profile_data["dateOfBirth"] == "1995-10-15"
        
        avatar_url = profile_data["avatar"]
        assert avatar_url.startswith("/uploads/avatars/")
        print(f"[SUCCESS] User registered. Saved avatar url: {avatar_url}")
        
        # 4. Verify static file serving
        print("4. Verifying static file serving of the uploaded avatar...")
        static_file_url = f"{STATIC_URL}{avatar_url}"
        
        # We don't need device headers for fetching a static file (since static mount doesn't use middleware),
        # but using the same client is perfectly fine.
        r = client.get(static_file_url)
        assert r.status_code == 200, f"Failed static file request: {r.text}"
        assert r.content == b"fake image data"
        print("[SUCCESS] Static file serving verified. Uploaded avatar content matches original.")
        
        # 5. Fetch profile again to verify persistence
        print("5. Querying GET /profile to verify persistence...")
        r = client.get(f"{BASE_URL}/auth/profile")
        assert r.status_code == 200, f"Failed get profile: {r.text}"
        resp_data = r.json()
        assert resp_data["success"] is True
        persisted_profile = next(p for p in resp_data["data"]["profiles"] if p["relation"] == "self")
        assert persisted_profile["avatar"] == avatar_url
        print("[SUCCESS] Profile retrieved and verified. All details persisted.")
        
        # 6. Email-login registration validation test
        print("6. Testing email-login registration flow...")
        test_email = f"test_{int(time.time())}@example.com"
        r = client.post(f"{BASE_URL}/auth/create-account", json={"identity": test_email, "type": "email"})
        assert r.status_code == 200
        otp_id = r.json()["data"]["otpId"]
        
        r = client.post(f"{BASE_URL}/auth/verify-otp", json={"otpId": otp_id, "code": "123456"})
        assert r.status_code == 200
        access_token = r.json()["data"]["token"]["accessToken"]
        
        email_client = httpx.Client(headers={**device_headers, "Authorization": f"Bearer {access_token}"})
        
        # Test 6a: Attempt registering without required phone number (should fail)
        r = email_client.post(
            f"{BASE_URL}/auth/register",
            json={
                "firstName": "Jane",
                "lastName": "Doe",
                "gender": "Female",
                "dateOfBirth": "1998-05-20"
            }
        )
        assert r.status_code == 400, f"Registration should have failed without phone number: {r.text}"
        print("[SUCCESS] Failed without phone number (correctly validated).")
        
        # Test 6b: Register with phone number (should succeed)
        test_phone_email_login = f"+1555{int(time.time()) + 1}"
        r = email_client.post(
            f"{BASE_URL}/auth/register",
            json={
                "firstName": "Jane",
                "lastName": "Doe",
                "gender": "Female",
                "dateOfBirth": "1998-05-20",
                "phoneNumber": test_phone_email_login
            }
        )
        assert r.status_code == 200, f"Failed email-login registration: {r.text}"
        profile = next(p for p in r.json()["data"]["profiles"] if p["relation"] == "self")
        assert profile["phoneNumber"] == test_phone_email_login
        assert profile["email"] == test_email
        print("[SUCCESS] Registered successfully with phone number.")

        # Test 6c: Attempt registering with an already registered phone number by another user (should fail)
        print("Test 6c: Attempting to register duplicate phone number by another user...")
        another_test_email = f"another_test_{int(time.time())}@example.com"
        r = client.post(f"{BASE_URL}/auth/create-account", json={"identity": another_test_email, "type": "email"})
        assert r.status_code == 200
        another_otp_id = r.json()["data"]["otpId"]

        r = client.post(f"{BASE_URL}/auth/verify-otp", json={"otpId": another_otp_id, "code": "123456"})
        assert r.status_code == 200
        another_access_token = r.json()["data"]["token"]["accessToken"]

        another_email_client = httpx.Client(headers={**device_headers, "Authorization": f"Bearer {another_access_token}"})

        r = another_email_client.post(
            f"{BASE_URL}/auth/register",
            json={
                "firstName": "Duplicate",
                "lastName": "User",
                "gender": "Male",
                "dateOfBirth": "1998-05-20",
                "phoneNumber": test_phone_email_login  # already registered by Jane Doe in step 6b
            }
        )
        assert r.status_code == 400, f"Registration should have failed with duplicate phone number: {r.text}"
        json_resp = r.json()
        error_msg = json_resp.get("message", "") or json_resp.get("detail", "")
        assert "Phone number is already in use" in error_msg, f"Expected conflict message, got: {json_resp}"
        print("[SUCCESS] Failed with duplicate phone number (correctly validated).")
        
        print("\n[SUCCESS] ALL TESTS PASSED SUCCESSFULLY! Endpoint is fully functional.")

if __name__ == "__main__":
    test_registration_flow()
