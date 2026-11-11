import time

import jwt
import pytest
from fastapi.testclient import TestClient

import colis_client
import database
from main import app

client = TestClient(app)
SECRET = "secret-de-test"

LIV = {
    "id": 7,
    "colis_id": 12,
    "livreur_id": 4,
    "statut": "en_attente",
    "created_at": "2026-11-12T15:00:00Z",
    "updated_at": "2026-11-12T15:00:00Z",
}
HIST = [
    {"id": 1, "livraison_id": 7, "statut": "en_attente",
     "date_changement": "2026-11-12T15:00:00Z"},
    {"id": 2, "livraison_id": 7, "statut": "en_transit",
     "date_changement": "2026-11-12T16:00:00Z"},
]


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)


def en_tete(role="admin", sub="1"):
    payload = {"sub": sub, "role": role, "exp": int(time.time()) + 3600}
    return {"Authorization": "Bearer " + jwt.encode(payload, SECRET, algorithm="HS256")}


def livraison_existante(monkeypatch, **changes):
    monkeypatch.setattr(database, "get_livraison", lambda i: {**LIV, **changes})


# --- GET / ---

def test_lister_ok(monkeypatch):
    monkeypatch.setattr(database, "lister_livraisons", lambda liv, s: [LIV])
    r = client.get("/", headers=en_tete("client"))
    assert r.status_code == 200
    assert r.json()[0]["id"] == 7


def test_lister_filtres(monkeypatch):
    recu = {}

    def faux(liv, s):
        recu["args"] = (liv, s)
        return []

    monkeypatch.setattr(database, "lister_livraisons", faux)
    r = client.get("/?livreur_id=4&statut=livre", headers=en_tete())
    assert r.status_code == 200
    assert recu["args"] == (4, "livre")


def test_lister_statut_invalide():
    assert client.get("/?statut=nimporte", headers=en_tete()).status_code == 422


def test_lister_sans_jeton():
    assert client.get("/").status_code == 401


# --- GET /{id} ---

def test_detail_ok(monkeypatch):
    livraison_existante(monkeypatch)
    r = client.get("/7", headers=en_tete("livreur"))
    assert r.status_code == 200
    assert r.json()["colis_id"] == 12


def test_detail_introuvable(monkeypatch):
    monkeypatch.setattr(database, "get_livraison", lambda i: None)
    assert client.get("/99", headers=en_tete()).status_code == 404


# --- GET /{id}/historique ---

def test_historique_ok(monkeypatch):
    livraison_existante(monkeypatch)
    monkeypatch.setattr(database, "get_historique", lambda i: HIST)
    r = client.get("/7/historique", headers=en_tete())
    assert r.status_code == 200
    assert [h["statut"] for h in r.json()] == ["en_attente", "en_transit"]


def test_historique_livraison_introuvable(monkeypatch):
    monkeypatch.setattr(database, "get_livraison", lambda i: None)
    assert client.get("/99/historique", headers=en_tete()).status_code == 404


# --- PATCH /{id}/statut ---

def brancher_maj(monkeypatch, appels):
    monkeypatch.setattr(
        colis_client, "maj_statut_colis",
        lambda cid, st, tok: appels.append(("colis", cid, st)),
    )

    def maj_base(i, st):
        appels.append(("base", i, st))
        return {**LIV, "statut": st}

    monkeypatch.setattr(database, "changer_statut", maj_base)


def test_statut_livreur_concerne(monkeypatch):
    livraison_existante(monkeypatch)
    appels = []
    brancher_maj(monkeypatch, appels)
    r = client.patch("/7/statut", json={"statut": "en_transit"},
                     headers=en_tete("livreur", "4"))
    assert r.status_code == 200
    assert r.json()["statut"] == "en_transit"
    # Colis d'abord, base ensuite
    assert appels == [("colis", 12, "en_transit"), ("base", 7, "en_transit")]


def test_statut_admin(monkeypatch):
    livraison_existante(monkeypatch)
    brancher_maj(monkeypatch, [])
    r = client.patch("/7/statut", json={"statut": "echec"}, headers=en_tete("admin"))
    assert r.status_code == 200


def test_statut_autre_livreur(monkeypatch):
    livraison_existante(monkeypatch)
    r = client.patch("/7/statut", json={"statut": "en_transit"},
                     headers=en_tete("livreur", "5"))
    assert r.status_code == 403


def test_statut_client_refuse():
    r = client.patch("/7/statut", json={"statut": "en_transit"},
                     headers=en_tete("client"))
    assert r.status_code == 403


def test_statut_livraison_introuvable(monkeypatch):
    monkeypatch.setattr(database, "get_livraison", lambda i: None)
    r = client.patch("/99/statut", json={"statut": "en_transit"}, headers=en_tete())
    assert r.status_code == 404


def test_statut_transition_invalide(monkeypatch):
    livraison_existante(monkeypatch, statut="livre")
    appels = []
    brancher_maj(monkeypatch, appels)
    r = client.patch("/7/statut", json={"statut": "en_attente"}, headers=en_tete())
    assert r.status_code == 400
    assert appels == []  # rien n'a été modifié


def test_statut_valeur_invalide():
    r = client.patch("/7/statut", json={"statut": "perdu"}, headers=en_tete())
    assert r.status_code == 422


def test_statut_colis_indisponible(monkeypatch):
    livraison_existante(monkeypatch)
    appels = []

    def boom(cid, st, tok):
        raise colis_client.ColisIndisponible()

    monkeypatch.setattr(colis_client, "maj_statut_colis", boom)
    monkeypatch.setattr(database, "changer_statut",
                        lambda i, s: appels.append("base"))
    r = client.patch("/7/statut", json={"statut": "en_transit"}, headers=en_tete())
    assert r.status_code == 503
    assert appels == []  # la base n'a pas été touchée


def test_statut_colis_refuse(monkeypatch):
    livraison_existante(monkeypatch)

    def refuse(cid, st, tok):
        raise colis_client.ColisRefuse(403, "Accès interdit")

    monkeypatch.setattr(colis_client, "maj_statut_colis", refuse)
    r = client.patch("/7/statut", json={"statut": "en_transit"}, headers=en_tete())
    assert r.status_code == 403
    assert r.json()["detail"] == "Accès interdit"


def test_statut_livraison_disparue(monkeypatch):
    livraison_existante(monkeypatch)
    monkeypatch.setattr(colis_client, "maj_statut_colis", lambda c, s, t: None)
    monkeypatch.setattr(database, "changer_statut", lambda i, s: None)
    r = client.patch("/7/statut", json={"statut": "en_transit"}, headers=en_tete())
    assert r.status_code == 404
