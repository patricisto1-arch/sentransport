import uuid

from sqlalchemy import Uuid

from app.models import Colis, UtilisateurRef


def test_modele_colis_utilise_champs_du_contrat():
    columns = Colis.__table__.columns
    assert set(columns.keys()) == {
        "id", "client_id", "destinataire_nom", "destinataire_adresse",
        "description", "poids_kg", "statut", "created_at"
    }
    assert isinstance(columns["id"].type, Uuid)
    assert isinstance(columns["client_id"].type, Uuid)
    assert Colis.expediteur_id.property.columns[0].name == "client_id"
    assert isinstance(UtilisateurRef.__table__.c.id.type, Uuid)


def test_identifiants_uuid():
    assert Colis.id.type.as_uuid is True
    assert Colis.expediteur_id.property.columns[0].type.as_uuid is True
