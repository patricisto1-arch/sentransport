from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import Base, SessionLocal, User, UserRole, app, hash_password, engine


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


def register(client, email="client@example.com", telephone="+221770123456"):
    return client.post("/auth/register", json={
        "nom": "Client Test", "email": email, "telephone": telephone,
        "mot_de_passe": "MotDePasse123!",
    })


def admin_token(client):
    with SessionLocal() as db:
        db.add(User(
            id=uuid4(), nom="Admin Test", email="admin@example.com",
            mot_de_passe_hash=hash_password("MotDePasse123!"), role=UserRole.ADMINISTRATEUR,
        ))
        db.commit()
    response = client.post("/auth/login", json={"email": "admin@example.com", "mot_de_passe": "MotDePasse123!"})
    return response.json()["access_token"]


def test_register_login_and_token(client):
    created = register(client)
    assert created.status_code == 201
    assert created.json()["role"] == "client"
    assert "mot_de_passe_hash" not in created.json()
    login = client.post("/auth/login", json={"email": "client@example.com", "mot_de_passe": "MotDePasse123!"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert login.status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 200
    assert client.post("/auth/verify", headers=headers).json()["valid"] is True
    assert client.get("/internal/validate", headers=headers).json()["role"] == "client"


def test_registration_cleans_values_and_rejects_role_escalation(client):
    response = client.post("/auth/register", json={
        "nom": "  Client Test  ", "email": "client@example.com",
        "telephone": "  +221770123456 ", "mot_de_passe": "MotDePasse123!",
        "role": "administrateur",
    })
    assert response.status_code == 422
    response = client.post("/auth/register", json={
        "nom": "  Client Test  ", "email": "client@example.com",
        "telephone": "  +221770123456 ", "mot_de_passe": "MotDePasse123!",
    })
    assert response.status_code == 201
    assert response.json()["nom"] == "Client Test"
    assert response.json()["telephone"] == "+221770123456"


def test_duplicate_email_and_phone_conflict(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409
    assert register(client, "other@example.com").status_code == 409


def test_bad_credentials_inactive_user_and_invalid_token(client):
    assert client.post("/auth/login", json={"email": "nobody@example.com", "mot_de_passe": "bad"}).status_code == 401
    register(client)
    assert client.post("/auth/login", json={"email": "client@example.com", "mot_de_passe": "wrong-password"}).status_code == 401
    with SessionLocal() as db:
        user = db.query(User).filter_by(email="client@example.com").one()
        user.actif = False
        db.commit()
    assert client.post("/auth/login", json={"email": "client@example.com", "mot_de_passe": "MotDePasse123!"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert client.get("/users").status_code == 401


def test_admin_manages_roles_and_client_is_forbidden(client):
    created = register(client)
    token = admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/users", headers=headers).status_code == 200
    result = client.patch(f"/users/{created.json()['id']}/role", headers=headers, json={"role": "livreur"})
    assert result.status_code == 200
    assert result.json()["role"] == "livreur"
    assert client.patch(f"/users/{uuid4()}/role", headers=headers, json={"role": "client"}).status_code == 404
    user_token = client.post("/auth/login", json={"email": "client@example.com", "mot_de_passe": "MotDePasse123!"}).json()["access_token"]
    assert client.get("/users", headers={"Authorization": f"Bearer {user_token}"}).status_code == 403


def test_password_hash_functions():
    hashed = hash_password("MotDePasse123!")
    from main import verify_password
    assert verify_password("MotDePasse123!", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("wrong", "invalid-hash")
