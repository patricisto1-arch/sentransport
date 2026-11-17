"""Routes du service Colis conformes a la section 5 du contrat API."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import verifier_role
from app.database import get_db
from app.models import Colis
from app.schemas import ColisCreate, ColisOut, ColisUpdate, StatutUpdate

router = APIRouter()

# Transitions correspondant au cycle de vie documente dans le contrat.
TRANSITIONS = {
    "en_attente": {"en_transit", "echec"},
    "en_transit": {"livre", "echec"},
    "livre": set(),
    "echec": set(),
}


def _get_colis(colis_id: uuid.UUID, user: dict, db: Session) -> Colis:
    colis = db.get(Colis, colis_id)
    if colis is None:
        raise HTTPException(status_code=404, detail="Colis introuvable")
    if user["role"] == "client" and colis.expediteur_id != user["user_id"]:
        # Le contrat indique qu'un client ne voit que ses propres colis.
        raise HTTPException(status_code=404, detail="Colis introuvable")
    return colis


@router.post("/", response_model=ColisOut, status_code=status.HTTP_201_CREATED)
def creer_colis(
    data: ColisCreate,
    user: dict = Depends(verifier_role("client", "admin")),
    db: Session = Depends(get_db),
):
    colis = Colis(expediteur_id=user["user_id"], **data.model_dump())
    db.add(colis)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Expéditeur inexistant ou données en conflit") from exc
    db.refresh(colis)
    return colis


@router.get("/", response_model=list[ColisOut])
def lister_colis(
    user: dict = Depends(verifier_role("client", "livreur", "admin")),
    db: Session = Depends(get_db),
):
    query = select(Colis).order_by(Colis.created_at.desc(), Colis.id.desc())
    if user["role"] == "client":
        query = query.where(Colis.expediteur_id == user["user_id"])
    return list(db.scalars(query).all())


@router.get("/{colis_id}", response_model=ColisOut)
def detail_colis(
    colis_id: uuid.UUID,
    user: dict = Depends(verifier_role("client", "livreur", "admin")),
    db: Session = Depends(get_db),
):
    return _get_colis(colis_id, user, db)


@router.put("/{colis_id}", response_model=ColisOut)
def modifier_colis(
    colis_id: uuid.UUID,
    data: ColisUpdate,
    user: dict = Depends(verifier_role("client", "admin")),
    db: Session = Depends(get_db),
):
    colis = _get_colis(colis_id, user, db)
    if colis.statut != "en_attente":
        raise HTTPException(status_code=409, detail="Seul un colis en attente peut être modifié")
    for champ, valeur in data.model_dump(exclude_unset=True).items():
        setattr(colis, champ, valeur)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Modification impossible") from exc
    db.refresh(colis)
    return colis


@router.delete("/{colis_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_colis(
    colis_id: uuid.UUID,
    user: dict = Depends(verifier_role("admin")),
    db: Session = Depends(get_db),
):
    colis = db.get(Colis, colis_id)
    if colis is None:
        raise HTTPException(status_code=404, detail="Colis introuvable")
    db.delete(colis)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ce colis est associé à une livraison") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{colis_id}/statut", response_model=ColisOut)
def modifier_statut(
    colis_id: uuid.UUID,
    data: StatutUpdate,
    user: dict = Depends(verifier_role("livreur", "admin")),
    db: Session = Depends(get_db),
):
    colis = db.get(Colis, colis_id)
    if colis is None:
        raise HTTPException(status_code=404, detail="Colis introuvable")
    if data.statut not in TRANSITIONS[colis.statut]:
        raise HTTPException(
            status_code=409,
            detail=f"Transition impossible : {colis.statut} -> {data.statut}",
        )
    colis.statut = data.statut
    db.commit()
    db.refresh(colis)
    return colis
