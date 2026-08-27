# Sekiro Boss Practice Analytics

## Project Overview

Sekiro Boss Practice Analytics is a web application for tracking and analyzing player attempts against bosses in *Sekiro: Shadows Die Twice*.

Players manually record information they can realistically remember after each boss attempt:

* whether the attempt ended in victory or failure
* which phase they reached
* which move caused the final failure, if known
* optional notes

The application derives analytics from this attempt history to identify:

* frequently recorded failure moves
* bottleneck phases
* progression across attempts
* overall boss progression

---

# Current Project Status

## V1 — Completed

V1 established the complete MVP workflow:

```text
Choose Boss
    ↓
Boss Dashboard
    ↓
Record Attempt
    ↓
Result + Phase + Failure Move
    ↓
Attempt History
    ↓
Basic Analytics
```

V1 uses:

* React + TypeScript
* FastAPI + Pydantic
* JSON persistence
* GitHub Actions CI
* Docker

V1 intentionally validated one complete vertical slice before expanding the system.

---

# Current Development Focus

This repository is now focused on:

> **V2 — Structured Sekiro Analytics Platform**

V2 evolves the JSON-backed MVP into a structured, multi-boss Sekiro analytics application.

The main V2 transition is:

```text
V1

Small boss dataset
+
JSON persistence
+
basic boss-level analytics

        ↓

V2

Multiple bosses
+
PostgreSQL
+
relational data model
+
progression analytics
+
game-level analytics
+
stable deployment
```

---

# V2 Product Goal

V2 should answer:

> **Where am I improving or struggling across Sekiro?**

V1 primarily answers:

> What killed me?

V2 should preserve that functionality while adding:

* multiple major Sekiro bosses
* relational persistence
* richer boss metadata
* progression analytics
* recent vs historical comparisons
* overall Sekiro-level analytics
* search and filtering
* stronger integration testing
* stable public deployment

---

# V2 Core Product Principles

## Preserve Lightweight Attempt Recording

The most important V1 interaction remains unchanged.

Users should still be able to record an attempt quickly using:

```text
Result
Phase Reached
Failure Move / Other / Not Sure
Optional Notes
```

Do NOT expand attempt recording into detailed manual combat telemetry.

Do NOT require users to remember:

* every move encountered
* total deflect attempts
* Mikiri success count
* healing usage
* damage taken
* posture events
* move frequency
* detailed per-action performance

Those belong to gameplay analysis in later versions.

---

## Prefer Derived Analytics

The system should derive weaknesses from attempt history whenever possible.

Do not ask users to manually declare:

```text
"My weakest move is Floating Passage."
```

Prefer computing:

```text
Most Common Recorded Failure:
Floating Passage
```

from attempt data.

---

## Maintain Honest Analytics

Do not calculate or display statistics that the available data cannot support.

For example:

```text
Floating Passage failures: 5
```

is valid.

But:

```text
Floating Passage success rate: 75%
```

is NOT valid unless the system knows how many times Floating Passage actually occurred.

True per-move success rates belong to V4 gameplay analysis.

---

# V2 Non-Goals

Do NOT introduce the following unless explicitly requested:

* user accounts
* authentication
* OAuth
* personalized multi-user histories
* recommendation engines
* gameplay video uploads
* computer vision
* machine learning
* automatic boss move detection
* automatic player action recognition
* Black Myth: Wukong support
* multi-game UI
* Redis without a demonstrated need
* Kafka or message queues without a demonstrated need
* microservices
* Kubernetes purely for complexity
* detailed combat telemetry

These belong to V3–V5 or should only be introduced when justified by an actual technical requirement.

---

# V2 Tech Stack

## Frontend

* React
* TypeScript
* Vite

## Backend

* Python
* FastAPI
* Pydantic

## Database

* PostgreSQL
* SQLAlchemy
* Alembic

## Testing

* pytest
* API tests
* database integration tests
* frontend type checking
* frontend build validation

## CI/CD

* GitHub Actions

## Deployment

* Docker

V2 may introduce staging and production deployment environments.

