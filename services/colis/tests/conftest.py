import os

# La configuration SQLite est reservee aux tests locaux.
os.environ.setdefault("DATABASE_URL", "sqlite:///./colis_test.db")
os.environ.setdefault("JWT_SECRET", "secret-test")

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth
from app.database import get_db
from app.models import Base, UtilisateurRef
from main import app

TEST_SECRET = "senTransport-test-secret-key-32-bytes-minimum"
CLIENT_ID = 1
OTHER_CLIENT_ID = 2
COURIER_ID = 3
ADMIN_ID = 4


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add_all(UtilisateurRef(id=i) for i in (CLIENT_ID, OTHER_CLIENT_ID, COURIER_ID, ADMIN_ID))
        session.commit()
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_engine, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def token():
    def make(role="client", user_id=CLIENT_ID, **overrides):
        claims = {"sub": str(user_id), "role": role, "exp": 1999999999}
        claims.update(overrides)
        return jwt.encode(claims, TEST_SECRET, algorithm="HS256")
    return make


@pytest.fixture
def headers(token):
    return lambda role="client", user_id=CLIENT_ID: {
        "Authorization": f"Bearer {token(role, user_id)}"
    }


@pytest.fixture
def colis_payload():
    def make(**overrides):
        payload = {
            "destinataire_nom": "Moussa Ndiaye",
            "destinataire_adresse": "Rue 10, Pikine",
            "description": "Carton de livres",
            "poids_kg": 2.5,
        }
        payload.update(overrides)
        return payload
    return make
