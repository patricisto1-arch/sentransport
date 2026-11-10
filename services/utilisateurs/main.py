"""Service Utilisateurs - SenTransport.

Squelette : ajoutez vos routes ici en suivant docs/contrats-api.md.
"""
import os

from fastapi import FastAPI

app = FastAPI(title="SenTransport - Service Utilisateurs")

DATABASE_URL = os.getenv("DATABASE_URL", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")


@app.get("/health")
def health():
    """Utilisé par docker-compose et le déploiement pour vérifier l'état du service."""
    return {"status": "ok", "service": "utilisateurs"}