A separate `stg` Git branch is not required.

---

# V2 High-Level Architecture

```text
Browser
   ↓
React + TypeScript
   ↓
HTTP / JSON
   ↓
FastAPI
   ↓
Service Layer
   ↓
SQLAlchemy
   ↓
PostgreSQL
```

Analytics should conceptually follow:

```text
FastAPI
   ↓
Analytics Service
   ↓
SQLAlchemy Queries
   ↓
PostgreSQL Attempt Data
```

The frontend must remain independent of the persistence implementation.

---

# API Compatibility Principle

The V1 frontend already communicates with FastAPI.

The PostgreSQL migration should preserve existing API contracts wherever practical.

Conceptually:

```text
V1

React
 ↓
FastAPI
 ↓
JSON
```

becomes:

```text
V2

React
 ↓
FastAPI
 ↓
PostgreSQL
```

The frontend should not require a large rewrite simply because persistence changes.

If an API contract must change, make the change deliberately and update frontend types and clients together.

---

# V2 Core Domain Model

The primary domain hierarchy remains:

```text
Game
 └── Boss
      └── Phase
           └── Move
```

Player attempt data:

```text
Boss
 └── Attempt
      ├── Result
      ├── Phase Reached
      ├── Failure Move
      ├── Failure Category
      ├── Notes
      └── Timestamp
```

---

# V2 Relational Data Model

The initial PostgreSQL schema should approximately contain:

```text
games
bosses
boss_phases
moves
attempts
```

Avoid adding tables solely for hypothetical future requirements.

---

## Games

Conceptual fields:

```text
id
slug
name
```

Example:

```text
1
sekiro
Sekiro: Shadows Die Twice
```

Even though V2 supports only Sekiro, retaining the Game entity keeps the domain model clean.

Do NOT build full multi-game functionality in V2.

---

## Bosses

Conceptual fields:

```text
id
game_id
slug
name
location
```

Relationship:

```text
Game
 1
 ↓
Many Bosses
```

---

## Boss Phases

Conceptual fields:

```text
id
boss_id
phase_number
name
```

Relationship:

```text
Boss
 1
 ↓
Many Phases
```

A boss may have a different number of phases from another boss.

Do not assume every boss has exactly three phases.

---

## Moves

Conceptual fields:

```text
id
boss_phase_id
slug
name
move_type
description
telegraph
recommended_response
common_mistakes
source_name
source_url
```

Not every optional field must be populated immediately.

Do not block V2 development on complete moveset documentation.

---

## Attempts

Conceptual fields:

```text
id
boss_id
result
phase_reached
failure_move_id
failure_category
notes
created_at
```

`failure_move_id` should be nullable.

Valid failure categories may include:

```text
known_move
other
not_sure
```

A victory should not require a failure move.

---

# Database Integrity

Use relational constraints where they protect meaningful domain rules.

Examples:

* boss must reference an existing game
* phase must reference an existing boss
* move must reference an existing phase
* attempt must reference an existing boss
* failure move must reference an existing move when present

Application-level validation should still ensure that:

* the selected phase belongs to the selected boss
* the selected failure move belongs to the selected boss
* invalid boss / phase / move combinations are rejected

Do not rely only on frontend validation.

---

# SQLAlchemy Guidelines

Use SQLAlchemy for database persistence.

Prefer clear ORM models and explicit relationships.

Avoid:

* unnecessarily generic base repository frameworks
* excessive abstraction around simple CRUD
* dynamic query builders without a concrete need
* hidden database behavior

Database access should remain understandable to someone reading the code.

---

# Alembic Guidelines

Use Alembic for schema evolution.

Do not manually mutate the production schema without migrations.

Typical workflow:

```text
Modify SQLAlchemy model
        ↓
Generate / write Alembic migration
        ↓
Review migration
        ↓
Apply migration
```

Do not blindly trust autogenerated migrations.

Review:

* created tables
* dropped columns
* constraints
* foreign keys
* nullable changes
* indexes

before applying them.

---

# V1 JSON Migration

