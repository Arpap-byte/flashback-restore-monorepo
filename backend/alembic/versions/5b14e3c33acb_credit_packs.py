"""credit_packs

Revision ID: 5b14e3c33acb
Revises: 31fffebd0c35
Create Date: 2026-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b14e3c33acb'
down_revision: Union[str, Sequence[str], None] = '8dc346ab91ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'credit_packs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('stripe_price_id', sa.String(100), nullable=False, unique=True),
        sa.Column('stripe_product_id', sa.String(100), nullable=False),
        sa.Column('nom', sa.String(100), nullable=False),
        sa.Column('credits', sa.Integer(), nullable=False),
        sa.Column('prix_centimes', sa.Integer(), nullable=False),
        sa.Column('actif', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('cree_le', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Étendre credit_transactions avec source
    op.execute("""
        ALTER TABLE achats_credits 
        ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'subscription'
    """)
    op.execute("""
        ALTER TABLE achats_credits 
        ADD CONSTRAINT ck_achats_source CHECK (
            source IN ('subscription', 'pack', 'bonus', 'refund')
        )
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE achats_credits DROP CONSTRAINT IF EXISTS ck_achats_source")
    op.execute("ALTER TABLE achats_credits DROP COLUMN IF EXISTS source")
    op.drop_table('credit_packs')
