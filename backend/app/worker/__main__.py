"""Run the recording worker: python -m app.worker

Checks every new upload and, once a pipeline version is installed, processes the queued ones; when there is nothing
to do it looks again every WORKER_POLL_SECONDS. A database that is not up yet, or not migrated yet (the backend runs
the migrations when it starts), is waited for.
"""

import logging
import os
import time

from sqlalchemy.exc import OperationalError, ProgrammingError

from app.db.session import get_sessionmaker
from app.worker import jobs, media
from app.worker.analyzer import load_analyzer

log = logging.getLogger("app.worker")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    poll = float(os.environ.get("WORKER_POLL_SECONDS", "2"))
    if not media.ffmpeg_available():
        log.error("ffmpeg and ffprobe are needed: uploads will be rejected as unreadable")
    analyzer = load_analyzer()
    log.info("pipeline: %s", analyzer.version if analyzer else "none installed yet; queued recordings wait")
    sessions = get_sessionmaker()
    recovered = False
    while True:
        busy = False
        try:
            with sessions() as session:
                if not recovered:
                    if count := jobs.recover_interrupted(session):
                        log.info("put back %d recording(s) left half done", count)
                    recovered = True
                busy = jobs.run_once(session, analyzer)
        except (OperationalError, ProgrammingError) as exc:
            log.warning("database not ready (%s); trying again", type(exc).__name__)
        if not busy:
            time.sleep(poll)


if __name__ == "__main__":
    main()
