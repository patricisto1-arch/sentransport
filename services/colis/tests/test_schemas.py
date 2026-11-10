
import pytest
from pydantic import ValidationError
from app.schemas import ColisCreate


def test_creation_colis_valide():
    colis = ColisCreate(
        destinataire_nom="Moussa Ndiaye",
        destinataire_adresse="Rue 10, Pikine",
        description="Carton de livres",
        poids_kg=2.5
    )

    assert colis.destinataire_nom == "Moussa Ndiaye"
    assert colis.poids_kg == 2.5


def test_poids_negatif_refuse():
    with pytest.raises(ValidationError):
        ColisCreate(
            destinataire_nom="Moussa Ndiaye",
            destinataire_adresse="Rue 10, Pikine",
            poids_kg=-2
        )


def test_nom_trop_court_refuse():
    with pytest.raises(ValidationError):
        ColisCreate(
            destinataire_nom="A",
            destinataire_adresse="Rue 10, Pikine",
            poids_kg=2.5
        )
