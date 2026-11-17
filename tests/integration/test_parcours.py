"""Tests d'integration SenTransport : parcours colis -> affectation -> statuts.

Ils s'executent contre l'application lancee avec docker compose (passerelle sur http://localhost).
Variables optionnelles : INTEGRATION_BASE_URL, ADMIN_EMAIL, LIVREUR_EMAIL, DEMO_PASSWORD.
"""
import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv("INTEGRATION_BASE_URL", "http://localhost")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin.demo@sentransport.sn")
LIVREUR_EMAIL = os.getenv("LIVREUR_EMAIL", "livreur.demo@sentransport.sn")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Demo1234!")


@pytest.fixture(scope="module")
def api():
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        try:
            client.get("/")
        except httpx.TransportError:
            pytest.skip(f"Application injoignable sur {BASE_URL} (docker compose up ?)")
        yield client


def _login(api, email, mot_de_passe):
    reponse = api.post("/api/utilisateurs/auth/login", json={"email": email, "mot_de_passe": mot_de_passe})
    assert reponse.status_code == 200, reponse.text
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}


@pytest.fixture(scope="module")
def admin(api):
    return _login(api, ADMIN_EMAIL, DEMO_PASSWORD)


@pytest.fixture(scope="module")
def livreur(api):
    headers = _login(api, LIVREUR_EMAIL, DEMO_PASSWORD)
    profil = api.get("/api/utilisateurs/me", headers=headers)
    assert profil.status_code == 200, profil.text
    return {"headers": headers, "id": profil.json()["id"]}


@pytest.fixture(scope="module")
def client_headers(api):
    email = f"client-{uuid.uuid4().hex[:8]}@exemple.sn"
    inscription = api.post(
        "/api/utilisateurs/auth/register",
        json={"nom": "Client Test", "email": email, "mot_de_passe": "motdepasse123"},
    )
    assert inscription.status_code == 201, inscription.text
    return _login(api, email, "motdepasse123")


def _creer_livraison(api, admin, livreur):
    colis = api.post(
        "/api/colis/",
        headers=admin,
        json={
            "destinataire_nom": "Fatou Sow",
            "destinataire_adresse": "Rue 5, Thies",
            "description": "Test integration",
            "poids_kg": 1.5,
        },
    )
    assert colis.status_code == 201, colis.text
    colis_id = colis.json()["id"]
    livraison = api.post("/api/livraisons/", headers=admin, json={"colis_id": colis_id, "livreur_id": livreur["id"]})
    assert livraison.status_code == 201, livraison.text
    return colis_id, livraison.json()["id"]


def _changer_statut(api, headers, livraison_id, statut):
    return api.patch(f"/api/livraisons/{livraison_id}/statut", headers=headers, json={"statut": statut})


def test_parcours_complet(api, admin, livreur):
    colis_id, livraison_id = _creer_livraison(api, admin, livreur)

    assert _changer_statut(api, livreur["headers"], livraison_id, "en_transit").status_code == 200
    colis = api.get(f"/api/colis/{colis_id}", headers=admin)
    assert colis.json()["statut"] == "en_transit"

    assert _changer_statut(api, livreur["headers"], livraison_id, "livre").status_code == 200
    colis = api.get(f"/api/colis/{colis_id}", headers=admin)
    assert colis.json()["statut"] == "livre"

    historique = api.get(f"/api/livraisons/{livraison_id}/historique", headers=admin)
    assert historique.status_code == 200
    statuts = [ligne["statut"] for ligne in historique.json()]
    assert statuts[-2:] == ["en_transit", "livre"]


def test_client_ne_peut_pas_changer_le_statut(api, admin, livreur, client_headers):
    _, livraison_id = _creer_livraison(api, admin, livreur)
    assert _changer_statut(api, client_headers, livraison_id, "en_transit").status_code == 403


def test_colis_deja_affecte(api, admin, livreur):
    colis_id, _ = _creer_livraison(api, admin, livreur)
    doublon = api.post("/api/livraisons/", headers=admin, json={"colis_id": colis_id, "livreur_id": livreur["id"]})
    assert doublon.status_code == 409


def test_transition_interdite(api, admin, livreur):
    _, livraison_id = _creer_livraison(api, admin, livreur)
    assert _changer_statut(api, livreur["headers"], livraison_id, "en_transit").status_code == 200
    assert _changer_statut(api, livreur["headers"], livraison_id, "en_attente").status_code == 400


def test_sans_jeton(api):
    assert api.get("/api/livraisons/").status_code == 401
