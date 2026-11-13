import os
import uuid

# La configuration SQLite est reservee aux tests locaux.
os.environ.setdefault("DATABASE_URL", "sqlite:///./colis_test.db")
os.environ.setdefault("JWT_SECRET", "secret-test")

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import get_db  # noqa: E402
from app.models import Base, UtilisateurRef  # noqa: E402
from main import app  # noqa: E402

TEST_SECRET = "senTransport-test-secret-key-32-bytes-minimum"
CLIENT_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
OTHER_CLIENT_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
COURIER_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
ADMIN_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")


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
        session.add_all(
            UtilisateurRef(id=user_id)
            for user_id in (CLIENT_ID, OTHER_CLIENT_ID, COURIER_ID, ADMIN_ID)
        )
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
