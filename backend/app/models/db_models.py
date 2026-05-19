"""
Modèles SQLAlchemy pour Flashback Restore.

ORM mapping vers PostgreSQL (Phase 2 de migration depuis SQLite).
Définitions basées sur les CREATE TABLE de database.py.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base déclarative pour tous les modèles."""
    pass


def _utcnow() -> datetime:
    """Retourne le timestamp UTC courant avec timezone."""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    """Génère un UUID v4 sous forme de chaîne."""
    return str(uuid.uuid4())


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id = Column(String, primary_key=True, default=_new_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    essais_restants = Column(Integer, nullable=False, default=3)
    credits = Column(Integer, nullable=False, default=0)
    est_abonne = Column(Integer, nullable=False, default=0)  # 0/1 flag
    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    derniere_connexion = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # OAuth (migration)
    oauth_provider = Column(String, nullable=True)
    oauth_provider_id = Column(String, nullable=True)

    # Plan / Animation (migration rapport COGS 10/05/2026)
    plan = Column(String, nullable=True, default="gratuit")
    animations_utilisees = Column(Integer, nullable=True, default=0)
    mois_animation_courant = Column(String, nullable=True)

    # Crédits perpétuels (packs achetés, n'expirent jamais)
    credits_perpetuels = Column(Integer, nullable=False, default=0)

    # Rétention & Dashboard admin (migration 12/05/2026)
    retention_jours = Column(Integer, nullable=False, default=30)
    derniere_activite = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_oauth_provider", "oauth_provider", "oauth_provider_id"),
        CheckConstraint(
            "retention_jours IN (7, 30, 90)",
            name="ck_utilisateurs_retention",
        ),
    )


class Travail(Base):
    __tablename__ = "travaux"

    id = Column(String, primary_key=True, default=_new_uuid)
    type = Column(
        String,
        nullable=False,
    )
    statut = Column(String, nullable=False, default="cree")
    utilisateur_id = Column(String, ForeignKey("utilisateurs.id"), nullable=True, index=True)
    chemin_photo = Column(String, nullable=True)
    chemin_resultat = Column(String, nullable=True)
    chemin_animation = Column(String, nullable=True)
    taille_original = Column(Integer, nullable=True)
    taille_resultat = Column(Integer, nullable=True)
    resultat_json = Column(Text, nullable=True)
    job_externe_id = Column(String, nullable=True)
    message_erreur = Column(Text, nullable=True)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    modifie_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("idx_travaux_statut", "statut"),
        Index("idx_travaux_type", "type"),
        Index("idx_travaux_user_date", "utilisateur_id", text("cree_le DESC")),
        CheckConstraint(
            "type IN ('analyse', 'restauration', 'animation', 'colorisation')",
            name="ck_travaux_type",
        ),
        CheckConstraint(
            "statut IN ('cree', 'en_cours', 'termine', 'erreur')",
            name="ck_travaux_statut",
        ),
    )


class Abonnement(Base):
    __tablename__ = "abonnements"

    id = Column(String, primary_key=True, default=_new_uuid)
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    statut = Column(String, nullable=False, default="cree")
    plan = Column(String, nullable=True)
    email_utilisateur = Column(String, nullable=True)
    derniere_attribution_credits = Column(String, nullable=True)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    modifie_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("idx_abonnements_statut", "statut"),
        CheckConstraint(
            "statut IN ('cree', 'actif', 'impaye', 'resilie', 'expire')",
            name="ck_abonnements_statut",
        ),
    )


class EssaiGratuit(Base):
    __tablename__ = "essais_gratuits"

    id = Column(String, primary_key=True, default=_new_uuid)
    utilisateur_id = Column(String, ForeignKey("utilisateurs.id"), nullable=False, index=True)
    type_travail = Column(
        String,
        nullable=False,
    )
    travail_id = Column(String, nullable=True)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        CheckConstraint(
            "type_travail IN ('analyse', 'restauration', 'animation', 'colorisation')",
            name="ck_essais_type",
        ),
    )


