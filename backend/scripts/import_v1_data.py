"""Sync boss reference data into PostgreSQL, and optionally import V1 attempt history.

    python -m scripts.import_v1_data                              # bosses, phases, moves
    python -m scripts.import_v1_data --attempts path/to/attempts.json

Reference data sync is safe to run on every startup. Attempt import is a
one-time step and refuses to run if the attempts table already has rows.
"""

import argparse
import sys
from pathlib import Path

from app.db.session import get_sessionmaker
from app.seed import BOSSES_FILE, SeedError, import_v1_attempts, load_boss_data, load_v1_attempts, sync_reference_data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bosses", type=Path, default=BOSSES_FILE, help="boss seed file (default: %(default)s)")
    parser.add_argument("--attempts", type=Path, help="V1 attempts.json to import once")
    args = parser.parse_args(argv)

    with get_sessionmaker()() as session:
        try:
            report = sync_reference_data(session, load_boss_data(args.bosses))
            imported = import_v1_attempts(session, load_v1_attempts(args.attempts)) if args.attempts else None
            session.commit()
        except SeedError as exc:
            session.rollback()
            print(f"Import failed, nothing was written.\n{exc}", file=sys.stderr)
            return 1

    print(
        f"Synced {report.bosses} bosses, {report.phases} phases, "
        f"{report.moves} moves, {report.phase_moves} phase-move links."
    )
    for warning in report.warnings:
        print(f"warning: {warning}")
    if imported is not None:
        print(f"Imported {imported} V1 attempts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
