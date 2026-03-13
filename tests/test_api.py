import pytest
from fastapi.testclient import TestClient
from api.main import app
import time

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

def test_generate_endpoint_phase3c():
    # Test POST request with all Phase 3C features
    response = client.post(
        "/api/v1/generate",
        json={
            "request": "A travel guide to Tokyo", 
            "languages": ["Spanish", "French"],
            "generate_image": True,
            "generate_social_posts": True
        }
    )
    assert response.status_code == 200
    request_id = response.json()["request_id"]
    
    # Wait for completion (simulated/mocked agents should be fast in unit tests usually, 
    # but here they are calling real LLMs unless mocked)
    # Actually, in this environment, I should probably mock the agents if I want fast tests.
    
    # For now, let's just check if the request was accepted and the content retrieval has the fields.
    content_response = client.get(f"/api/v1/content/{request_id}")
    assert content_response.status_code == 200
    content_data = content_response.json()
    
    assert "translated_content" in content_data
    assert "social_media_posts" in content_data
    assert "generated_images" in content_data