class AchatCredits(Base):
    __tablename__ = "achats_credits"

    id = Column(String, primary_key=True, default=_new_uuid)
    utilisateur_id = Column(String, ForeignKey("utilisateurs.id"), nullable=False, index=True)
    stripe_session_id = Column(String, nullable=True)
    nombre_credits = Column(Integer, nullable=False)
    montant_euros = Column(Float, nullable=False)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class ConsommationCredits(Base):
    __tablename__ = "consommation_credits"

    id = Column(String, primary_key=True, default=_new_uuid)
    utilisateur_id = Column(String, ForeignKey("utilisateurs.id"), nullable=False, index=True)
    travail_id = Column(String, ForeignKey("travaux.id"), nullable=False)
    type_operation = Column(
        String,
        nullable=False,
    )
    credits_utilises = Column(Integer, nullable=False, default=1)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        CheckConstraint(
            "type_operation IN ('restauration', 'animation', 'colorisation')",
            name="ck_consommation_type",
        ),
    )


class ReinitialisationMdp(Base):
    __tablename__ = "reinitialisation_mdp"

    id = Column(String, primary_key=True, default=_new_uuid)
    utilisateur_id = Column(String, ForeignKey("utilisateurs.id"), nullable=False, index=True)
    token = Column(String, nullable=False, unique=True, index=True)
    expire_le = Column(DateTime(timezone=True), nullable=False)
    utilise = Column(Integer, nullable=False, default=0)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=_new_uuid)
    evenement = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True, index=True)
    utilisateur_id = Column(String, ForeignKey("utilisateurs.id"), nullable=True)
    ip = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    reussite = Column(Integer, nullable=False, default=1)
    detail = Column(Text, nullable=True)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    __table_args__ = (
        Index("idx_audit_reussite", "reussite"),
    )


class StripeEvent(Base):
    """Traçabilité des événements Stripe pour idempotence des webhooks."""

    __tablename__ = "stripe_events"

    id = Column(String, primary_key=True, default=_new_uuid)
    event_id = Column(String, nullable=False, unique=True, index=True)
    type_evenement = Column(String, nullable=False)
    traite_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("idx_stripe_event_id", "event_id"),
    )


class Consentement(Base):
    """Trace immuable des consentements légaux (CGV, rétractation, RGPD).

    Append-only : une révocation crée une nouvelle ligne avec retire_le,
    on ne modifie jamais une ligne existante (preuve légale).
    """

    __tablename__ = "consentements"

    id = Column(String, primary_key=True, default=_new_uuid)
    utilisateur_id = Column(String, ForeignKey("utilisateurs.id"), nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    type_consentement = Column(String, nullable=False, index=True)
    accepte = Column(Boolean, nullable=False, default=True)
    version_texte = Column(String, nullable=False)
    ip = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    contexte = Column(Text, nullable=True)
    accorde_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    retire_le = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_consentements_user_type", "utilisateur_id", "type_consentement"),
        CheckConstraint(
            "type_consentement IN ('cgv_checkout', 'renonciation_retractation', "
            "'rgpd_biometrique', 'rgpd_ia')",
            name="ck_consentements_type",
        ),
    )


class ImageImportee(Base):
    """Galerie personnelle d'images importées par l'utilisateur (sans traitement IA)."""

    __tablename__ = "images_importees"

    id = Column(String, primary_key=True, default=_new_uuid)
    utilisateur_id = Column(String, ForeignKey("utilisateurs.id"), nullable=False, index=True)
    chemin_fichier = Column(String, nullable=False)
    nom_origine = Column(String, nullable=True)
    mime_type = Column(String, nullable=False)
    taille_octets = Column(Integer, nullable=False)
    largeur = Column(Integer, nullable=True)
    hauteur = Column(Integer, nullable=True)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    derniere_utilisation = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_lib_user_date", "utilisateur_id", text("cree_le DESC")),
        CheckConstraint(
            "mime_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_lib_mime",
        ),
    )


class CreditPack(Base):
    """Pack de crédits standalone (one-shot, pas d'abonnement)."""

    __tablename__ = "credit_packs"

    id = Column(String, primary_key=True, default=_new_uuid)
    stripe_price_id = Column(String, nullable=False, unique=True)
    stripe_product_id = Column(String, nullable=False)
    nom = Column(String, nullable=False)
    credits = Column(Integer, nullable=False)
    prix_centimes = Column(Integer, nullable=False)
    actif = Column(Boolean, nullable=False, default=True)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
