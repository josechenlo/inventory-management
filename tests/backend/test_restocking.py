"""
Tests for restocking API endpoints.
"""
import pytest


class TestRestockingEndpoints:
    """Test suite for restocking-related endpoints."""

    def test_get_recommendations_zero_budget(self, client):
        """Test that a zero budget returns no recommended items."""
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total_cost"] == 0

    def test_get_recommendations_shape(self, client):
        """Test the structure of a recommendations response."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        assert response.status_code == 200

        data = response.json()
        assert "budget" in data
        assert "total_cost" in data
        assert "remaining_budget" in data
        assert "items" in data
        assert isinstance(data["items"], list)

        for item in data["items"]:
            assert "sku" in item
            assert "item_name" in item
            assert "recommended_quantity" in item
            assert "unit_cost" in item
            assert "line_cost" in item
            assert "priority_score" in item

    def test_recommendations_respect_budget(self, client):
        """Test that total recommended cost never exceeds the given budget."""
        for budget in [100, 1000, 10000]:
            response = client.get(f"/api/restocking/recommendations?budget={budget}")
            assert response.status_code == 200

            data = response.json()
            assert data["total_cost"] <= budget

    def test_recommendations_sorted_by_priority(self, client):
        """Test that recommended items are sorted by descending priority score."""
        response = client.get("/api/restocking/recommendations?budget=20000")
        assert response.status_code == 200

        data = response.json()
        scores = [item["priority_score"] for item in data["items"]]
        assert scores == sorted(scores, reverse=True)

    def test_recommendations_exclude_healthy_declining_items(self, client):
        """Test that healthy-stock, declining-demand items are never recommended."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        assert response.status_code == 200

        data = response.json()
        skus = [item["sku"] for item in data["items"]]
        assert "DRV-405" not in skus

    def test_create_restock_order_success(self, client):
        """Test submitting a valid multi-item restock order."""
        payload = {
            "budget": 1000,
            "items": [
                {
                    "sku": "TMP-201",
                    "item_name": "Temperature Sensor Module",
                    "quantity": 5,
                    "unit_cost": 89.5,
                    "line_cost": 447.5
                }
            ]
        }
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["order_number"].startswith("RSK-")
        assert data["total_cost"] == 447.5
        assert data["status"] == "Processing"
        assert 7 <= data["lead_time_days"] <= 14

    def test_create_restock_order_empty_items_rejected(self, client):
        """Test that submitting a restock order with no items is rejected."""
        payload = {"budget": 500, "items": []}
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    def test_get_restock_orders_after_create(self, client):
        """Test that a newly created restock order appears in the list."""
        payload = {
            "budget": 200,
            "items": [
                {
                    "sku": "PCB-003",
                    "item_name": "Multi Layer PCB Assembly",
                    "quantity": 2,
                    "unit_cost": 34.5,
                    "line_cost": 69.0
                }
            ]
        }
        create_response = client.post("/api/restock-orders", json=payload)
        assert create_response.status_code == 201
        created_id = create_response.json()["id"]

        list_response = client.get("/api/restock-orders")
        assert list_response.status_code == 200

        orders = list_response.json()
        assert any(order["id"] == created_id for order in orders)