Existing V1 data should not simply be discarded.

Create an explicit migration / seed process.

Conceptual flow:

```text
bosses.json
attempts.json
      ↓
Import Script
      ↓
Validate Data
      ↓
PostgreSQL
```

Suggested location:

```text
backend/scripts/
```

Potential script:

```text
import_v1_data.py
```

The import process should:

1. load V1 boss data
2. validate the source records
3. create the game
4. create bosses
5. create phases
6. create moves
7. migrate existing attempt history
8. preserve relationships between attempts and moves
9. avoid creating duplicate seed data when rerun accidentally

Do not permanently maintain two competing persistence implementations after migration is complete.

---

# V2 Boss Coverage

V2 should expand from one representative boss to approximately **5–8 major Sekiro bosses**.

Potential set:

* Genichiro Ashina
* Lady Butterfly
* Guardian Ape
* Corrupted Monk
* Great Shinobi Owl
* Owl (Father)
* Isshin
* Demon of Hatred

The exact list may change.

The objective is NOT full Sekiro encyclopedia coverage.

The objective is to validate that the architecture handles:

* different boss phase counts
* different movesets
* different attempt histories
* multiple boss dashboards
* game-level comparisons

---

# Boss Data Strategy

Do not spend excessive development time entering every possible boss move.

Prioritize:

1. representative bosses
2. major identifiable moves
3. correct phase relationships
4. useful practice information
5. source traceability

Avoid creating hundreds of low-quality placeholder records.

---

# Data Provenance

V2 may include source metadata for boss and move information.

Potential fields:

```text
source_name
source_url
```

This is useful for:

* verifying move descriptions
* future data cleanup
* future structured ingestion
* avoiding invented mechanics

Do not present uncertain Sekiro mechanics as verified facts.

---

# Existing V1 APIs

The following capabilities should remain functional.

## Health

```text
GET /health
```

---

## Boss List

```text
GET /api/bosses
```

---

## Boss Detail

```text
GET /api/bosses/{boss_id}
```

---

## Record Attempt

```text
POST /api/bosses/{boss_id}/attempts
```

---

## Attempt History

```text
GET /api/bosses/{boss_id}/attempts
```

---

## Boss Analytics

```text
GET /api/bosses/{boss_id}/analytics
```

These endpoints should move from JSON-backed services to database-backed services without unnecessary frontend disruption.

---

# V2 Analytics Goal

V1 mainly provides aggregate failure analytics.

V2 should introduce meaningful progression analytics.

The main questions are:

```text
Am I reaching later phases more often?

Are earlier bottlenecks becoming less frequent?

Which boss is currently giving me the most difficulty?

How does recent performance compare with historical performance?
```

---

# Boss-Level Analytics

Boss dashboards should continue to support:

* total attempts
* defeated status
* best phase reached
* main bottleneck phase
* most common known failure move
* failure breakdown by phase
* failure breakdown by move

V2 should extend these with progression-oriented metrics.

---

# Attempt Progression

Track phase reached across attempts.

Example:

```text
Attempt 1    Phase 1
Attempt 2    Phase 1
Attempt 3    Phase 2
Attempt 4    Phase 2
Attempt 5    Phase 3
Attempt 6    Phase 2
Attempt 7    Phase 3
Attempt 8    Victory
```

The frontend may visualize this as a simple progression chart.

Avoid overly complicated visualization libraries if a simple implementation is sufficient.

---

# Recent vs Historical Analytics

V2 should support a concept such as:

```text
All-Time
vs
Recent Attempts
```

Default recent window may be:

```text
Last 10 attempts
```

unless a better product reason emerges.

Example:

| Metric           | All-Time | Last 10 |
| ---------------- | -------: | ------: |
| Phase 1 Failures |       10 |       1 |
| Phase 2 Failures |       15 |       4 |
| Phase 3 Failures |        7 |       5 |

This helps identify changing bottlenecks.

---

# Failure Trend

The application may compare failure counts over time.

Example:

```text
Floating Passage

All-Time Failures:
12

Last 10 Attempts:
2
```

