import json
from fastapi.testclient import TestClient
from services.ai_product_owner.app import app

client = TestClient(app)


def test_receive_product_vision():
    product_vision = {
        "title": "AI-Powered Personal Finance Manager",
        "description": "An AI-driven personal finance management tool that helps users track expenses and make better financial decisions.",
        "goals": [
            "Provide a clear overview of the user's financial situation",
            "Offer personalized suggestions for improving financial health",
            "Integrate with major banks and financial institutions"
        ],
        "key_features": [
            "Expense tracking",
            "Budgeting and savings goals",
            "Financial insights and recommendations",
            "Bank account integration"
        ],
        "constraints": [
            "Ensure user data privacy",
            "Comply with financial regulations",
            "Optimize for mobile devices"
        ]
    }

    response = client.post("/receive_product_vision", json=product_vision)
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Backlog items created"}

