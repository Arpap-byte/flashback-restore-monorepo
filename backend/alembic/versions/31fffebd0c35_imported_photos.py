"""imported_photos

Revision ID: 31fffebd0c35
Revises: d9e4a25a8bc3
Create Date: 2026-05-19 16:28:25.569281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31fffebd0c35'
down_revision: Union[str, Sequence[str], None] = 'd9e4a25a8bc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'imported_photos',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('utilisateur_id', sa.String(36), sa.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('chemin_original', sa.String(500), nullable=False),
        sa.Column('b2_key', sa.String(500), nullable=True),
        sa.Column('taille', sa.Integer(), nullable=False),  # octets
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('content_type', sa.String(50), nullable=True),
        sa.Column('nom_fichier', sa.String(255), nullable=True),
        sa.Column('cree_le', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('supprime_le', sa.DateTime(timezone=True), nullable=True, index=True),  # soft-delete (NULL = actif)
    )


def downgrade() -> None:
    op.drop_table('imported_photos')
