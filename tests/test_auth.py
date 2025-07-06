from fastapi.testclient import TestClient
from main import app
import pytest

# The TestClient allows you to send HTTP requests to your FastAPI app from your tests.
client = TestClient(app)

# Use pytest.mark.dependency to create dependencies between tests
# The login test will only run if the signup test passes.
@pytest.mark.dependency()
def test_user_signup():
    """
    Tests the user signup endpoint.
    - Sends a POST request to /signup with new user credentials.
    - Asserts that the response status code is 200 (OK).
    - Asserts that the response message indicates a successful signup.
    """
    response = client.post(
        "/signup",
        json={"email": "testuser@example.com", "password": "testpassword"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Signup successful"}


@pytest.mark.dependency(depends=["test_user_signup"])
def test_user_login():
    """
    Tests the user login endpoint after a successful signup.
    - Sends a POST request to /login with the credentials created in the signup test.
    - Asserts that the response status code is 200 (OK).
    - Asserts that the response message indicates a successful login.
    """
    response = client.post(
        "/login",
        json={"email": "testuser@example.com", "password": "testpassword"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Login successful"}


@pytest.mark.dependency(depends=["test_user_signup"])
def test_failed_login():
    """
    Tests that login fails with an incorrect password.
    - Sends a POST request to /login with the correct email but wrong password.
    - Asserts that the response status code is 401 (Unauthorized).
    - Asserts that the response detail indicates invalid credentials.
    """
    response = client.post(
        "/login",
        json={"email": "testuser@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials" 