Acceptable interpretation:

> Recorded failures attributed to Floating Passage are less common recently.

Do NOT automatically interpret this as:

```text
Floating Passage success rate increased to X%.
```

The application does not know how many times the move occurred.

---

# First Victory

Where useful, track:

```text
Attempts Until First Victory
```

This can be calculated from chronological attempt history.

Avoid storing derived values redundantly unless there is a performance reason.

---

# Game-Level Sekiro Dashboard

V2 should introduce an overall Sekiro analytics view.

This is one of the main product upgrades from V1.

Potential metrics:

```text
Bosses Attempted
Bosses Defeated
Total Attempts
Most Practiced Boss
Boss Requiring Most Attempts
Recent Practice Activity
```

Example:

```text
Sekiro Practice Dashboard

Bosses Attempted      6
Bosses Defeated       4
Total Attempts      143

Most Practiced Boss
Genichiro Ashina

Boss Requiring Most Attempts
Owl (Father)
```

---

# Boss Comparison

The Sekiro dashboard may include:

| Boss             | Attempts | Best Result | Defeated |
| ---------------- | -------: | ----------- | -------- |
| Genichiro Ashina |       24 | Victory     | Yes      |
| Guardian Ape     |       18 | Victory     | Yes      |
| Owl (Father)     |       31 | Phase 2     | No       |
| Isshin           |       14 | Phase 3     | No       |

Do not invent a universal boss difficulty ranking.

Any "hardest boss" metric must be clearly defined from the player's own attempt data.

For example:

```text
Boss Requiring Most Attempts
```

is more precise than:

```text
Hardest Boss
```

unless the definition is explicitly shown.

---

# Search and Filtering

As boss coverage expands, the boss selection experience may include:

```text
Search Boss...
```

Suggested filters:

```text
All
Attempted
Not Attempted
Defeated
Not Defeated
```

Keep filtering lightweight.

Do not build a generic search platform.

---

# Frontend Structure

The current frontend structure should remain simple and explicit.

Preferred conceptual structure:

```text
frontend/src/
├── api/
├── components/
├── pages/
├── types/
└── App.tsx
```

V2 may introduce an additional page:

```text
Sekiro Dashboard
Boss Selection / Browse
Boss Dashboard
```

Avoid turning every dashboard section into a separate route unless the UX benefits.

---

# Boss Dashboard Priority

The boss dashboard should prioritize:

```text
Boss Summary
↓
Record Attempt
↓
Progress Analytics
↓
Recent Attempts
↓
Boss Moveset Reference
```

This remains an analytics application.

It should not become primarily a Wiki.

---

# Frontend Type Safety

Continue using explicit TypeScript domain types.

Examples:

```text
BossSummary
Boss
BossPhase
BossMove
Attempt
BossAnalytics
SekiroAnalytics
ProgressionPoint
```

Avoid `any`.

Keep frontend types synchronized with backend response models.

---

# API Client

Continue centralizing backend calls.

Prefer:

```text
frontend/src/api/
```

rather than raw fetch calls inside many components.

Potential V2 functions:

```text
getBosses()
getBossById()
createAttempt()
getBossAttempts()
getBossAnalytics()
getSekiroAnalytics()
```

---

# Backend Structure

A reasonable V2 backend structure is:

```text
backend/
└── app/
    ├── main.py
    │
    ├── models/
    │   ├── db/
    │   └── schemas/
    │
    ├── routers/
    │   ├── bosses.py
    │   ├── attempts.py
    │   └── analytics.py
    │
    ├── services/
    │   ├── boss_service.py
    │   ├── attempt_service.py
    │   └── analytics_service.py
    │
    ├── db/
    │   ├── session.py
    │   └── base.py
    │
    └── ...
```

Exact folder names may differ.

Do not reorganize the entire repository merely to match this example if the existing layout is already clear.

---

# Service Layer

Prefer:

```text
Router
   ↓
Service
   ↓
Database
```

Route handlers should primarily:

1. receive input
2. validate request parameters
3. call application logic
4. return response models

