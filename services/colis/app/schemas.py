
from pydantic import BaseModel, Field


class ColisCreate(BaseModel):
    destinataire_nom: str = Field(
        min_length=2,
        max_length=100
    )

    destinataire_adresse: str = Field(
        min_length=5,
        max_length=255
    )

    description: str | None = None

    poids_kg: float = Field(gt=0, le=9999.99)
