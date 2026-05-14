"""Tests de non-régression pour la tarification V2."""

import pytest
import sys
sys.path.insert(0, "..")

from app.api.routes import (
    TARIF_RESTAURATION,
    TARIF_COLORISATION,
    TARIF_ANIMATION,
)


class TestTarification:
    """Vérifie que la grille tarifaire est correcte."""

    def test_tarif_restauration_720p(self):
        assert TARIF_RESTAURATION["720p"] == 1

    def test_tarif_restauration_1080p(self):
        assert TARIF_RESTAURATION["1080p"] == 2

    def test_tarif_restauration_4k(self):
        assert TARIF_RESTAURATION["4k"] == 4

    def test_tarif_colorisation_720p(self):
        assert TARIF_COLORISATION["720p"] == 1

    def test_tarif_colorisation_1080p(self):
        assert TARIF_COLORISATION["1080p"] == 2

    def test_tarif_colorisation_4k(self):
        assert TARIF_COLORISATION["4k"] == 4

    def test_tarif_animation_720p(self):
        assert TARIF_ANIMATION["720p"] == 10

    def test_tarif_animation_1080p(self):
        assert TARIF_ANIMATION["1080p"] == 20

    def test_tarif_restauration_720p_colorize_total(self):
        """720p + colorisation = 1 + 1 = 2 crédits"""
        total = TARIF_RESTAURATION["720p"] + TARIF_COLORISATION["720p"]
        assert total == 2

    def test_tarif_restauration_4k_colorize_total(self):
        """4K + colorisation = 4 + 4 = 8 crédits"""
        total = TARIF_RESTAURATION["4k"] + TARIF_COLORISATION["4k"]
        assert total == 8

    def test_resolution_invalide_non_presente(self):
        """Les résolutions non supportées ne sont pas dans le dict."""
        assert "480p" not in TARIF_RESTAURATION
        assert "8k" not in TARIF_RESTAURATION


class TestValidationResolution:
    """Vérifie que l'API rejette les résolutions invalides (tests d'intégration)."""

    @pytest.mark.skip(reason="Nécessite setup JWT + client async complet")
    async def test_restore_resolution_invalide_retourne_400(self):
        pass

    @pytest.mark.skip(reason="Nécessite setup JWT + client async complet")
    async def test_colorize_resolution_invalide_retourne_400(self):
        pass
