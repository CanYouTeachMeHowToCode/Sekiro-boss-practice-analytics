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

## V2 — Completed

V2 delivered the structured, multi-boss Sekiro analytics application:

* PostgreSQL persistence with SQLAlchemy and Alembic (Plan B schema: moves stored once per boss, linked to phases through `phase_moves`)
* 8 bosses: Genichiro Ashina, Owl (Father), Lady Butterfly, Guardian Ape, Corrupted Monk, True Corrupted Monk, Great Shinobi Owl, Isshin, the Sword Saint
* richer move metadata with a source page for each boss
* progression analytics: progression chart, all-time vs. last 10 attempts, attempts until first victory
* an overall Sekiro dashboard at `/`, with the boss list at `/bosses`
* four required CI jobs: backend, frontend, integration, docker
* local deployment with Docker Compose

Milestone 8 (search and filtering) was skipped. Milestone 10 (public deployment) moved into V3 as Milestone 6.

Released as `v2.0.0`.

## V3 — In Progress

Completed so far:

* **Milestone 1 — Accounts and Authentication:** `users` and `user_sessions` tables, argon2 password hashing, server-side sessions in an httpOnly SameSite=Lax cookie (only a SHA-256 hash of the token is stored), register / login / logout / me endpoints, login and register pages, and a welcome page with the boss list for visitors. Registration is open to everyone.
* **Milestone 2 — User-Owned Attempts:** `attempts.user_id` foreign key. It is nullable for now: attempts from before accounts existed stay ownerless and hidden until `python -m scripts.claim_attempts <username>` assigns them.
* **Milestone 3 — Per-User Analytics and Isolation:** attempt history, boss analytics, progression and the Sekiro dashboard only cover the logged-in user, with isolation tests at the API and service level.

Next: Milestone 4 (bilingual interface), then Milestone 5 (content completion and moveset review), then Milestone 6 (public deployment), which also makes `attempts.user_id` NOT NULL.

---

# Current Development Focus: V3 — Personalized Practice Coach

V3 answers:

> **What should I practice next?**

V3 scope is:

```text
User accounts
+
Bilingual interface (English / 中文)
+
Content completion (all main bosses, reviewed movesets)
+
Public deployment
+
Rule-based practice recommendations
```

The bilingual interface and content completion were added after Milestones 1–3, so the public release covers every main boss in both English and Chinese. Move video or GIF references were considered and deferred (Milestone 9).

Long-term tracking and practice goals are NOT part of V3. Long-term progression is already covered by V2's progression chart, recent vs. all-time comparisons and Sekiro dashboard. Practice goals were considered and dropped.

## Precedence

The V2 sections later in this file still describe how the existing code is built, and their engineering rules still apply: SQLAlchemy, reviewed Alembic migrations, the service layer, honest analytics, the lightweight attempt form, source-traceable boss data, and testing against PostgreSQL.

Where a V2 section conflicts with this V3 section, this section wins. In particular, V2's non-goals of "user accounts", "authentication", "personalized multi-user histories" and "recommendation engines" are lifted only as far as the V3 milestones below require.

## V3 Product Principles

* Recording an attempt stays as quick as in V2: result, phase reached, failure move / `Other` / `Not Sure`, optional notes. Accounts must not add fields to that form.
* Boss, phase and move data stays global and shared by all users. Only attempts belong to users.
* Every analytics and recommendation query is scoped to the current user. A user must never see or write another user's attempts.
* Recommendations are derived only from the user's own attempt records. There is no in-game telemetry.
* Every recommendation shows the evidence behind it, as counts from the user's attempts.
* Do not present recommendations as success rates, skill scores or difficulty ratings. The data cannot support them.

## V3 Non-Goals

Do NOT introduce the following in V3 unless explicitly requested:

* OAuth or third-party login
* password reset emails or other email infrastructure
* user roles, admin panels, or teams
* social features: sharing, following, leaderboards
* practice goals
* machine learning or LLM-generated recommendations
* gameplay video, computer vision, or combat telemetry (V4)
* Black Myth: Wukong or multi-game UI (V5)
* Redis, message queues, Kubernetes, or microservices without a demonstrated need

## V3 Milestones

Implement V3 incrementally. Each milestone should leave the project in a working state.

### Milestone 1 — Accounts and Authentication (Completed)

* add a `users` table through an Alembic migration
* hash passwords with argon2
* register, log in, log out
* authenticate with an httpOnly session cookie. The frontend and backend are same-origin through nginx, so JWTs are not needed.
* add a login / register page in the frontend
* boss data remains browsable without logging in; recording attempts and viewing analytics require login

### Milestone 2 — User-Owned Attempts (Completed)

