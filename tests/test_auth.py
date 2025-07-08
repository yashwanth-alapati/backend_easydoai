from fastapi.testclient import TestClient
from main import app, get_db
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# --- Test Database Setup ---
# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# --- Pytest Fixtures ---
@pytest.fixture(scope="module")
def db_session():
    # Create the tables in the test database
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop the tables after tests are done
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client(db_session):
    # Dependency override to use the test database
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    # Clean up the override after tests
    del app.dependency_overrides[get_db]


# --- Tests ---
# Note: Tests now take the `client` fixture as an argument.
@pytest.mark.dependency()
def test_user_signup(client):
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
def test_user_login(client):
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
def test_failed_login(client):
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
