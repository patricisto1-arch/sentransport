"""Vérification du jeton JWT et des rôles."""
import os

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

ROLES = {"client", "livreur", "admin"}
bearer = HTTPBearer(auto_error=False)


class Utilisateur(BaseModel):
    id: int
    role: str
    token: str  # gardé pour le transmettre au service Colis


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Utilisateur:
    if creds is None:
        raise HTTPException(status_code=401, detail="Authentification requise")
    try:
        payload = jwt.decode(
            creds.credentials,
            os.getenv("JWT_SECRET", ""),
            algorithms=["HS256"],
        )
        user_id = int(payload["sub"])
        role = payload["role"]
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Jeton invalide ou expiré")
    if role not in ROLES:
        raise HTTPException(status_code=401, detail="Rôle inconnu")
    return Utilisateur(id=user_id, role=role, token=creds.credentials)


def require_roles(*roles: str):
    """Dépendance qui n'autorise que les rôles donnés."""

    def verifier(user: Utilisateur = Depends(get_current_user)) -> Utilisateur:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Droits insuffisants")
        return user

    return verifier
