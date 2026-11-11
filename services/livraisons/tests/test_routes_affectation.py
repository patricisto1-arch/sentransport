import time

import jwt
import pytest
from fastapi.testclient import TestClient

import colis_client
import database
from main import app

client = TestClient(app)
SECRET = "secret-de-test"
DONNEES = {"colis_id": 12, "livreur_id": 4}
LIVRAISON = {
    "id": 7,
    "colis_id": 12,
    "livreur_id": 4,
    "statut": "en_attente",
    "created_at": "2026-11-12T15:00:00Z",
    "updated_at": "2026-11-12T15:00:00Z",
}


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)


def en_tete(role="admin"):
    payload = {"sub": "1", "role": role, "exp": int(time.time()) + 3600}
    return {"Authorization": "Bearer " + jwt.encode(payload, SECRET, algorithm="HS256")}


def test_affectation_ok(monkeypatch):
    monkeypatch.setattr(colis_client, "colis_existe", lambda cid, tok: True)
    monkeypatch.setattr(database, "creer_livraison", lambda c, l: LIVRAISON)
    r = client.post("/", json=DONNEES, headers=en_tete())
    assert r.status_code == 201
    assert r.json()["id"] == 7
    assert r.json()["statut"] == "en_attente"


def test_affectation_sans_jeton():
    assert client.post("/", json=DONNEES).status_code == 401


def test_affectation_role_refuse():
    assert client.post("/", json=DONNEES, headers=en_tete("client")).status_code == 403


def test_affectation_donnees_invalides():
    r = client.post("/", json={"colis_id": "abc"}, headers=en_tete())
    assert r.status_code == 422


def test_affectation_colis_introuvable(monkeypatch):
    monkeypatch.setattr(colis_client, "colis_existe", lambda cid, tok: False)
    assert client.post("/", json=DONNEES, headers=en_tete()).status_code == 404


def test_affectation_colis_indisponible(monkeypatch):
    def boom(cid, tok):
        raise colis_client.ColisIndisponible()
    monkeypatch.setattr(colis_client, "colis_existe", boom)
    assert client.post("/", json=DONNEES, headers=en_tete()).status_code == 503


def test_affectation_colis_refuse(monkeypatch):
    def refuse(cid, tok):
        raise colis_client.ColisRefuse(403, "Accès interdit")
    monkeypatch.setattr(colis_client, "colis_existe", refuse)
    r = client.post("/", json=DONNEES, headers=en_tete())
    assert r.status_code == 403
    assert r.json()["detail"] == "Accès interdit"


def test_affectation_deja_affecte(monkeypatch):
    monkeypatch.setattr(colis_client, "colis_existe", lambda cid, tok: True)

    def doublon(c, l):
        raise database.DejaAffecte(c)
    monkeypatch.setattr(database, "creer_livraison", doublon)
    assert client.post("/", json=DONNEES, headers=en_tete()).status_code == 409