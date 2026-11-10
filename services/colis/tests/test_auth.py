
import jwt
import pytest

from fastapi import HTTPException

from app.auth import verifier_token, verifier_role


def test_token_valide(monkeypatch):
    monkeypatch.setattr("app.auth.JWT_SECRET", "secret_test")

    token = jwt.encode(
        {
            "sub": "1",
            "role": "client",
            "exp": 1999999999
        },
        "secret_test",
        algorithm="HS256"
    )

    resultat = verifier_token(f"Bearer {token}")

    assert resultat["sub"] == "1"
    assert resultat["role"] == "client"


def test_token_manquant():
    with pytest.raises(HTTPException) as erreur:
        verifier_token(None)

    assert erreur.value.status_code == 401


def test_mauvais_format():
    with pytest.raises(HTTPException) as erreur:
        verifier_token("Basic abc123")

    assert erreur.value.status_code == 401


def test_secret_manquant(monkeypatch):
    monkeypatch.setattr("app.auth.JWT_SECRET", "")

    with pytest.raises(HTTPException) as erreur:
        verifier_token("Bearer abc123")

    assert erreur.value.status_code == 500


def test_token_invalide(monkeypatch):
    monkeypatch.setattr("app.auth.JWT_SECRET", "secret_test")

    with pytest.raises(HTTPException) as erreur:
        verifier_token("Bearer faux_token")

    assert erreur.value.status_code == 401


def test_token_expire(monkeypatch):
    monkeypatch.setattr("app.auth.JWT_SECRET", "secret_test")

    token = jwt.encode(
        {
            "sub": "1",
            "role": "client",
            "exp": 1000000000
        },
        "secret_test",
        algorithm="HS256"
    )

    with pytest.raises(HTTPException) as erreur:
        verifier_token(f"Bearer {token}")

    assert erreur.value.status_code == 401
    assert erreur.value.detail == "Token expiré"


def test_role_autorise():
    controle = verifier_role("client", "admin")

    resultat = controle({
        "sub": "1",
        "role": "client"
    })

    assert resultat["role"] == "client"


def test_role_interdit():
    controle = verifier_role("client")

    with pytest.raises(HTTPException) as erreur:
        controle({
            "sub": "2",
            "role": "livreur"
        })

    assert erreur.value.status_code == 403
