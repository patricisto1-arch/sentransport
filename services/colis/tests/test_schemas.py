import pytest
from pydantic import ValidationError
from app.schemas import ColisCreate, ColisUpdate, StatutUpdate


def test_payload_creation_conforme_contrat():
    data = ColisCreate(
        destinataire_nom="Moussa Ndiaye",
        destinataire_adresse="Rue 10, Pikine",
        description="Carton de livres",
        poids_kg=2.5,
    )
    assert data.poids_kg > 0


def test_reference_ancien_format_refusee():
    with pytest.raises(ValidationError):
        ColisCreate(reference="REF", description="x", poids_kg=1, adresse_depart="A", adresse_arrivee="B")


def test_poids_zero_refuse():
    with pytest.raises(ValidationError):
        ColisCreate(destinataire_nom="A", destinataire_adresse="B", poids_kg=0)


def test_statut_valide():
    assert StatutUpdate(statut="en_transit").statut == "en_transit"


def test_statut_invalide():
    with pytest.raises(ValidationError):
        StatutUpdate(statut="annule")


def test_update_vide_refuse():
    with pytest.raises(ValidationError):
        ColisUpdate()
