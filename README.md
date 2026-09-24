# Sekiro Boss Practice Analytics

English | [简体中文](README.zh-CN.md)

A web app for tracking *Sekiro: Shadows Die Twice* boss attempts, mistakes, and player improvement over time.

## Why This Tool

Sekiro players often struggle with bosses such as Genichiro, Isshin, Owl (Father), and Corrupted Monk, yet most players do not have a structured way to understand:

* which boss attacks or skills cause the most deaths
* whether they are actually improving
* which phase is the main bottleneck
* how many attempts it takes to defeat each boss

Sekiro Boss Practice Analytics turns individual boss attempts into structured practice data.

Instead of requiring players to remember detailed combat statistics, the app focuses on information players can realistically recall after each attempt, such as the phase reached and the move that caused the final failure.

The application then uses this history to identify recurring weaknesses and progression patterns.

---

## V1 — Manual Attempt Analytics

V1 is a manual boss-attempt tracking and failure analytics tool.

Players record how far they reached and what ended each attempt, and the app identifies their most common failure moves and bottleneck phases.

### V1.0 — Completed

V1.0 implements the complete initial end-to-end workflow using **Genichiro Ashina** as the representative boss.

The goal of V1 was intentionally not to provide complete Sekiro boss coverage. Instead, it validates the full application architecture and user workflow before expanding the dataset.

### V1 Features

* Browse supported Sekiro bosses
* View boss phases and movesets
* Record boss attempts
* Record whether an attempt ended in victory or failure
* Record the phase reached
* Record the boss move that caused the final failure
* Support `Other` and `Not Sure` when the failure move is unknown
* Add optional notes to an attempt
* View attempt history
* View total attempt statistics
* Identify the most common failure move
* Identify the main bottleneck phase
* View basic progress analytics

### V1 User Flow

```text
Choose Boss
    ↓
Boss Dashboard
    ↓
Record Attempt
    ↓
Result + Phase Reached + Failure Move
    ↓
Save Attempt
    ↓
Attempt History
    ↓
Failure Analytics
```

V1 intentionally focuses on a small dataset and a complete vertical slice rather than broad boss coverage.

---

## V2 — Structured Sekiro Analytics Platform

### V2.0 — Completed

V2 expanded the V1 prototype into a structured, multi-boss Sekiro practice analytics platform.

The main change in V2 was moving from a small JSON-backed MVP to a relational persistence and analytics architecture that supports multiple bosses and larger attempt histories. The lightweight attempt form from V1 is unchanged: result, phase reached, failure move / `Other` / `Not Sure`, and optional notes.

### V2 Features

#### PostgreSQL Persistence

The V1 JSON persistence layer was replaced with PostgreSQL, using SQLAlchemy for the ORM and Alembic for schema migrations.

The relational model:

```text
Game
 └── Boss
      ├── Phase
      ├── Move
      └── Attempt
           └── Failure Move

Phase ←── many-to-many ──→ Move
```

A move belongs to a boss and is stored once, even when it appears in several phases. A join table records which phases each move appears in, and in what order, so an attempt that failed to the same move always points to the same record, regardless of the phase.

Database constraints and service-level validation reject invalid data, such as a failure move from another boss, a move that does not appear in the phase reached, or a victory with a failure cause.

Boss data lives in `backend/seed/bosses.json` and is synced into PostgreSQL every time the backend starts. The sync is idempotent. A separate one-time import script migrated the V1 attempt history.

The frontend API contract from V1 was preserved through the migration.

#### Expanded Boss Coverage

V2 supports 8 major Sekiro bosses:

* Genichiro Ashina
* Owl (Father)
* Lady Butterfly
* Guardian Ape
* Corrupted Monk
* True Corrupted Monk
* Great Shinobi Owl
* Isshin, the Sword Saint

Bosses have different numbers of phases and different movesets, and every boss uses the same code path. Boss cards show both English and Chinese names.

#### Richer Boss Data

Each move includes:

* the phases it appears in
* move type
* attack description
* telegraph, where the source describes one
* counter
* common mistakes, where the source describes them

#### Progress Analytics

On top of the V1 metrics, each boss dashboard now shows:

