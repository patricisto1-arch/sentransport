import uuid

import jwt

from conftest import CLIENT_ID


def test_token_absent(client):
    assert client.get("/").status_code == 401


def test_format_bearer_invalide(client):
    assert client.get("/", headers={"Authorization": "Basic abc"}).status_code == 401


def test_token_valide(client, headers):
    assert client.get("/", headers=headers()).status_code == 200


def test_token_sub_uuid_conserve(client, token):
    from app.auth import verifier_token
    from fastapi import HTTPException

    encoded = token(user_id=CLIENT_ID)
    payload = verifier_token(f"Bearer {encoded}")
    assert payload["user_id"] == CLIENT_ID
    assert isinstance(payload["user_id"], uuid.UUID)


def test_role_inconnu_refuse(client, token):
    bad = token(role="administrateur")
    response = client.get("/", headers={"Authorization": f"Bearer {bad}"})
    assert response.status_code == 401


def test_sub_non_uuid_refuse(client, token):
    bad = token(user_id="not-a-uuid")
    response = client.get("/", headers={"Authorization": f"Bearer {bad}"})
    assert response.status_code == 401


def test_token_expire_refuse(client):
    expired = jwt.encode(
        {"sub": str(CLIENT_ID), "role": "client", "exp": 1},
        "senTransport-test-secret-key-32-bytes-minimum",
        algorithm="HS256",
    )
    response = client.get("/", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
