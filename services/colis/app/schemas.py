"""Schemas HTTP conformes au contrat API SenTransport, section Colis."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


StatutColis = str
StatutValide = Annotated[str, Field(pattern=r"^(en_attente|en_transit|livre|echec)$")]
Poids = Annotated[Decimal, Field(gt=0, max_digits=6, decimal_places=2)]


class ColisCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destinataire_nom: str = Field(min_length=1, max_length=100)
    destinataire_adresse: str = Field(min_length=1, max_length=255)
    description: str | None = None
    poids_kg: Poids


class ColisUpdate(BaseModel):
    """Champs modifiables par PUT; l'expediteur et le statut ne sont pas modifiables ici."""
    model_config = ConfigDict(extra="forbid")

    destinataire_nom: str | None = Field(default=None, min_length=1, max_length=100)
    destinataire_adresse: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    poids_kg: Poids | None = None

    @model_validator(mode="after")
    def verifier_champs(self):
        if not self.model_fields_set:
            raise ValueError("Au moins un champ doit être modifié")
        for champ in ("destinataire_nom", "destinataire_adresse", "poids_kg"):
            if champ in self.model_fields_set and getattr(self, champ) is None:
                raise ValueError(f"{champ} ne peut pas être nul")
        return self


class StatutUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statut: StatutValide


class ColisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    expediteur_id: int
    destinataire_nom: str
    destinataire_adresse: str
    description: str | None
    poids_kg: Decimal
    statut: str
    created_at: datetime