Analytics calculations should remain outside route handlers.

---

# Database Session Management

Database session lifecycle should be explicit and safe.

Avoid:

* long-lived global sessions
* silently swallowed transaction failures
* manual transaction handling scattered across route handlers

Use clear FastAPI dependency patterns or equivalent clean session management.

---

# Query Efficiency

V2 remains a small application.

Do not prematurely optimize database queries.

However, avoid obvious issues such as:

* loading the entire attempts table when only one boss is needed
* N+1 queries caused by careless relationship loading
* repeated identical queries inside loops

Only introduce indexing or query optimization when the access pattern justifies it.

---

# V2 Testing Strategy

Testing should focus on product behavior and database correctness.

---

## Existing API Behavior

Continue testing:

```text
GET /health
GET /api/bosses
GET /api/bosses/{boss_id}
POST /api/bosses/{boss_id}/attempts
GET /api/bosses/{boss_id}/attempts
GET /api/bosses/{boss_id}/analytics
```

---

## Database Tests

Add tests for:

* boss persistence
* phase relationships
* move relationships
* attempt persistence
* nullable failure moves
* invalid boss references
* invalid phase / move combinations

---

## Migration Tests

Verify that:

```text
Alembic upgrade
```

can create the expected schema from a clean database.

Where practical, test V1 data import independently.

---

## Analytics Tests

Analytics tests should use controlled datasets.

Example:

```text
Attempt 1 → Phase 1 → Thrust
Attempt 2 → Phase 2 → Floating Passage
Attempt 3 → Phase 2 → Floating Passage
Attempt 4 → Phase 3 → Lightning
```

Expected:

```text
main bottleneck = Phase 2
most common failure move = Floating Passage
```

Progression logic should also be tested with deterministic histories.

---

# Integration Testing

V2 should contain at least one meaningful end-to-end backend integration workflow.

Example:

```text
Create Boss Data
      ↓
Create Attempt
      ↓
Persist to PostgreSQL
      ↓
Read Attempt History
      ↓
Request Analytics
      ↓
Verify Updated Metrics
```

This is more valuable than testing implementation details individually.

---

# CI

GitHub Actions should validate both backend and frontend.

Conceptually:

```text
Pull Request / Push
        ↓
Backend Checks
├── install dependencies
├── pytest
└── database tests

Frontend Checks
├── npm ci
├── typecheck
├── lint
└── build
```

Only include commands that actually exist in the project.

Do not invent package scripts solely because they are listed here.

---

# V2 CD / Deployment

V2 may introduce:

```text
dev
 ↓
Staging

main
 ↓
Production
```

Conceptual workflow:

```text
feature/*
    ↓
Pull Request
    ↓
dev
    ↓
CI
    ↓
Staging Deployment

main
    ↓
CI
    ↓
Production Deployment
```

A separate staging Git branch is not required.

---

# Stable Public Demo

By the end of V2, the application should ideally have:

```text
stable public URL
```

that can be shared without requiring the developer's local machine to remain online.

Cloudflare Tunnel may still be used for local testing.

A portfolio release should preferably use stable hosting.

---

# Docker

Continue supporting Docker.

V2 Docker setup should account for:

```text
frontend
backend
postgres
```

Local development may use:

```text
docker compose
```

Do not introduce Kubernetes simply to orchestrate three local services.

---

# Environment Configuration

Database URLs and deployment-specific configuration should use environment variables.

Do not commit:

* passwords
* production credentials
* secret keys
* private database URLs

Provide an example environment file where useful:

```text
.env.example
```

Do not commit real `.env` secrets.

---

# V2 Milestones

Implement V2 incrementally.

Each milestone should leave the project in a working state.

---

## Milestone 1 — PostgreSQL Foundation

### Goal

Replace JSON persistence with a relational persistence foundation.

### Tasks

* add PostgreSQL development environment
* add SQLAlchemy
* add Alembic
* configure database connection
* configure database session handling
* define initial relational schema
* create first Alembic migration
* verify schema can be created from scratch

### Completion Criteria

