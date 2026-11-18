"""Make a user an admin, or stop them being one.

An admin may open every user's recordings and reports in the app, read-only (owner decision, 2026-11-18). No API
changes this: it is set only here, on the server.

    python -m scripts.set_admin <username>          # make an admin
    python -m scripts.set_admin <username> --off    # no longer an admin
    docker compose exec backend python -m scripts.set_admin <username>   # with Docker Compose

Running it again is harmless.
"""

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_sessionmaker
from app.services.auth_service import normalize_username


class SetAdminError(Exception):
    pass


def set_admin(session: Session, username: str, admin: bool = True) -> User:
    """Sets whether `username` is an admin and returns the user."""
    user = session.scalar(select(User).where(User.username == normalize_username(username)))
    if user is None:
        raise SetAdminError(f"No user named '{username}'. Register the account in the app first.")
    user.is_admin = admin
    session.commit()
    return user


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("username", help="the account to change")
    parser.add_argument("--off", action="store_true", help="remove admin instead of granting it")
    args = parser.parse_args(argv)

    with get_sessionmaker()() as session:
        try:
            user = set_admin(session, args.username, admin=not args.off)
        except SetAdminError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"'{user.username}' is {'now' if user.is_admin else 'no longer'} an admin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