* add `attempts.user_id` as a foreign key to `users`, through a reviewed Alembic migration
* migrate existing attempts to the owner's account explicitly. Do not silently delete or orphan them.
  * Done by making `attempts.user_id` nullable: pre-account attempts stay ownerless and hidden from everyone until `python -m scripts.claim_attempts <username>` assigns them. Milestone 6 makes the column NOT NULL.
* record the current user on every new attempt
* read attempt history for the current user only

### Milestone 3 — Per-User Analytics and Isolation (Completed)

* scope boss analytics, progression and the Sekiro dashboard to the current user
* add tests proving users cannot read or write each other's attempts, at both the API and service level
* keep the V2 analytics definitions unchanged apart from the user scope

### Milestone 4 — Bilingual Interface (English / 中文)

Users choose English or Chinese, and each language shows only its own text; the two are never mixed on one page.

* a language switch in the nav bar
  * logged-in users: the choice is saved in their account (a `users` column) and follows them across devices
  * visitors: the choice is kept in the browser; the first visit follows the browser language
* all interface text in both languages, through a small in-house dictionary and `t()` helper; no i18n framework is needed for two languages
* Chinese versions of all boss content for the existing bosses: boss locations, phase names, move names, descriptions, telegraphs, counters and common mistakes
* Chinese move names: the name used by a Chinese Sekiro wiki where one exists (recorded with its page), otherwise a translation (marked as such in the data, never presented as official)
* Chinese descriptions are translations of the English, wiki-sourced text; the Chinese moveset shows one note saying so instead of a marker on every move
* the API returns both languages and the frontend picks one, so existing clients keep working
* the user reviews all Chinese text manually
* analytics definitions do not change with the language; only the displayed text does

### Milestone 5 — Content Completion and Moveset Review

Comes before public deployment so the public release is complete.

* add the remaining main bosses, each in both languages: Gyoubu Masataka Oniwa, Headless Ape, Demon of Hatred, Genichiro (Way of Tomoe), Emma the Gentle Blade, Isshin Ashina, Folding Screen Monkeys, Divine Dragon, Inner Father, Inner Genichiro, Inner Isshin. Mini-bosses stay out of scope.
* for new bosses, compare the Fextralife and Fandom wikis; every conflict between them, in English or Chinese, goes to the user for review
* review the movesets of the existing bosses; the user may remove or edit moves
  * the seed sync never deletes a move on its own, because attempts may reference it. Removing a move that has recorded attempts needs an explicit decision about those attempts (for example, keep the move but hide it from new attempts, or reassign the attempts) before it is deleted.
* follow the existing data rules: sourced from a wiki, boss-level `source_name` / `source_url`, `telegraph` and `common_mistakes` only when the source states them, no placeholder moves

### Milestone 6 — Public Deployment

Moved from V2 Milestone 10. It comes after the account milestones because accounts are what make a public instance safe, and after the bilingual and content milestones so the public release is complete. See "Public Deployment" below for the work involved.

### Milestone 7 — Practice Recommendations

* rule-based and explainable, derived only from the user's attempt records
* candidate signals include:
  * the recent bottleneck phase
  * the most common recorded failure move among attempts that reached that move's phases
  * undefeated bosses the user has practiced recently
* every recommendation includes its evidence, for example "6 of your last 10 attempts ended in Phase 2; 4 of those were Floating Passage"
* failure counts for a move only count attempts that reached a phase containing that move, so dying earlier cannot make a move look "improved"
* recommendations are shown in both languages
* the exact rules are decided with the user before implementation

### Milestone 8 — Integration Testing, CI and Release

* an end-to-end test: register → record attempts → analytics → recommendations
* extend CI to cover authentication and user isolation
* verify the production deployment workflow
* release `v3.0.0`

### Milestone 9 — Move Video References (Deferred)

Short clips or GIFs showing each move, so players can identify it more easily.

Deferred because of the effort (clips for every move), hosting size, and copyright: wiki-hosted GIFs must not be hotlinked or copied, and game footage belongs to FromSoftware. A lighter option to consider first is a timestamped YouTube link per move.

Not required for `v3.0.0`.

## V3 Success Criteria

V3 is complete when a user can:

```text
Open the public URL
        ↓
Register / Log In
        ↓
Record Attempts
        ↓
See Only Their Own History and Analytics
        ↓
Get Practice Recommendations with Evidence
```

Once these criteria are met, merge `dev` into `main`, release `v3.0.0`, and stop V3 development. Do not delay the release by adding V4 features.

---

# V2 Scope (Completed)

This section records what V2 covered:

> **V2 — Structured Sekiro Analytics Platform**

V2 evolved the JSON-backed MVP into a structured, multi-boss Sekiro analytics application.

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
local Docker deployment
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
* stronger integration testing
* a reliable local deployment with Docker Compose (public hosting moved into V3 Milestone 6)

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

* Docker Compose, run locally

