import uuid

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


def test_colis_out_accepte_identifiants_uuid():
    from app.schemas import ColisOut
    from datetime import datetime
    from decimal import Decimal

    client_id = uuid.UUID("11111111-1111-4111-8111-111111111111")
    colis_id = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    data = ColisOut(
        id=colis_id,
        expediteur_id=client_id,
        destinataire_nom="Moussa",
        destinataire_adresse="Pikine",
        description=None,
        poids_kg=Decimal("2.50"),
        statut="en_attente",
        created_at=datetime(2026, 1, 1),
    )
    assert data.id == colis_id
    assert data.expediteur_id == client_id
