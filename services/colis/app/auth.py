
import os

import jwt
from fastapi import Header, HTTPException, Depends


JWT_SECRET = os.getenv("JWT_SECRET", "")


def verifier_token(authorization: str = Header(default=None)):
    """
    Vérifie le token JWT envoyé dans l'en-tête Authorization.
    """

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Token manquant"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Format du token invalide"
        )

    token = authorization.split(" ", 1)[1]

    if not JWT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Configuration JWT manquante"
        )

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"]
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expiré"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token invalide"
        )


def verifier_role(*roles_autorises):
    """
    Vérifie si l'utilisateur possède un rôle autorisé.
    """

    def controle_role(payload: dict = Depends(verifier_token)):
        role = payload.get("role")

        if role not in roles_autorises:
            raise HTTPException(
                status_code=403,
                detail="Accès interdit : permissions insuffisantes"
            )

        return payload

    return controle_role
