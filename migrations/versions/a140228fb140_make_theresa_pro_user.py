"""make_theresa_pro_user

Revision ID: a140228fb140
Revises: a4b9000ca891
Create Date: 2025-09-14 19:51:28.905948

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision = 'a140228fb140'
down_revision = 'a4b9000ca891'
branch_labels = None
depends_on = None


def upgrade():
    """Update theresasumma@gmail.com to be a pro user with Stripe provider."""
    # Use raw SQL to update the user
    conn = op.get_bind()
    
    # First check if the user exists
    result = conn.execute(
        text("SELECT id, email, is_subscribed FROM \"user\" WHERE email = :email"),
        {"email": "theresasumma@gmail.com"}
    )
    
    user = result.fetchone()
    
    if user:
        # Update existing user to be a pro subscriber
        conn.execute(
            text(
                "UPDATE \"user\" SET is_subscribed = :is_subscribed, provider = :provider "
                "WHERE email = :email"
            ),
            {
                "is_subscribed": True,
                "provider": "admin",  # Using 'admin' to indicate manually granted access
                "email": "theresasumma@gmail.com"
            }
        )
        print(f"✅ Updated user theresasumma@gmail.com to Pro status")
    else:
        print(f"⚠️ User theresasumma@gmail.com not found in database. Please create the user first.")


def downgrade():
    """Revert theresasumma@gmail.com back to free user."""
    conn = op.get_bind()
    
    # Revert the user back to free status
    conn.execute(
        text(
            "UPDATE \"user\" SET is_subscribed = :is_subscribed, provider = NULL "
            "WHERE email = :email"
        ),
        {
            "is_subscribed": False,
            "email": "theresasumma@gmail.com"
        }
    )
    print(f"✅ Reverted user theresasumma@gmail.com to Free status")
