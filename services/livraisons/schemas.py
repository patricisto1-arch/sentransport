"""Modèles d'entrée et de sortie, conformes à docs/contrats-api.md."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Statut = Literal["en_attente", "en_transit", "livre", "echec"]


class AffectationIn(BaseModel):
    colis_id: int
    livreur_id: int


class StatutIn(BaseModel):
    statut: Statut


class LivraisonOut(BaseModel):
    id: int
    colis_id: int
    livreur_id: int
    statut: Statut
    created_at: datetime
    updated_at: datetime


class HistoriqueOut(BaseModel):
    id: int
    livraison_id: int
    statut: Statut
    date_changement: datetime