V2 has no public hosting and no staging or production environments. Public deployment moved into V3 Milestone 6; see "Public Deployment (V3 Milestone 6)".

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
      ├── Phase
      └── Move

Phase ←── many-to-many ──→ Move
```

A move belongs to a boss and may appear in several of that boss's phases.

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
phase_moves
attempts
```

Avoid adding tables solely for hypothetical future requirements.

`phase_moves` is not hypothetical: the existing boss data already reuses the same move across multiple phases (for example, Owl (Father)'s Shadowfall appears in both phases).

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
name_zh
location
source_name
source_url
```

`name_zh` is the official Simplified Chinese name. From V3 Milestone 4 the whole interface and all boss content exist in English and Chinese; see Milestone 4.

`source_name` and `source_url` record where the boss's phase and move data came from. All moves of a boss share this source.

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
boss_id
slug
name
move_type
description
telegraph
counter
common_mistakes
```

Moves do not have their own source fields; they use their boss's `source_name` and `source_url`. Add move-level sources only if a move's data ever comes from a different page than its boss.

Only fill `telegraph` and `common_mistakes` from what the source explicitly states. Leave them null rather than inferring them.

Relationship:

```text
Boss
 1
 ↓
Many Moves
```

Each move is stored once per boss, even if it appears in several phases. `slug` should be unique within a boss.

Not every optional field must be populated immediately.

Do not block V2 development on complete moveset documentation.

---

## Phase Moves

Join table recording which moves appear in which phases.

Conceptual fields:

```text
boss_phase_id
move_id
```

Relationship:

```text
Phase
 Many
 ↕
Many Moves
```

Example (Owl (Father)):

| boss_phase_id | move_id | meaning |
| ------------- | ------- | ------- |
| Phase 1 | Shadowfall | Shadowfall appears in Phase 1 |
| Phase 2 | Shadowfall | Shadowfall also appears in Phase 2 |
| Phase 2 | Owl Teleport | Owl Teleport only appears in Phase 2 |

Because a move is stored once, an attempt that failed to Shadowfall always references the same `failure_move_id`, regardless of the phase. Phase information comes from `phase_reached`.

The phase and the move must belong to the same boss.

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

`id` is an integer primary key. The API exposes it as a string so the existing frontend `Attempt.id: string` contract does not change.

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
* move must reference an existing boss
* phase_moves entries must reference an existing phase and an existing move
* attempt must reference an existing boss
* failure move must reference an existing move when present

Application-level validation should still ensure that:

* the selected phase belongs to the selected boss
* the selected failure move belongs to the selected boss
* a phase_moves entry never links a phase and a move from different bosses
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

Each boss records the source of its phase and move data:

```text
source_name
source_url
```

Source metadata is kept at the boss level because every move currently comes from its boss's page.

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

Not planned. Sekiro has roughly 20 bosses even including mini-bosses, so every boss fits on one page, and the Sekiro Dashboard's boss comparison table already shows each boss's attempts and defeat status. See Milestone 8.

Revisit only if the boss list grows well beyond what fits on one page.

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

# V2 CI / Deployment

V2 has continuous integration but no continuous deployment.

```text
feature/*
    ↓
Pull Request
    ↓
CI (backend, frontend, integration, docker)
    ↓
dev
    ↓
main
    ↓
v2.0.0 (run locally with Docker Compose)
```

`dev` and `main` are protected: all four CI jobs must pass before a pull request can merge.

---

# Public Deployment (V3 Milestone 6)

V2 ran locally only. Public deployment was moved into V3 because:

* V2 has no authentication, so a public instance would let anyone record attempts into the only attempt history
* V3 Milestones 1–3 add user accounts and per-user data, which solves that problem directly

Until Milestone 6 is done, a Cloudflare Tunnel to the local instance is acceptable for temporary remote access, such as from a phone away from home.

The work involved:

* a production compose configuration that exposes only the reverse proxy, not the PostgreSQL or backend ports
* HTTPS, for example with Caddy's automatic certificates
* secrets supplied through environment variables; secure, SameSite session cookies
* rate limiting on login and registration
* scheduled `pg_dump` backups of attempt data, with a restore tested at least once
* make `attempts.user_id` NOT NULL through a migration. Milestone 2 left it nullable so pre-account attempts could stay ownerless until claimed with `scripts.claim_attempts`. The migration should fail loudly if any ownerless attempts remain.
* deployment from `main` through GitHub Actions
* choosing a host and a domain. Free tiers such as Oracle Cloud Always Free may reclaim idle instances; a small paid VPS is more predictable.
* setup documentation in the README

V4 gameplay analysis (video storage, computer vision) will likely need different infrastructure, so keep this deployment simple rather than building for V4.

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

## Milestone 1 — PostgreSQL Foundation (Completed)

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
* run database tests against a PostgreSQL service in backend CI

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

## Milestone 2 — V1 Data Migration (Completed)

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

## Milestone 3 — Multi-Boss Support (Completed)

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

## Milestone 4 — Richer Boss Metadata (Completed)

### Goal

Improve the moveset reference enough to support better failure identification.

### Potential Fields

* move type
* description
* telegraph
* counter
* common mistakes
* source name
* source URL

### Completion Criteria

Boss moves contain useful practice context without turning the application into a Wiki clone.

---

## Milestone 5 — Progression Analytics (Completed)

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

## Milestone 6 — Progression UI (Completed)

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

## Milestone 7 — Overall Sekiro Dashboard (Completed)

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

## Milestone 8 — Search and Filtering (Skipped)

### Decision

Skipped. Sekiro has roughly 20 bosses even including mini-bosses, so the full list fits on one page and search adds little. The Sekiro Dashboard's boss comparison table (Milestone 7) already shows each boss's attempts and defeat status.

This does not affect the V2 success criteria, which never required search or filtering.

Do not add search or filtering unless the boss list grows well beyond what fits on one page.

---

## Milestone 9 — Integration Testing and CI Hardening (Completed)

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

## Milestone 10 — Stable Deployment (Moved to V3 Milestone 6)

### Decision

Public deployment moved into V3 as Milestone 6. See "Public Deployment (V3 Milestone 6)" for the reasons and the work involved.

### What V2 Still Includes

* running the full stack locally with `docker compose up`
* local setup instructions in the README
* LAN access from other devices, such as a phone on the same network

The V2 success criteria do not require public hosting.

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

11. Search / Filter (skipped, see Milestone 8)

12. Integration Tests

13. CI Hardening

14. Stable Deployment (moved to V3 Milestone 6, see Milestone 10)

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

Current development focus. See "Current Development Focus: V3" near the top of this file.

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

These are NOT V3 requirements.

---

## V5 — Multi-Game Analytics

Core question:

> Can the same analysis work across games?

Potential additions:

* Black Myth: Wukong
* shared multi-game domain model
* game-specific combat mechanics
* cross-game analytics

These are NOT V3 requirements.

---

# Important Instructions for Claude

When working in this repository:

1. Treat V1 and V2 as completed.
2. Treat V3 as the current active development scope, limited to accounts, the bilingual interface, content completion, public deployment and rule-based practice recommendations.
3. Preserve the lightweight manual attempt-recording workflow; accounts must not add fields to it.
4. Do not add detailed manual combat telemetry.
5. Continue supporting `Other` and `Not Sure`.
6. Prefer structured move IDs over free-text move names.
7. Keep analytics and recommendations derived from attempt data.
8. Do not invent success rates without occurrence denominators.
9. Show the evidence behind every recommendation.
10. Scope every attempt, analytics and recommendation query to the current user.
11. Keep boss, phase and move data global.
12. Never store plain-text passwords; hash them with argon2.
13. Use SQLAlchemy for relational persistence.
14. Use Alembic for schema migrations, and review generated migrations before applying them.
15. Migrate existing attempts to a user explicitly; never silently drop them.
16. Preserve frontend API contracts where practical; change frontend types and clients together when a contract must change.
17. Keep database access and analytics logic outside route handlers.
18. Avoid unnecessary repository/factory/framework abstractions.
19. Do not create large amounts of low-quality boss data.
20. Do not invent Sekiro mechanics when uncertain, and keep game knowledge traceable to sources. Chinese move names come from a Chinese wiki where one exists; otherwise they are marked as translations. Chinese descriptions are translations of the sourced English text.
21. Do not commit secrets, production credentials or private database URLs.
22. Do not add OAuth, email infrastructure, roles, social features or practice goals in V3.
23. Do not add video analysis (V4) or Black Myth: Wukong (V5).
24. Do not add Redis, Kafka, Kubernetes, or microservices without a concrete requirement.
25. Prefer incremental changes over large rewrites, and preserve working functionality after every milestone.
26. Add tests for meaningful behavior, including user isolation, not arbitrary coverage targets.
27. Stop V3 once the defined V3 success criteria are complete.

---

# Current Milestone Rule

Before implementing a new feature, identify which V3 milestone it belongs to.

If the feature does not clearly belong to:

```text
Accounts and Authentication
User-Owned Attempts
Per-User Analytics and Isolation
Bilingual Interface
Content Completion and Moveset Review
Public Deployment
Practice Recommendations
Testing / CI / Release
```

check whether it actually belongs to V4 or V5, or was deliberately dropped from V3, before adding it.

The goal of V3 is not to maximize feature count.

The goal is to let each player keep their own practice history on a public instance and get honest, evidence-backed practice recommendations, and then release `v3.0.0`.
