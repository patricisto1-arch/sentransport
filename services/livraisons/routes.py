"""Routes du service Livraisons."""
from fastapi import APIRouter, Depends, HTTPException

import colis_client
import database
from auth import Utilisateur, require_roles
from schemas import AffectationIn, LivraisonOut

router = APIRouter()


@router.post("/", response_model=LivraisonOut, status_code=201)
def affecter_colis(
    donnees: AffectationIn,
    user: Utilisateur = Depends(require_roles("admin")),
):
    try:
        existe = colis_client.colis_existe(donnees.colis_id, user.token)
    except colis_client.ColisIndisponible:
        raise HTTPException(status_code=503, detail="Service Colis indisponible")
    except colis_client.ColisRefuse as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    if not existe:
        raise HTTPException(status_code=404, detail="Colis introuvable")
    try:
        return database.creer_livraison(donnees.colis_id, donnees.livreur_id)
    except database.DejaAffecte:
        raise HTTPException(status_code=409, detail="Colis déjà affecté")