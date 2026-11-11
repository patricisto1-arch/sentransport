import time

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from auth import Utilisateur, get_current_user, require_roles

SECRET = "secret-de-test"

app = FastAPI()


@app.get("/moi")
def moi(user: Utilisateur = Depends(get_current_user)):
    return {"id": user.id, "role": user.role}


@app.get("/admin")
def admin(user: Utilisateur = Depends(require_roles("admin"))):
    return {"ok": True}


client = TestClient(app)


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)


def jeton(role="admin", sub="4", exp=None, secret=SECRET):
    payload = {"sub": sub, "role": role, "exp": exp or int(time.time()) + 3600}
    return jwt.encode(payload, secret, algorithm="HS256")


def en_tete(token):
    return {"Authorization": f"Bearer {token}"}


def test_sans_jeton():
    assert client.get("/moi").status_code == 401


def test_jeton_valide():
    r = client.get("/moi", headers=en_tete(jeton("livreur", "4")))
    assert r.status_code == 200
    assert r.json() == {"id": 4, "role": "livreur"}


def test_jeton_expire():
    r = client.get("/moi", headers=en_tete(jeton(exp=int(time.time()) - 10)))
    assert r.status_code == 401


def test_mauvais_secret():
    assert client.get("/moi", headers=en_tete(jeton(secret="autre"))).status_code == 401


def test_role_inconnu():
    assert client.get("/moi", headers=en_tete(jeton(role="pirate"))).status_code == 401


def test_acces_admin():
    assert client.get("/admin", headers=en_tete(jeton("admin"))).status_code == 200


def test_acces_refuse():
    assert client.get("/admin", headers=en_tete(jeton("client"))).status_code == 403