```text
FastAPI
   ↓
SQLAlchemy
   ↓
PostgreSQL
```

is working locally.

Existing APIs do not yet need every V2 feature, but database infrastructure must be stable.

---

## Milestone 2 — V1 Data Migration

### Goal

Move existing boss and attempt data into PostgreSQL.

### Tasks

* create V1 JSON import script
* migrate Genichiro
* migrate phases
* migrate moves
* migrate attempt history
* validate relationships
* preserve existing API behavior
* remove application dependency on JSON persistence once migration is validated

### Completion Criteria

The existing V1 workflow works against PostgreSQL:

```text
Choose Genichiro
      ↓
View Dashboard
      ↓
Record Attempt
      ↓
PostgreSQL
      ↓
History + Analytics
```

The frontend should require minimal or no persistence-specific changes.

---

## Milestone 3 — Multi-Boss Support

### Goal

Validate the relational model across several different Sekiro bosses.

### Tasks

* add approximately 5–8 major bosses
* add phase structures
* add representative moves
* verify attempt creation for every supported boss
* verify analytics remain boss-specific
* eliminate any Genichiro-specific application logic

### Completion Criteria

The same code path supports multiple bosses without special-case logic.

---

## Milestone 4 — Richer Boss Metadata

### Goal

Improve the moveset reference enough to support better failure identification.

### Potential Fields

* move type
* description
* telegraph
* recommended response
* common mistakes
* source name
* source URL

### Completion Criteria

Boss moves contain useful practice context without turning the application into a Wiki clone.

---

## Milestone 5 — Progression Analytics

### Goal

Answer:

> Am I improving over time?

### Tasks

* model chronological attempt progression
* expose phase progression data
* implement recent-attempt window
* compare recent vs all-time failure patterns
* calculate attempts until first victory
* add relevant backend tests

### Completion Criteria

A boss dashboard can show meaningful change over time, not only lifetime totals.

---

## Milestone 6 — Progression UI

### Goal

Make the new analytics understandable visually.

### Tasks

* add attempt progression visualization
* add all-time vs recent comparison
* display recent failure patterns
* retain existing V1 metrics
* preserve mobile usability

### Completion Criteria

A user should be able to inspect a boss page and quickly understand whether recent attempts differ from older ones.

---

## Milestone 7 — Overall Sekiro Dashboard

### Goal

Move from boss-specific analytics to game-level analytics.

### Tasks

Add metrics such as:

```text
Bosses Attempted
Bosses Defeated
Total Attempts
Most Practiced Boss
Boss Requiring Most Attempts
Recent Practice Activity
```

Add a boss comparison view.

### Completion Criteria

The user can understand their overall Sekiro practice history without opening every boss individually.

---

## Milestone 8 — Search and Filtering

### Goal

Keep boss discovery usable as the dataset expands.

### Tasks

Potentially add:

```text
Search Boss

All
Attempted
Not Attempted
Defeated
Not Defeated
```

### Completion Criteria

Users can quickly locate relevant bosses without unnecessary UI complexity.

---

## Milestone 9 — Integration Testing and CI Hardening

### Goal

Protect the full PostgreSQL-backed workflow.

### Tasks

* database-backed API tests
* analytics tests
* migration tests
* one complete attempt integration test
* backend CI
* frontend CI
* verify Docker build in CI if useful

### Completion Criteria

A broken persistence or analytics change should normally be detected before merging into `dev`.

---

## Milestone 10 — Stable Deployment

### Goal

Produce a reliable public V2 demo.

### Tasks

* production PostgreSQL configuration
* environment configuration
* Docker deployment
* staging deployment if useful
* production deployment
* fixed public URL
* verify mobile access
* update README screenshots and setup instructions

### Completion Criteria

The application can be opened from a stable public URL and the complete V2 workflow functions correctly.

---

# V2 Development Order

Recommended sequence:

