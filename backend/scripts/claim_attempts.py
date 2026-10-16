"""Assign ownerless attempts to a user.

Attempts recorded before accounts existed (V1/V2 history) had no owner and
were visible to nobody. Since V3.1 every attempt must have one: the migration
that makes attempts.user_id NOT NULL refuses to run while any remain. Run this
against the database before that upgrade, after registering your account:

    python -m scripts.claim_attempts <username>
    docker compose run --rm backend python -m scripts.claim_attempts <username>   # with Docker Compose

Only ownerless attempts are touched; attempts that already belong to someone
are never reassigned. Running it again is harmless.
"""

import argparse
import sys

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.models import Attempt, User
from app.db.session import get_sessionmaker
from app.services.auth_service import normalize_username


class ClaimError(Exception):
    pass


def claim_attempts(session: Session, username: str) -> int:
    """Gives every ownerless attempt to `username`; returns how many were claimed."""
    user = session.scalar(select(User).where(User.username == normalize_username(username)))
    if user is None:
        raise ClaimError(f"No user named '{username}'. Register the account in the app first.")
    result = session.execute(update(Attempt).where(Attempt.user_id.is_(None)).values(user_id=user.id))
    session.commit()
    return result.rowcount


def count_ownerless(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id.is_(None)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("username", help="the account that should own the ownerless attempts")
    args = parser.parse_args(argv)

    with get_sessionmaker()() as session:
        try:
            claimed = claim_attempts(session, args.username)
        except ClaimError as exc:
            print(exc, file=sys.stderr)
            return 1
    print(f"Assigned {claimed} ownerless attempt(s) to '{normalize_username(args.username)}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