* an attempt progression chart of the phase reached on each attempt
* all-time vs. last 10 attempts comparisons of failures by phase and by move
* attempts until first victory, counting the winning attempt

For example:

```text
                     All-Time   Last 10
Floating Passage        12         2
```

This shows that recorded failures to a move are becoming less common. The app does not present this as a move success rate, because it does not know how many times the move occurred.

Ties are shown as ties, not broken arbitrarily.

#### Overall Sekiro Dashboard

The home page is now a game-level dashboard showing:

* bosses attempted and bosses defeated
* total attempts
* most practiced boss
* boss requiring the most attempts before first victory
* recent practice activity (last 7 days and the last 10 attempts across all bosses)
* a boss comparison table with attempts, best result, and defeated status

The boss list moved to `/bosses`.

#### Data Provenance

Every boss records the wiki page its moveset data came from. Move details are taken from those sources rather than invented.

#### CI and Local Deployment

Every pull request runs four GitHub Actions jobs, and all four must pass before merging into `dev` or `main`:

* **backend:** pytest against PostgreSQL, including a check that the models match the Alembic migrations
* **frontend:** type checking, linting, unit tests, and a production build
* **integration:** the frontend's API client against the real backend and PostgreSQL
* **docker:** builds the Docker Compose stack and smoke tests it through nginx

V2 runs locally with Docker Compose.

#### Deferred or Skipped

* **Public deployment** moved into V3: there is currently a single user, and without accounts a public instance would let anyone record attempts. V3 adds accounts, which removes that problem.
* **Boss search and filtering** was skipped, because 8 bosses fit comfortably on one page.

---

## Future Direction

The longer-term roadmap is:

```text
V1
Manual boss-attempt tracking
+
basic failure analytics

        ↓

V2
PostgreSQL
+
expanded Sekiro boss data
+
richer progression analytics

        ↓

V3
User accounts
+
per-user attempt histories
+
evidence-based practice recommendations
+
public deployment

        ↓

V4
Gameplay video analysis
+
automatic / semi-automatic move detection
+
detailed combat performance metrics

        ↓

V5
Multi-game platform
+
Sekiro
+
Black Myth: Wukong
```

The long-term goal is to evolve Sekiro Boss Practice Analytics from a manual attempt tracker into a generalized boss-practice and gameplay-performance analytics platform.

---

## Tech Stack

### V1.0

* **Backend:** FastAPI
* **Persistence:** JSON
* **Frontend:** React + TypeScript
* **Deployment:** Docker

V1 intentionally uses JSON persistence because the initial dataset is small and the primary goal is validating the complete application workflow.

### V2.0

* **Backend:** FastAPI
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy
* **Database Migrations:** Alembic
* **Frontend:** React + TypeScript
* **Deployment:** Docker Compose (local)
* **CI:** GitHub Actions

---

## Running Locally

Requires [Docker](https://www.docker.com/) (Docker Desktop on Windows or macOS).

1. Create your environment file and choose a database password:

   ```bash
   cp .env.example .env
   ```

   Replace `change-me` everywhere in `.env` with the same password.

2. Build and start the stack:

   ```bash
   docker compose up -d --build
   ```

   On every start the backend applies database migrations and loads the bosses from `backend/seed/bosses.json`.

3. Open http://localhost:8080 and create an account. Boss movesets can be browsed without one; recording attempts and viewing analytics need a login. The API documentation is at http://localhost:8000/docs.

To open the app on a phone on the same network, use `http://<your computer's LAN IP>:8080`. On Windows, find the IP with `ipconfig` under the Ethernet or Wi-Fi adapter, not the `vEthernet (WSL)` one.

Attempt data is kept in the `postgres-data` Docker volume. `docker compose down` keeps it; `docker compose down -v` deletes it.

### Running the Tests

The backend and integration tests need PostgreSQL running (`docker compose up -d postgres`).

```bash
# Backend: database tests read TEST_DATABASE_URL from the environment and are skipped without it
cd backend
pip install -r requirements.txt
set -a; . ../.env; set +a   # load .env into the environment (bash)
pytest

# Frontend
cd frontend
npm ci
npm test
npm run test:integration   # reads TEST_DATABASE_URL from .env; needs the backend's Python environment
```