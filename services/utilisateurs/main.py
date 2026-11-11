"""SenTransport user identity service: registration, authentication and roles."""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
import os
from typing import Generator
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    String,
    Text,
    Uuid,
    create_engine,
    func,
    select,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sentransport.db")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
JWT_SECRET = os.getenv("JWT_SECRET", "local-development-secret-change-in-production")
JWT_ALGORITHM = "HS256"
TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
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
    ADMINISTRATEUR = "administrateur"


class ParcelStatus(str, Enum):
    EN_ATTENTE = "en_attente"
    PRISE_EN_CHARGE = "prise_en_charge"
    EN_TRANSIT = "en_transit"
    LIVRE = "livre"
    ANNULE = "annule"


class DeliveryStatus(str, Enum):
    AFFECTEE = "affectee"
    EN_COURS = "en_cours"
    TERMINEE = "terminee"
    ECHEC = "echec"


def enum_values(enum_cls):
    return [item.value for item in enum_cls]


class User(Base):
    __tablename__ = "utilisateurs"
    __table_args__ = (CheckConstraint("length(nom) >= 2", name="ck_utilisateur_nom_min"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    nom: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    telephone: Mapped[str | None] = mapped_column(String(30), unique=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", values_callable=enum_values),
        nullable=False,
        default=UserRole.CLIENT,
    )
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Parcel(Base):
    __tablename__ = "colis"
    __table_args__ = (CheckConstraint("poids_kg > 0", name="ck_colis_poids_positif"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    client_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("utilisateurs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    poids_kg: Mapped[float] = mapped_column(Float, nullable=False)
    adresse_depart: Mapped[str] = mapped_column(String(255), nullable=False)
    adresse_arrivee: Mapped[str] = mapped_column(String(255), nullable=False)
    statut: Mapped[ParcelStatus] = mapped_column(
        SAEnum(ParcelStatus, name="parcel_status", values_callable=enum_values),
        nullable=False,
        default=ParcelStatus.EN_ATTENTE,
    )
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Delivery(Base):
    __tablename__ = "livraisons"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    colis_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("colis.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    livreur_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("utilisateurs.id", ondelete="SET NULL"),
        index=True,
    )
    statut: Mapped[DeliveryStatus] = mapped_column(
        SAEnum(DeliveryStatus, name="delivery_status", values_callable=enum_values),
        nullable=False,
        default=DeliveryStatus.AFFECTEE,
    )
    date_affectation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_livraison: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    commentaire: Mapped[str | None] = mapped_column(Text)


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nom: str = Field(min_length=2, max_length=120)
    email: EmailStr
    telephone: str | None = Field(default=None, max_length=30)
    mot_de_passe: str = Field(min_length=8, max_length=128)

    @field_validator("nom")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Le nom doit contenir au moins 2 caractères")
        return value

    @field_validator("telephone")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        value = value.strip() if value else None
        return value or None


class UserLogin(BaseModel):
    email: EmailStr
    mot_de_passe: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    nom: str
    email: EmailStr
    telephone: str | None
    role: UserRole
    actif: bool
    cree_le: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    utilisateur: UserOut


class RoleUpdate(BaseModel):
    role: UserRole


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
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id), "role": user.role.value, "email": user.email,
        "iat": now, "exp": now + timedelta(minutes=TOKEN_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"require": ["sub", "exp"]})


bearer = HTTPBearer(auto_error=False)
unauthorized = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Jeton absent, invalide ou expiré",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise unauthorized
    try:
        claims = decode_access_token(credentials.credentials)
        user = db.get(User, UUID(claims["sub"]))
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        raise unauthorized
    if user is None or not user.actif:
        raise unauthorized
    return user


def require_roles(*roles: str):
    def check(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in roles:
            raise HTTPException(status_code=403, detail="Droits insuffisants")
        return user
    return check


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SenTransport - Service Utilisateurs", version="1.0.0", lifespan=lifespan)


@app.get("/health", tags=["sante"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": "utilisateurs"}


@app.post("/auth/register", response_model=UserOut, status_code=201, tags=["authentification"])
def register(data: UserCreate, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Cette adresse e-mail est déjà utilisée")
    user = User(
        id=uuid4(), nom=data.nom, email=email, telephone=data.telephone,
        mot_de_passe_hash=hash_password(data.mot_de_passe), role=UserRole.CLIENT,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="E-mail ou téléphone déjà utilisé")
    return user


@app.post("/auth/login", response_model=TokenOut, tags=["authentification"])
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if user is None or not user.actif or not verify_password(data.mot_de_passe, user.mot_de_passe_hash):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    return TokenOut(access_token=create_access_token(user), expires_in=TOKEN_MINUTES * 60, utilisateur=user)


@app.get("/auth/me", response_model=UserOut, tags=["authentification"])
def me(user: User = Depends(get_current_user)):
    return user


@app.post("/auth/verify", tags=["authentification"])
def verify_token(user: User = Depends(get_current_user)):
    return {"valid": True, "user_id": str(user.id), "role": user.role.value, "email": user.email}


@app.get("/users", response_model=list[UserOut], tags=["utilisateurs"])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMINISTRATEUR.value))):
    return db.scalars(select(User).order_by(User.cree_le.desc())).all()


@app.patch("/users/{user_id}/role", response_model=UserOut, tags=["utilisateurs"])
def update_role(
    user_id: UUID,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRATEUR.value)),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user.role = data.role
    db.commit()
    db.refresh(user)
    return user


@app.get("/internal/validate", tags=["inter-services"])
def validate_for_services(user: User = Depends(get_current_user)):
    return {"id": str(user.id), "role": user.role.value, "active": user.actif}
