"""Service Livraisons - SenTransport."""
import os

from fastapi import FastAPI

from routes import router

app = FastAPI(title="SenTransport - Service Livraisons")

DATABASE_URL = os.getenv("DATABASE_URL", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")


@app.get("/health")
def health():
    """Utilisé par docker-compose et le déploiement pour vérifier l'état du service."""
    return {"status": "ok", "service": "livraisons"}


app.include_router(router)
