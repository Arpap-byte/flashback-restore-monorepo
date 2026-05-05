"""
Schémas Pydantic pour les requêtes et réponses de l'API Flaskback Restore.

Tous les messages sont en français, destinés à une application francophone.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Analyse de photo
# ---------------------------------------------------------------------------

class AnalyseReponse(BaseModel):
    """Résultat de l'analyse d'une photo ancienne/abîmée."""

    rayures: bool = Field(..., description="Présence de rayures sur la photo")
    decoloration: bool = Field(..., description="Présence de décoloration / jaunissement")
    taches: bool = Field(..., description="Présence de taches ou moisissures")
    dechirures: bool = Field(..., description="Présence de déchirures")
    bruit: bool = Field(..., description="Présence de bruit numérique ou argentique")
    etat_global: str = Field(
        ..., description="État global : excellent, bon, moyen, mauvais, très_mauvais"
    )
    age_estime: str = Field(..., description="Âge estimé de la photo (ex: 30-40 ans)")
    recommandations: list[str] = Field(
        default_factory=list,
        description="Recommandations de restauration en français",
    )


# ---------------------------------------------------------------------------
# Paramètres de restauration
# ---------------------------------------------------------------------------

class ParametresRestauration(BaseModel):
    """Paramètres de restauration extraits par Gemini."""

    luminosite: float = Field(
        default=1.0, ge=0.5, le=2.0,
        description="Facteur de luminosité (0.5 à 2.0)",
    )
    contraste: float = Field(
        default=1.0, ge=0.5, le=2.0,
        description="Facteur de contraste (0.5 à 2.0)",
    )
    saturation: float = Field(
        default=1.0, ge=0.0, le=2.0,
        description="Facteur de saturation (0.0 à 2.0)",
    )
    nettete: float = Field(
        default=1.0, ge=0.5, le=3.0,
        description="Facteur de netteté (0.5 à 3.0)",
    )
    debruitage: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Intensité du débruitage (0.0 à 1.0)",
    )
    correction_rouge: float = Field(
        default=1.0, ge=0.5, le=2.0,
        description="Correction du canal rouge (0.5 à 2.0)",
    )
    correction_vert: float = Field(
        default=1.0, ge=0.5, le=2.0,
        description="Correction du canal vert (0.5 à 2.0)",
    )
    correction_bleu: float = Field(
        default=1.0, ge=0.5, le=2.0,
        description="Correction du canal bleu (0.5 à 2.0)",
    )


class RestaurationReponse(BaseModel):
    """Réponse après restauration d'une photo."""

    message: str = Field(..., description="Message de succès")
    analyse: AnalyseReponse
    parametres: ParametresRestauration
    url_image: str = Field(..., description="URL ou chemin de l'image restaurée")


# ---------------------------------------------------------------------------
# Animation (D-ID)
# ---------------------------------------------------------------------------

class AnimationRequete(BaseModel):
    """Requête pour créer une animation D-ID."""

    texte: str = Field(
        default="Bonjour ! Je suis un souvenir restauré.",
        description="Texte que le portrait animé va prononcer",
    )
    voix: Optional[str] = Field(
        default=None,
        description="Identifiant de la voix (laisser vide pour la voix par défaut)",
    )


class AnimationReponse(BaseModel):
    """Réponse après soumission d'une animation."""

    message: str = Field(..., description="Message de confirmation")
    job_id: str = Field(..., description="Identifiant du travail D-ID pour suivi")


class StatutAnimation(str, Enum):
    """Statuts possibles d'une animation D-ID."""

    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    TERMINE = "termine"
    ERREUR = "erreur"


class StatutAnimationReponse(BaseModel):
    """Réponse lors du suivi d'une animation."""

    job_id: str
    statut: StatutAnimation
    url_video: Optional[str] = Field(
        default=None,
        description="URL de la vidéo animée (disponible uniquement si terminé)",
    )
    message: Optional[str] = Field(default=None, description="Message d'erreur éventuel")


# ---------------------------------------------------------------------------
# Santé
# ---------------------------------------------------------------------------

class SanteReponse(BaseModel):
    """Réponse du endpoint de santé."""

    statut: str = Field(default="OK", description="Statut du service")
    version: str = Field(default="1.0.0", description="Version de l'API")
    gemini_disponible: bool = Field(
        default=True, description="Indique si l'API Gemini est configurée"
    )
    did_disponible: bool = Field(
        default=True, description="Indique si l'API D-ID est configurée"
    )
