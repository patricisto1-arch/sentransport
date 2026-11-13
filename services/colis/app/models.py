"""Modeles SQLAlchemy du service Colis, conformes a database/init.sql."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UtilisateurRef(Base):
    """Reference minimale a utilisateurs, table geree par le service Utilisateurs."""
    __tablename__ = "utilisateurs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)


class Colis(Base):
    __tablename__ = "colis"
    __table_args__ = (
        CheckConstraint("poids_kg > 0", name="ck_colis_poids_positif"),
        CheckConstraint(
            "statut IN ('en_attente', 'en_transit', 'livre', 'echec')",
            name="ck_colis_statut_valide",
        ),
        Index("idx_colis_client_id", "client_id"),
        Index("idx_colis_statut", "statut"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expediteur_id: Mapped[uuid.UUID] = mapped_column(
        "client_id",
        Uuid(as_uuid=True),
        ForeignKey("utilisateurs.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    destinataire_nom: Mapped[str] = mapped_column(String(100), nullable=False)
    destinataire_adresse: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    poids_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    statut: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="en_attente"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
