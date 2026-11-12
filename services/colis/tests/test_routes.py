from decimal import Decimal


def creer(client, headers, colis_payload, role="client", user_id=1):
    return client.post("/", json=colis_payload(), headers=headers(role, user_id))


def test_creer_colis(client, headers, colis_payload):
    response = client.post("/", json=colis_payload(), headers=headers())
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["expediteur_id"] == 1
    assert body["destinataire_nom"] == "Moussa Ndiaye"
    assert body["statut"] == "en_attente"
    assert "created_at" in body
    assert "client_id" not in body


def test_creation_interdite_sans_token(client, colis_payload):
    assert client.post("/", json=colis_payload()).status_code == 401


def test_creation_interdite_au_livreur(client, headers, colis_payload):
    assert client.post("/", json=colis_payload(), headers=headers("livreur", 3)).status_code == 403


def test_creation_autorisee_admin(client, headers, colis_payload):
    assert client.post("/", json=colis_payload(), headers=headers("admin", 4)).status_code == 201


def test_champs_inconnus_refuses(client, headers, colis_payload):
    payload = colis_payload(reference="REF-123")
    assert client.post("/", json=payload, headers=headers()).status_code == 422


def test_poids_positif_obligatoire(client, headers, colis_payload):
    assert client.post("/", json=colis_payload(poids_kg=-1), headers=headers()).status_code == 422
    assert client.post("/", json=colis_payload(poids_kg=0), headers=headers()).status_code == 422


def test_poids_trop_precis_refuse(client, headers, colis_payload):
    assert client.post("/", json=colis_payload(poids_kg=12345.678), headers=headers()).status_code == 422


def test_liste_client_ne_voit_que_ses_colis(client, headers, colis_payload):
    client.post("/", json=colis_payload(), headers=headers("client", 1))
    client.post("/", json=colis_payload(destinataire_nom="Autre"), headers=headers("client", 2))
    response = client.get("/", headers=headers("client", 1))
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["expediteur_id"] == 1


def test_livreur_voit_tous_les_colis(client, headers, colis_payload):
    client.post("/", json=colis_payload(), headers=headers("client", 1))
    client.post("/", json=colis_payload(destinataire_nom="Autre"), headers=headers("client", 2))
    response = client.get("/", headers=headers("livreur", 3))
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_detail_colis(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    response = client.get(f"/{created['id']}", headers=headers())
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_client_ne_peut_pas_voir_colis_autre_client(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers("client", 1)).json()
    response = client.get(f"/{created['id']}", headers=headers("client", 2))
    assert response.status_code == 404


def test_colis_inexistant(client, headers):
    assert client.get("/999", headers=headers()).status_code == 404


def test_modifier_colis_en_attente(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    response = client.put(
        f"/{created['id']}",
        json={"destinataire_nom": "Aminata Diop"},
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["destinataire_nom"] == "Aminata Diop"


def test_client_ne_peut_pas_modifier_colis_autre_client(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers("client", 1)).json()
    response = client.put(
        f"/{created['id']}", json={"destinataire_nom": "Intrus"}, headers=headers("client", 2)
    )
    assert response.status_code == 404


def test_livreur_ne_peut_pas_modifier(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    response = client.put(
        f"/{created['id']}", json={"destinataire_nom": "Test"}, headers=headers("livreur", 3)
    )
    assert response.status_code == 403


def test_modification_vide_refusee(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    response = client.put(f"/{created['id']}", json={}, headers=headers())
    assert response.status_code == 422


def test_modification_description_peut_etre_nulle(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    response = client.put(f"/{created['id']}", json={"description": None}, headers=headers())
    assert response.status_code == 200
    assert response.json()["description"] is None


def test_statut_en_transit_par_livreur(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    response = client.patch(
        f"/{created['id']}/statut", json={"statut": "en_transit"}, headers=headers("livreur", 3)
    )
    assert response.status_code == 200
    assert response.json()["statut"] == "en_transit"


def test_statut_livre_depuis_en_transit(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    client.patch(f"/{created['id']}/statut", json={"statut": "en_transit"}, headers=headers("livreur", 3))
    response = client.patch(
        f"/{created['id']}/statut", json={"statut": "livre"}, headers=headers("admin", 4)
    )
    assert response.status_code == 200
    assert response.json()["statut"] == "livre"


def test_statut_echec_depuis_attente(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    response = client.patch(
        f"/{created['id']}/statut", json={"statut": "echec"}, headers=headers("admin", 4)
    )
    assert response.status_code == 200
    assert response.json()["statut"] == "echec"


def test_transition_directe_vers_livre_refusee(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    response = client.patch(
        f"/{created['id']}/statut", json={"statut": "livre"}, headers=headers("admin", 4)
    )
    assert response.status_code == 409


def test_statut_inconnu_refuse(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    response = client.patch(
        f"/{created['id']}/statut", json={"statut": "annule"}, headers=headers("admin", 4)
    )
    assert response.status_code == 422


def test_client_ne_peut_pas_changer_statut(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    response = client.patch(
        f"/{created['id']}/statut", json={"statut": "en_transit"}, headers=headers()
    )
    assert response.status_code == 403


def test_admin_peut_supprimer(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    response = client.delete(f"/{created['id']}", headers=headers("admin", 4))
    assert response.status_code == 204


def test_client_ne_peut_pas_supprimer(client, headers, colis_payload):
    created = client.post("/", json=colis_payload(), headers=headers()).json()
    response = client.delete(f"/{created['id']}", headers=headers())
    assert response.status_code == 403


def test_suppression_colis_inexistant(client, headers):
    assert client.delete("/999", headers=headers("admin", 4)).status_code == 404
