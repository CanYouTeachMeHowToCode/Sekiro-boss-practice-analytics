"""The recording worker (V4 Milestone 3): checks uploaded recordings and turns them into failure reports.

Runs as its own Compose service (`python -m app.worker`, image Dockerfile.worker, which adds ffmpeg) next to the
backend, sharing its database and the recordings volume. See jobs.py for the steps and statuses.
"""