```text
1. PostgreSQL Foundation

2. SQLAlchemy Models

3. Alembic Migration

4. V1 JSON → PostgreSQL Migration

5. Verify Existing V1 APIs

6. Multi-Boss Support

7. Richer Boss Metadata

8. Progression Analytics Backend

9. Progression Analytics Frontend

10. Overall Sekiro Dashboard

11. Search / Filter

12. Integration Tests

13. CI Hardening

14. Stable Deployment

15. Release v2.0.0
```

Do not start several major milestones simultaneously unless there is a clear dependency reason.

---

# V2 Success Criteria

V2 is complete when a user can:

```text
Open Sekiro Dashboard
        ↓
View Multiple Bosses
        ↓
See Overall Sekiro Progress
        ↓
Choose a Boss
        ↓
View Attempt History
        ↓
View Progression Analytics
        ↓
Compare Recent vs Historical Performance
        ↓
Record New Attempt
        ↓
Persist to PostgreSQL
        ↓
Analytics Update
```

and the system can support multiple bosses through the same architecture.

---

# Release Boundary

Once the V2 success criteria are complete:

```text
dev
 ↓
main
 ↓
v2.0.0
```

Stop V2 development.

Do not delay the V2 release by introducing V3 features.

---

# Future Versions

## V3 — Personalized Practice Coach

Core question:

> What should I practice next?

Potential additions:

* authentication
* user accounts
* user-owned attempts
* long-term player profiles
* practice goals
* personalized recommendations

These are NOT V2 requirements.

---

## V4 — Gameplay Analysis

Core question:

> What actually happened during the fight?

Potential additions:

* gameplay video upload
* move occurrence annotation
* player response annotation
* computer vision
* automatic move detection
* true per-move success rates

These are NOT V2 requirements.

---

## V5 — Multi-Game Analytics

Core question:

> Can the same analysis work across games?

Potential additions:

* Black Myth: Wukong
* shared multi-game domain model
* game-specific combat mechanics
* cross-game analytics

These are NOT V2 requirements.

---

# Important Instructions for Claude

When working in this repository:

1. Treat V1 as completed.
2. Treat V2 as the current active development scope.
3. Preserve the lightweight manual attempt-recording workflow.
4. Do not add detailed manual combat telemetry.
5. Continue supporting `Other` and `Not Sure`.
6. Prefer structured move IDs over free-text move names.
7. Keep analytics derived from attempt data where practical.
8. Do not invent success rates without occurrence denominators.
9. Migrate persistence from JSON to PostgreSQL cleanly.
10. Use SQLAlchemy for relational persistence.
11. Use Alembic for schema migrations.
12. Review generated migrations before applying them.
13. Preserve frontend API contracts where practical.
14. Do not silently rewrite working frontend behavior during the database migration.
15. Keep database access outside route handlers where practical.
16. Keep analytics logic outside route handlers.
17. Avoid unnecessary repository/factory/framework abstractions.
18. Expand boss coverage only after the PostgreSQL-backed V1 workflow is stable.
19. Do not create large amounts of low-quality boss data.
20. Do not invent Sekiro mechanics when uncertain.
21. Keep game knowledge traceable to sources where practical.
22. Do not add authentication in V2.
23. Do not add video analysis in V2.
24. Do not add Black Myth: Wukong in V2.
25. Do not add Redis, Kafka, Kubernetes, or microservices without a concrete requirement.
26. Prefer incremental changes over large rewrites.
27. Preserve working functionality after every milestone.
28. Add tests for meaningful behavior, not arbitrary coverage targets.
29. Keep derived analytics semantically honest.
30. Stop V2 once the defined V2 success criteria are complete.

---

# Current Milestone Rule

Before implementing a new feature, identify which V2 milestone it belongs to.

If the feature does not clearly belong to:

```text
PostgreSQL Migration
Multi-Boss Support
Richer Boss Data
Progression Analytics
Sekiro Dashboard
Search / Filtering
Testing / CI
Deployment
```

check whether it actually belongs to V3, V4, or V5 before adding it.

The goal of V2 is not to maximize feature count.

The goal is to turn the completed V1 MVP into a structured, maintainable, multi-boss Sekiro analytics application and then release `v2.0.0`.