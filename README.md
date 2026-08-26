# Sekiro Boss Practice Analytics

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

V2 will expand the V1 prototype into a more complete Sekiro practice analytics platform.

The main focus of V2 is moving from a small JSON-backed MVP to a structured persistence and analytics architecture capable of supporting multiple bosses and larger attempt histories.

### Planned V2 Features

#### PostgreSQL Persistence

Replace the V1 JSON persistence layer with PostgreSQL.

The V2 relational model will approximately represent:

```text
Game
 └── Boss
      └── Phase
           └── Move

Boss
 └── Attempt
      └── Failure Move
```

This will introduce:

* PostgreSQL
* SQLAlchemy
* database relationships and foreign keys
* schema migrations with Alembic
* migration of existing V1 JSON data into PostgreSQL

The frontend API contract should remain largely unchanged when the underlying persistence layer moves from JSON to PostgreSQL.

#### Expanded Boss Coverage

V2 will add additional major Sekiro bosses beyond Genichiro.

Potential additions include:

* Lady Butterfly
* Guardian Ape
* Corrupted Monk
* Great Shinobi Owl
* Owl (Father)
* Isshin

Boss coverage will be expanded incrementally rather than attempting to build a complete Sekiro encyclopedia immediately.

#### Richer Boss Data

Boss moves may contain additional structured information such as:

* phase availability
* move type
* attack description
* telegraph
* recommended response
* common mistakes

This boss metadata will also provide a stronger foundation for future gameplay analysis.

#### Improved Progress Analytics

V2 will move beyond simple aggregate counts and introduce progression-oriented analytics such as:

* attempt progression over time
* phase reached across recent attempts
* all-time vs. recent failure patterns
* changes in commonly reported failure moves
* attempts required before first victory
* boss difficulty based on the player's attempt history

For example:

```text
All Attempts

Floating Passage failures: 12

Last 10 Attempts

Floating Passage failures: 2
```

This can provide evidence that a particular weakness is becoming less frequent over time.

V2 will avoid presenting metrics such as move success rate unless the application has enough data to calculate them correctly.

#### Overall Sekiro Dashboard

In addition to individual boss dashboards, V2 may provide a game-level analytics dashboard showing information such as:

* bosses attempted
* bosses defeated
* total attempts
* boss requiring the most attempts
* recent practice activity
* progression across multiple bosses

#### Search and Filtering

As the supported boss dataset grows, V2 may add:

* boss search
* attempted / not attempted filters
* defeated / not defeated filters
* location filtering

#### Data Provenance

Boss and moveset information may include source metadata so that game knowledge can be traced back to reliable sources such as community documentation or Sekiro Wiki references.

#### Deployment and CI/CD

V2 may extend the current development workflow into separate deployment environments:

```text
feature/*
    ↓
dev
    ↓
CI
    ↓
Staging

main
    ↓
CI
    ↓
Production
```

Potential additions include:

* automated backend tests
* frontend type checking and builds
* integration tests
* Docker image builds
* automated staging deployment
* production deployment from stable releases

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
User profiles
+
long-term personalized practice tracking
+
practice recommendations

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

### Planned V2

* **Backend:** FastAPI
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy
* **Database Migrations:** Alembic
* **Frontend:** React + TypeScript
* **Deployment:** Docker
* **CI/CD:** GitHub Actions