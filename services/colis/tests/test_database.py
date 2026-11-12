from app.models import Colis


def test_modele_colis_utilise_champs_du_contrat():
    assert set(Colis.__table__.columns.keys()) == {
        "id", "expediteur_id", "destinataire_nom", "destinataire_adresse",
        "description", "poids_kg", "statut", "created_at"
    }
    assert str(Colis.__table__.c.id.type) == "INTEGER"
