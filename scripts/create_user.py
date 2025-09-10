#!/usr/bin/env python3
"""
Create or update a user account and optionally grant subscription status.

Usage examples:
  python scripts/create_user.py --email user@example.com --name "User Name" --generate-password --make-subscribed --provider admin
  python scripts/create_user.py --email user@example.com --password-env USER_PASSWORD --make-subscribed

Notes:
- If --generate-password is used, a secure temporary password will be generated and printed once.
- If the user already exists, fields will be updated as requested.
"""
import argparse
import os
import sys
import secrets

from app import create_app, db
from app.models import User


def upsert_user(email: str,
                name: str | None = None,
                password: str | None = None,
                make_subscribed: bool = False,
                provider: str | None = None) -> tuple[dict, str | None, bool]:
    """Create or update a user. Returns (summary_dict, generated_password, created_new)."""
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User.query.filter_by(email=email.lower()).first()
        created_new = False
        generated_password = None

        if not user:
            if not name:
                # Derive a friendly name from email if not provided
                local = email.split('@', 1)[0].replace('.', ' ').replace('_', ' ').title()
                name = local or 'User'
            user = User(name=name.strip(), email=email.lower())
            created_new = True

        # Set/Update password if provided
        if password:
            user.set_password(password)
        elif created_new and password is None:
            # For a brand-new user, ensure there is a password
            generated_password = secrets.token_urlsafe(12)
            user.set_password(generated_password)

        # Subscription flags
        if make_subscribed:
            user.is_subscribed = True
            if provider:
                user.provider = provider

        # Persist
        if created_new:
            db.session.add(user)
        db.session.commit()

        summary = {
            'email': user.email,
            'name': user.name,
            'is_subscribed': user.is_subscribed,
            'provider': user.provider,
        }
        return summary, generated_password, created_new


def main():
    parser = argparse.ArgumentParser(description="Create or update a user account")
    parser.add_argument('--email', required=True, help='Email for the user (unique)')
    parser.add_argument('--name', help='Display name for the user')
    parser.add_argument('--password', help='Password to set (NOT recommended to pass in plain text)')
    parser.add_argument('--password-env', dest='password_env', help='Environment variable name containing the password')
    parser.add_argument('--generate-password', action='store_true', help='Generate a secure temporary password if creating a new user')
    parser.add_argument('--make-subscribed', action='store_true', help='Mark the user as subscribed')
    parser.add_argument('--provider', default=None, help="Subscription provider label, e.g. 'admin', 'stripe', 'paypal'")

    args = parser.parse_args()

    # Resolve password safely
    password = None
    if args.password_env:
        env_name = args.password_env
        password = os.environ.get(env_name)
        if password is None:
            print(f"ERROR: Environment variable {env_name} is not set", file=sys.stderr)
            sys.exit(2)
    elif args.password:
        password = args.password  # As provided (use with caution)

    summary, generated_password, created_new = upsert_user(
        email=args.email,
        name=args.name,
        password=password if password else (None if args.generate_password else None),
        make_subscribed=args.make_subscribed,
        provider=args.provider,
    )

    # Output summary (avoid printing any provided password env value)
    print("=== User Upsert Result ===")
    print(f"Email: {summary['email']}")
    print(f"Name: {summary['name']}")
    print(f"Created new: {created_new}")
    print(f"Subscribed: {summary['is_subscribed']}")
    print(f"Provider: {summary['provider'] or ''}")

    if created_new and generated_password:
        print("\nA secure temporary password was generated for this new account:")
        print(generated_password)
        print("\nPlease store it securely and change it after first login (once a change-password flow exists).")


if __name__ == '__main__':
    main()

