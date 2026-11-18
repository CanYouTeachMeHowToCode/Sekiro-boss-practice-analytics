"""Analyse a recording again, keeping its video: after a new pipeline version, or a fix to the checks.

Its failures and clips are removed and it goes back to "uploaded", so the worker checks it again (format and content)
and analyses it with the version it runs now. The owner sees it waiting and then the new report.

    python -m scripts.reanalyze <recording id>
    docker compose exec backend python -m scripts.reanalyze <recording id>   # with Docker Compose

A recording the worker is checking or analysing right now is left alone: wait until it is done.
"""

import argparse
import shutil
import sys

from sqlalchemy.orm import Session

from app.db import models as db
from app.db.session import get_sessionmaker
from app.services.recording_service import clips_dir, recordings_dir

BUSY = ("checking", "processing")


class ReanalyzeError(Exception):
    pass


def reanalyze(session: Session, recording_id: int) -> db.Recording:
    """Puts the recording back to "uploaded" without its failures, clips or results; the video stays."""
    row = session.get(db.Recording, recording_id)
    if row is None:
        raise ReanalyzeError(f"No recording {recording_id}.")
    if row.status in BUSY:
        raise ReanalyzeError(f"Recording {recording_id} is {row.status} right now: try again when it is done.")
    row.failures.clear()
    row.status, row.reject_code, row.progress, row.error = "uploaded", None, 0.0, None
    row.processed_at, row.pipeline_version = None, None
    session.commit()
    shutil.rmtree(clips_dir(recordings_dir() / row.storage_path), ignore_errors=True)
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("recording_id", type=int, help="the recording's id (the admin list and the URLs show it)")
    args = parser.parse_args(argv)

    with get_sessionmaker()() as session:
        try:
            row = reanalyze(session, args.recording_id)
        except ReanalyzeError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"Recording {row.id} ({row.original_filename}) is waiting to be checked and analysed again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
