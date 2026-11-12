"""Application FastAPI SenTransport - service Colis."""
from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine
from app.routes import router

app = FastAPI(title="SenTransport - Service Colis", version="2.0.0")


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Base de données indisponible") from exc
    return {"status": "ok", "service": "colis"}


app.include_router(router)
