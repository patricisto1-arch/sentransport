"""SenTransport identity API, shared data model and JWT helpers."""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
import os
from typing import Generator

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from starlette.responses import JSONResponse


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sentransport.db")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
TOKEN_HOURS = 1
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
password_hasher = PasswordHasher()


class Base(DeclarativeBase):
    pass


class UserRole(str, Enum):
    CLIENT = "client"
    LIVREUR = "livreur"
    ADMIN = "admin"


class DeliveryStatus(str, Enum):
    EN_ATTENTE = "en_attente"
    EN_TRANSIT = "en_transit"
    LIVRE = "livre"
    ECHEC = "echec"


STATUS_CHECK = "statut IN ('en_attente', 'en_transit', 'livre', 'echec')"


class User(Base):
    __tablename__ = "utilisateurs"
    __table_args__ = (
        CheckConstraint("role IN ('client', 'livreur', 'admin')", name="ck_utilisateurs_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.CLIENT.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now(), nullable=False)


class Parcel(Base):
    __tablename__ = "colis"
    __table_args__ = (
        CheckConstraint("poids_kg > 0", name="ck_colis_poids_positif"),
        CheckConstraint(STATUS_CHECK, name="ck_colis_statut"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expediteur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateurs.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    destinataire_nom: Mapped[str] = mapped_column(String(100), nullable=False)
    destinataire_adresse: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    poids_kg: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    statut: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DeliveryStatus.EN_ATTENTE.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now(), nullable=False)


class Delivery(Base):
    __tablename__ = "livraisons"
    __table_args__ = (
        CheckConstraint(STATUS_CHECK, name="ck_livraisons_statut"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    colis_id: Mapped[int] = mapped_column(
        ForeignKey("colis.id", onupdate="CASCADE", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    livreur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateurs.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    statut: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DeliveryStatus.EN_ATTENTE.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DeliveryHistory(Base):
    __tablename__ = "historique_livraisons"
    __table_args__ = (
        CheckConstraint(STATUS_CHECK, name="ck_historique_livraisons_statut"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    livraison_id: Mapped[int] = mapped_column(
        ForeignKey("livraisons.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    statut: Mapped[str] = mapped_column(String(20), nullable=False)
    date_changement: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), nullable=False
    )


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nom: str = Field(min_length=2, max_length=100)
    email: EmailStr
    mot_de_passe: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.CLIENT

    @field_validator("nom")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Le nom doit contenir au moins 2 caractères")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    mot_de_passe: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nom: str
    email: EmailStr
    role: UserRole


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(hashed, password)
    except (InvalidHash, VerificationError, ValueError):
        return False


def create_access_token(user: User) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    payload = {"sub": str(user.id), "role": user.role, "exp": expires_at}
    if not JWT_SECRET:
        raise RuntimeError("La variable JWT_SECRET doit être configurée")
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    if not JWT_SECRET:
        raise RuntimeError("La variable JWT_SECRET doit être configurée")
    claims = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "role", "exp"]},
    )
    if claims["role"] not in {role.value for role in UserRole}:
        raise jwt.InvalidTokenError("Rôle de jeton inconnu")
    return claims


bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton absent, invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = decode_access_token(credentials.credentials)
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton absent, invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return user


def require_roles(*roles: UserRole):
    def check(user: User = Depends(get_current_user)) -> User:
        if user.role not in {role.value for role in roles}:
            raise HTTPException(status_code=403, detail="Droits insuffisants")
        return user

    return check


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SenTransport - Service Utilisateurs", version="1.0.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def invalid_request_handler(_: Request, __: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": "Données invalides"},
    )


@app.get("/health", tags=["sante"])
def health():
    return {"status": "ok", "service": "utilisateurs"}


@app.post("/auth/register", response_model=UserOut, status_code=201, tags=["authentification"])
def register(data: UserCreate, db: Session = Depends(get_db)):
    if data.role != UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Seul le rôle client peut être choisi à l'inscription")
    email = str(data.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Cette adresse e-mail est déjà utilisée")
    user = User(
        nom=data.nom,
        email=email,
        mot_de_passe_hash=hash_password(data.mot_de_passe),
        role=UserRole.CLIENT.value,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cette adresse e-mail est déjà utilisée")
    return user


@app.post("/auth/login", response_model=TokenOut, tags=["authentification"])
def login(data: UserLogin, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(data.mot_de_passe, user.mot_de_passe_hash):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    return TokenOut(access_token=create_access_token(user))


@app.get("/me", response_model=UserOut, tags=["utilisateurs"])
def me(user: User = Depends(get_current_user)):
    return user


@app.get("/livreurs", response_model=list[UserOut], tags=["utilisateurs"])
def list_livreurs(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    return db.scalars(
        select(User).where(User.role == UserRole.LIVREUR.value).order_by(User.nom)
    ).all()
