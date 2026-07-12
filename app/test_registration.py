import httpx
import os
import io

BASE_URL = "http://localhost:8000/api/v1"
STATIC_URL = "http://localhost:8000"

def test_registration_flow():
    print("🚀 Starting Registration and Avatar Upload Integration Test...")
    
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
        r = client.post(f"{BASE_URL}/auth/send-otp", json={"identity": test_phone, "type": "phone"})
        assert r.status_code == 200, f"Failed send-otp: {r.text}"
        resp_data = r.json()
        assert resp_data["success"] is True
        otp_id = resp_data["data"]["otpId"]
        print(f"✅ OTP sent successfully. Session OTP ID: {otp_id}")
        
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
        
        # Check that profile is None for new users
        assert user_data["profile"] is None, "Profile should be null/None for a new user"
        print("✅ OTP verified. User created with no profile (as expected).")
        
        # Set Authorization header in the client
        client.headers["Authorization"] = f"Bearer {access_token}"
        
        # 3. Register user (Form + File upload)
        print("3. Registering user with basic details and avatar file...")
        
        # Create a mock image file
        mock_file = io.BytesIO(b"fake image data")
        
        form_data = {
            "firstName": "John",
            "lastName": "Doe",
            "gender": "Male",
            "dateOfBirth": "1995-10-15"
        }
        files = {
            "avatar": ("test_avatar.jpg", mock_file, "image/jpeg")
        }
        
        r = client.post(
            f"{BASE_URL}/auth/register",
            data=form_data,
            files=files
        )
        assert r.status_code == 200, f"Failed register: {r.text}"
        resp_data = r.json()
        assert resp_data["success"] is True
        
        profile_data = resp_data["data"]["profile"]
        assert profile_data is not None
        assert profile_data["firstName"] == "John"
        assert profile_data["lastName"] == "Doe"
        assert profile_data["gender"] == "Male"
        assert profile_data["dateOfBirth"] == "1995-10-15"
        
        avatar_url = profile_data["avatar"]
        assert avatar_url == f"/uploads/avatars/{user_uid}_avatar.jpg"
        print(f"✅ User registered. Saved avatar url: {avatar_url}")
        
        # 4. Verify static file serving
        print("4. Verifying static file serving of the uploaded avatar...")
        static_file_url = f"{STATIC_URL}{avatar_url}"
        
        # We don't need device headers for fetching a static file (since static mount doesn't use middleware),
        # but using the same client is perfectly fine.
        r = client.get(static_file_url)
        assert r.status_code == 200, f"Failed static file request: {r.text}"
        assert r.content == b"fake image data"
        print("✅ Static file serving verified. Uploaded avatar content matches original.")
        
        # 5. Fetch profile again to verify persistence
        print("5. Querying GET /profile to verify persistence...")
        r = client.get(f"{BASE_URL}/auth/profile")
        assert r.status_code == 200, f"Failed get profile: {r.text}"
        resp_data = r.json()
        assert resp_data["success"] is True
        persisted_profile = resp_data["data"]["profile"]
        assert persisted_profile["avatar"] == avatar_url
        print("✅ Profile retrieved and verified. All details persisted.")
        
        # 6. Email-login registration validation test
        print("6. Testing email-login registration flow...")
        test_email = f"test_{int(time.time())}@example.com"
        r = client.post(f"{BASE_URL}/auth/send-otp", json={"identity": test_email, "type": "email"})
        assert r.status_code == 200
        otp_id = r.json()["data"]["otpId"]
        
        r = client.post(f"{BASE_URL}/auth/verify-otp", json={"otpId": otp_id, "code": "123456"})
        assert r.status_code == 200
        access_token = r.json()["data"]["token"]["accessToken"]
        
        email_client = httpx.Client(headers={**device_headers, "Authorization": f"Bearer {access_token}"})
        
        # Test 6a: Attempt registering without required phone number (should fail)
        r = email_client.post(
            f"{BASE_URL}/auth/register",
            data={
                "firstName": "Jane",
                "lastName": "Doe",
                "gender": "Female",
                "dateOfBirth": "1998-05-20"
            }
        )
        assert r.status_code == 400, f"Registration should have failed without phone number: {r.text}"
        print("✅ Failed without phone number (correctly validated).")
        
        # Test 6b: Register with phone number (should succeed)
        r = email_client.post(
            f"{BASE_URL}/auth/register",
            data={
                "firstName": "Jane",
                "lastName": "Doe",
                "gender": "Female",
                "dateOfBirth": "1998-05-20",
                "phoneNumber": "+15559876543"
            }
        )
        assert r.status_code == 200, f"Failed email-login registration: {r.text}"
        profile = r.json()["data"]["profile"]
        assert profile["phoneNumber"] == "+15559876543"
        assert profile["email"] == test_email
        print("✅ Registered successfully with phone number.")
        
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! Endpoint is fully functional.")

if __name__ == "__main__":
    test_registration_flow()
