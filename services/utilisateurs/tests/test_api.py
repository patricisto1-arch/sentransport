from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from main import (
    Base,
    JWT_ALGORITHM,
    JWT_SECRET,
    SessionLocal,
    User,
    UserRole,
    app,
    decode_access_token,
    engine,
    hash_password,
    verify_password,
)


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


def register(client, email="client@example.com", name="Client Test", role="client"):
    return client.post(
        "/auth/register",
        json={
            "nom": name,
            "email": email,
            "mot_de_passe": "MotDePasse123!",
            "role": role,
        },
    )


def create_admin():
    with SessionLocal() as db:
        admin = User(
            nom="Admin Test",
            email="admin@example.com",
            mot_de_passe_hash=hash_password("MotDePasse123!"),
            role=UserRole.ADMIN.value,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin.id


def login(client, email="client@example.com"):
    return client.post(
        "/auth/login",
        json={"email": email, "mot_de_passe": "MotDePasse123!"},
    )


def test_health_matches_contract(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "utilisateurs"}


def test_register_login_and_me(client):
    response = register(client, name="  Awa Diop  ")
    assert response.status_code == 201
    profile_data = response.json()
    assert profile_data["id"] > 0
    assert profile_data["nom"] == "Awa Diop"
    assert profile_data["email"] == "client@example.com"
    assert profile_data["role"] == "client"
    assert "mot_de_passe_hash" not in profile_data

    authenticated = login(client)
    assert authenticated.status_code == 200
    assert set(authenticated.json()) == {"access_token", "token_type"}
    assert authenticated.json()["token_type"] == "bearer"
    claims = decode_access_token(authenticated.json()["access_token"])
    assert claims["sub"] == str(response.json()["id"])
    assert claims["role"] == "client"
    assert "exp" in claims
    profile = client.get(
        "/me",
        headers={"Authorization": f"Bearer {authenticated.json()['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["nom"] == "Awa Diop"


def test_register_rejects_duplicate_email_and_privileged_role(client):
    assert register(client).status_code == 201
    duplicate = register(client)
    assert duplicate.status_code == 409
    privileged = register(client, "admin@example.com", role="admin")
    assert privileged.status_code == 403


def test_register_rejects_blank_name(client):
    response = register(client, name="   ")
    assert response.status_code == 400


def test_login_rejects_unknown_user_and_wrong_password(client):
    assert login(client, "missing@example.com").status_code == 401
    register(client)
    response = client.post(
        "/auth/login",
        json={"email": "client@example.com", "mot_de_passe": "incorrect-password"},
    )
    assert response.status_code == 401


def test_livreurs_is_admin_only_and_returns_only_couriers(client):
    create_admin()
    with SessionLocal() as db:
        db.add(
            User(
                nom="Livreur Test",
                email="livreur@example.com",
                mot_de_passe_hash=hash_password("MotDePasse123!"),
                role=UserRole.LIVREUR.value,
            )
        )
        db.commit()
    admin_token = login(client, "admin@example.com").json()["access_token"]
    response = client.get(
        "/livreurs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert [user["email"] for user in response.json()] == ["livreur@example.com"]

    assert register(client).status_code == 201
    client_token = login(client).json()["access_token"]
    forbidden = client.get(
        "/livreurs",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert forbidden.status_code == 403


def test_missing_invalid_expired_and_tampered_tokens_are_rejected(client):
    assert client.get("/me").status_code == 401
    invalid = client.get("/me", headers={"Authorization": "Bearer invalid-token"})
    assert invalid.status_code == 401

    expired_token = jwt.encode(
        {
            "sub": "1",
            "role": "client",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    assert client.get("/me", headers={"Authorization": f"Bearer {expired_token}"}).status_code == 401

    tampered = jwt.encode(
        {
            "sub": "1",
            "role": "client",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "wrong-secret-for-this-test",
        algorithm=JWT_ALGORITHM,
    )
    assert client.get("/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_password_hashing_and_invalid_hash():
    hashed = hash_password("MotDePasse123!")
    assert verify_password("MotDePasse123!", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("wrong", "invalid-hash")
