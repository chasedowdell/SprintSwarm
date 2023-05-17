import json
from fastapi.testclient import TestClient
from services.backlog.app import app

client = TestClient(app)

def test_add_item():
    new_item = {
        "item": {
            "id": "1",
            "description": "Implement user authentication",
            "closure_criteria": "User can securely log in and log out",
            "status": 0,
            "priority": 1,
            "assignee": "AI Developer"
        }
    }

    response = client.post("/add_item", data=json.dumps(new_item))
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "new item added"}
