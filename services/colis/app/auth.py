"""Verification locale des JWT partages par les services SenTransport."""
import os

import jwt
from fastapi import Depends, Header, HTTPException

ROLES = {"client", "livreur", "admin"}


def verifier_token(authorization: str | None = Header(default=None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentification requise")

    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token.strip():
        raise HTTPException(status_code=401, detail="Format du token invalide")

    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="Configuration JWT manquante")

    try:
        payload = jwt.decode(
            token.strip(),
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "role", "exp"]},
        )
        # Le contrat transporte l'identifiant en texte dans sub, mais la BDD utilise INTEGER.
        user_id = int(payload["sub"])
        if user_id <= 0 or payload["role"] not in ROLES:
            raise ValueError("Identifiant ou rôle invalide")
        payload["user_id"] = user_id
        return payload
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Jeton invalide ou expiré")


def verifier_role(*roles_autorises: str):
    def controle_role(payload: dict = Depends(verifier_token)) -> dict:
        if payload["role"] not in roles_autorises:
            raise HTTPException(status_code=403, detail="Droits insuffisants")
        return payload
    return controle_role
