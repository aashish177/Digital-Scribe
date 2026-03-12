import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_generate_endpoint():
    # Test POST request
    response = client.post(
        "/api/v1/generate",
        json={"request": "test API request", "word_count": 50, "tone": "friendly"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert data["message"] == "Content generation started. Poll status endpoint for updates."
    
    request_id = data["request_id"]
    
    # Test GET status endpoint
    status_response = client.get(f"/api/v1/status/{request_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] in ["pending", "processing", "completed", "failed"]

    # Test GET content endpoint
    content_response = client.get(f"/api/v1/content/{request_id}")
    assert content_response.status_code == 200

def test_generate_endpoint_with_approval():
    # Test POST request with require_approval=True
    response = client.post(
        "/api/v1/generate",
        json={"request": "test API request", "require_approval": True}
    )
    assert response.status_code == 200
    request_id = response.json()["request_id"]
    
    # Needs to transition to awaiting_approval
    import time
    max_retries = 30
    for _ in range(max_retries):
        status = client.get(f"/api/v1/status/{request_id}").json()["status"]
        if status == "awaiting_approval":
            break
        time.sleep(0.5)
        
    assert client.get(f"/api/v1/status/{request_id}").json()["status"] == "awaiting_approval"
    
    # Try POST approve
    approve_res = client.post(f"/api/v1/approve/{request_id}")
    assert approve_res.status_code == 200
    app_status = client.get(f"/api/v1/status/{request_id}").json()["status"]
    assert app_status in ["processing", "completed", "failed"]
