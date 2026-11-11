"""Routes du service Livraisons."""
from fastapi import APIRouter, Depends, HTTPException

import colis_client
import database
from auth import Utilisateur, get_current_user, require_roles
from schemas import (
    AffectationIn,
    HistoriqueOut,
    LivraisonOut,
    Statut,
    StatutIn,
)
from statuts import transition_valide

router = APIRouter()


def _livraison_ou_404(livraison_id: int) -> dict:
    livraison = database.get_livraison(livraison_id)
    if livraison is None:
        raise HTTPException(status_code=404, detail="Livraison introuvable")
    return livraison


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


@router.get("/", response_model=list[LivraisonOut])
def lister(
    livreur_id: int | None = None,
    statut: Statut | None = None,
    user: Utilisateur = Depends(get_current_user),
):
    return database.lister_livraisons(livreur_id, statut)


@router.get("/{livraison_id}", response_model=LivraisonOut)
def detail(livraison_id: int, user: Utilisateur = Depends(get_current_user)):
    return _livraison_ou_404(livraison_id)


@router.get("/{livraison_id}/historique", response_model=list[HistoriqueOut])
def historique(livraison_id: int, user: Utilisateur = Depends(get_current_user)):
    _livraison_ou_404(livraison_id)
    return database.get_historique(livraison_id)


@router.patch("/{livraison_id}/statut", response_model=LivraisonOut)
def changer_statut(
    livraison_id: int,
    donnees: StatutIn,
    user: Utilisateur = Depends(require_roles("livreur", "admin")),
):
    livraison = _livraison_ou_404(livraison_id)
    if user.role == "livreur" and livraison["livreur_id"] != user.id:
        raise HTTPException(status_code=403, detail="Livraison d'un autre livreur")
    if not transition_valide(livraison["statut"], donnees.statut):
        raise HTTPException(
            status_code=400,
            detail=f"Transition impossible : {livraison['statut']} -> {donnees.statut}",
        )
    # Colis d'abord : si Colis échoue, rien n'est écrit dans notre base.
    try:
        colis_client.maj_statut_colis(
            livraison["colis_id"], donnees.statut, user.token
        )
    except colis_client.ColisIndisponible:
        raise HTTPException(status_code=503, detail="Service Colis indisponible")
    except colis_client.ColisRefuse as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    modifiee = database.changer_statut(livraison_id, donnees.statut)
    if modifiee is None:
        raise HTTPException(status_code=404, detail="Livraison introuvable")
    return modifiee