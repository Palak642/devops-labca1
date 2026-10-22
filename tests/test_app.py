import pytest

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_greeting_trims_surrounding_whitespace(client):
    response = client.get("/api/greet/Ada%20")

    assert response.status_code == 200
    assert response.json == {"message": "Hello, Ada!"}


@pytest.mark.parametrize(
    "name",
    [
        "%20",
        "x" * 81,
        "bad%0Aname",
    ],
)
def test_greeting_rejects_invalid_names(client, name):
    response = client.get(f"/api/greet/{name}")

    assert response.status_code == 400


def test_adds_numbers(client):
    response = client.post("/api/add", json={"left": 2.5, "right": 4})

    assert response.status_code == 200
    assert response.json == {"result": 6.5}


@pytest.mark.parametrize(
    "payload",
    [
        {"left": True, "right": 1},
        {"left": "1", "right": 1},
        {"left": float("inf"), "right": 1},
        {"left": float("-inf"), "right": 1},
        ["not", "an", "object"],
    ],
)
def test_add_rejects_invalid_payloads(client, payload):
    response = client.post("/api/add", json=payload)

    assert response.status_code == 400


def test_add_accepts_large_finite_integers(client):
    response = client.post("/api/add", json={"left": 10**400, "right": 1})

    assert response.status_code == 200
    assert response.json["result"] == 10**400 + 1


def test_add_rejects_non_json_body(client):
    response = client.post("/api/add", data="not json", content_type="text/plain")

    assert response.status_code == 400
