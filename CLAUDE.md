# Sekiro Boss Practice Analytics

## Project Overview

Sekiro Boss Practice Analytics is a web application for tracking and analyzing player attempts against bosses in *Sekiro: Shadows Die Twice*.

The core problem is simple:

After repeatedly fighting a difficult boss, players usually remember that they died, roughly how far they reached, and sometimes which move killed them. However, they usually do not have a structured way to determine:

* which boss moves cause the most deaths
* which phase is the main bottleneck
* whether they are progressing further over time
* how many attempts it takes to defeat a boss

V1 turns this lightweight, manually recorded information into useful failure analytics.

This repository is currently focused on **V1 only**.

---

# V1 Product Definition

V1 is a:

> **Manual boss-attempt tracking and failure analytics tool.**

Players record how far they reached and what ended each attempt.

The application uses attempt history to identify:

* the player's most common failure moves
* the player's main bottleneck phase
* progression across attempts
* number of attempts
* whether the boss has been defeated

V1 is NOT intended to measure every action performed during a fight.

The user should not be expected to remember detailed combat statistics such as:

* every attack they were hit by
* total deflect success rate
* number of successful Mikiri Counters
* number of times each move appeared
* damage taken from each move
* detailed per-move performance

Those require gameplay observation or video analysis and belong to future versions.

---

# Core User Flow

The primary V1 user flow is:

```text
Open Web App
    ↓
Choose Boss
    ↓
Boss Dashboard
    ↓
Record Attempt
    ↓
Select Result
    ↓
Select Phase Reached
    ↓
Select What Ended the Attempt
    ↓
Save
    ↓
Attempt History + Analytics Update
```

For example:

```text
Sekiro Boss Practice Analytics

Choose a Boss

[ Genichiro Ashina ]
[ Lady Butterfly ]
[ Guardian Ape ]
```

The initial implementation should start with only one boss:

```text
Genichiro Ashina
```

Additional bosses should only be added after the complete V1 workflow works end-to-end.

---

# Boss Dashboard

After selecting a boss, the user should arrive at a single primary boss dashboard.

Example:

```text
Genichiro Ashina
Ashina Castle

Attempts: 12
Best Result: Phase 3
Defeated: No

[ + Record Attempt ]


Your Analytics

Main Bottleneck:
Phase 2

Most Common Failure:
Floating Passage

Failure Breakdown:

Floating Passage    5
Thrust Attack       3
Lightning           2
Other               1


Recent Attempts

#12  Phase 3  Lightning Attack
#11  Phase 2  Floating Passage
#10  Phase 2  Floating Passage


Boss Moveset

Phase 1
- Thrust Attack
- Sweep Attack
- Floating Passage

Phase 2
...

Phase 3
- Lightning Attack
...
```

The Boss Dashboard combines three types of information:

```text
Action
→ Record Attempt

Personal Analytics
→ What the player struggles with

Boss Reference
→ Phases and moveset
```

Do not unnecessarily split these into many separate pages during V1.

---

# Record Attempt

Recording an attempt is the most important interaction in V1.

It should be fast and require minimal memory from the player.

A player who just finished a boss attempt should ideally be able to record it in approximately a few selections.

Example:

```text
Record Attempt — Genichiro Ashina

Result

(●) Failed
( ) Victory


Phase Reached

[ Phase 2 ▼ ]


What ended this attempt?

[ Floating Passage ▼ ]

Options may include:

- known boss moves
- Other
- Not Sure


Notes

[ Optional ]


[ Save Attempt ]
```

---

# What Users Are Expected to Remember

V1 assumes users can reasonably remember:

1. Which boss they fought.
2. Whether they won or lost.
3. Approximately which phase they reached.
4. If known, which move caused the final failure.
5. Optionally, a short note about the attempt.

V1 must NOT assume users accurately remember their performance against every move during an entire fight.

---

# Unknown Failure Cause

Users may not always know exactly which move killed them.

Therefore:

```text
What ended this attempt?
```

must support:

```text
Not Sure
Other
```

A failure move must NOT be required.

An attempt such as:

```text
Boss:
Genichiro

Result:
Failed

Phase Reached:
Phase 2

Failure Cause:
Not Sure
```

is still valuable.

It contributes to phase analytics even if it cannot contribute to move-specific analytics.

Do not force users to guess a move simply to satisfy structured data requirements.

---

# Boss Moveset Purpose

The Boss Moveset is reference data.

Its purpose in V1 is NOT to ask the user to manually score their performance against every move.

The moveset serves three purposes.

## 1. Failure Identification

It helps players identify the move that ended their attempt.

For example:

```text
Floating Passage

Type:
Combo

Description:
Multi-hit sword combo.

Recommended Response:
Deflect the sequence.
```

The player may recognize:

```text
"That is the attack I died to."
```

and select it when recording an attempt.

---

## 2. Structured Analytics

Failure causes should use structured move IDs rather than arbitrary user-entered strings.

Prefer:

```text
floating-passage
```

instead of free-text variants such as:

```text
"floating combo"
"that long sword combo"
"the multi slash attack"
```

This allows attempts to be aggregated reliably.

---

## 3. Future Video Analysis Compatibility

V1:

```text
User manually selects:
Floating Passage
```

Future version:

```text
Gameplay analyzer detects:
Floating Passage
```

Both can ultimately reference:

```text
move_id = "floating-passage"
```

Design the move model so this future transition is possible.

Do NOT implement automatic detection in V1.

---

# V1 Core Features

Users should be able to:

1. Browse supported Sekiro bosses.
2. Select a boss.
3. View the boss dashboard.
4. View basic boss phases and moves.
5. Record a boss attempt.
6. Record whether the attempt ended in failure or victory.
7. Record the phase reached.
8. Optionally record the move that ended the attempt.
9. Select `Other` or `Not Sure` when appropriate.
10. Add an optional note.
11. View attempt history.
12. View failure breakdown by boss move.
13. View failure breakdown by phase.
14. Identify the main bottleneck phase.
15. Identify the most common known failure move.
16. View basic progression across attempts.

---

# V1 Non-Goals

Do NOT introduce the following unless explicitly requested:

* PostgreSQL
* MySQL
* SQLite
* SQLAlchemy
* Alembic
* Redis
* Authentication
* User accounts
* OAuth
* Kubernetes
* Microservices
* Message queues
* automated Wiki scraping
* game file unpacking
* game memory reading
* gameplay video upload
* computer vision
* machine learning
* automatic boss move detection
* automatic deflect detection
* automatic player action recognition
* detailed combat telemetry
* predictive recommendation systems

Do not implement future-version functionality prematurely.

---

# Tech Stack

## Backend

* Python
* FastAPI
* Pydantic

## Frontend

* React
* TypeScript
* Vite

## Persistence

V1 uses JSON files instead of a database.

Suggested structure:

```text
backend/app/data/
├── bosses.json
└── attempts.json
```

`bosses.json` contains relatively static boss knowledge.

`attempts.json` contains manually recorded player attempts.

V1 intentionally uses JSON because:

* only a few bosses are supported
* the dataset is small
* persistence requirements are simple
* the goal is to validate the full product workflow first

PostgreSQL may replace JSON in V2.

## Deployment

* Docker

Dockerization should be added after the application works locally end-to-end.

---

# High-Level Architecture

```text
Browser
   |
   v
React + TypeScript
   |
   | HTTP / JSON
   v
FastAPI
   |
   +-------------------+
   |                   |
   v                   v
bosses.json        attempts.json
```

The frontend should access application data only through FastAPI APIs.

Do not import backend JSON directly into React.

This keeps the frontend independent of the persistence implementation.

Future migration should be possible:

```text
V1

FastAPI
   ↓
JSON

        ↓

V2

FastAPI
   ↓
PostgreSQL
```

without significantly changing frontend API contracts.

---

# Core Data Model

V1 contains two categories of data.

## Game Knowledge

```text
Game
 └── Boss
      └── Phase
           └── Move
```

## Player Attempt Data

```text
Boss
 └── Attempt
      ├── Result
      ├── Phase Reached
      ├── Failure Move
      └── Optional Notes
```

Analytics are derived from attempt data.

---

# Boss Model

A boss should approximately follow:

```json
{
  "id": "genichiro-ashina",
  "name": "Genichiro Ashina",
  "game": "sekiro",
  "location": "Ashina Castle",
  "phases": [
    {
      "phase_number": 1,
      "name": "Phase 1",
      "moves": [
        {
          "id": "floating-passage",
          "name": "Floating Passage",
          "move_type": "combo",
          "description": "Multi-hit sword combo.",
          "recommended_response": "Deflect the sequence."
        }
      ]
    }
  ]
}
```

Optional move fields may include:

```text
description
telegraph
recommended_response
common_mistakes
notes
```

Avoid excessive data collection during initial development.

Do not invent boss mechanics or statistics when uncertain.

---

# Attempt Model

Keep an attempt intentionally small.

Approximate model:

```json
{
  "id": "attempt-001",
  "boss_id": "genichiro-ashina",
  "timestamp": "2026-08-24T21:00:00Z",
  "result": "failed",
  "phase_reached": 2,
  "failure_move_id": "floating-passage",
  "notes": ""
}
```

A failure with unknown cause:

```json
{
  "id": "attempt-002",
  "boss_id": "genichiro-ashina",
  "timestamp": "2026-08-24T21:15:00Z",
  "result": "failed",
  "phase_reached": 2,
  "failure_move_id": null,
  "failure_category": "not_sure",
  "notes": ""
}
```

A victory:

```json
{
  "id": "attempt-003",
  "boss_id": "genichiro-ashina",
  "timestamp": "2026-08-24T21:30:00Z",
  "result": "victory",
  "phase_reached": 3,
  "failure_move_id": null,
  "notes": ""
}
```

Do not add detailed fight telemetry fields to V1.

---

# Analytics Philosophy

Analytics should be derived from attempt history.

Do not ask users to manually state:

```text
"My weakest move is Floating Passage."
```

Instead, infer it from recorded attempts where possible.

For example:

```text
Attempt 1
Phase 1
Killed by Thrust

Attempt 2
Phase 2
Killed by Floating Passage

Attempt 3
Phase 2
Killed by Floating Passage

Attempt 4
Phase 3
Killed by Lightning

Attempt 5
Phase 2
Killed by Floating Passage
```

The application can derive:

```text
Most Common Failure:
Floating Passage

Main Bottleneck:
Phase 2
```

The product should prefer:

```text
data-derived insight
```

over:

```text
user self-assessment
```

when the available attempt data supports it.

---

# V1 Analytics

## Total Attempts

```text
Total Attempts: 15
```

---

## Victory Status

```text
Defeated: Yes
```

Optional:

```text
Attempts Until First Victory: 15
```

---

## Most Common Failure Move

Use attempts with known structured failure moves.

Example:

```text
Floating Passage    5
Thrust Attack       3
Lightning Attack    2
```

If too many attempts have unknown causes, do not pretend the move analytics are complete.

---

## Phase Failure Breakdown

Use failed attempts grouped by phase reached.

Example:

```text
Phase 1    3 failures
Phase 2    8 failures
Phase 3    4 failures
```

---

## Main Bottleneck Phase

The simplest V1 definition may be:

> the phase associated with the largest number of failed attempts

Keep this definition explicit.

Do not introduce sophisticated statistical interpretations during V1.

---

## Progress Over Time

Keep progress analytics simple.

Useful signals may include:

* phase reached per attempt
* recent attempts reaching later phases
* number of attempts before victory
* reduction in failures to a particular move

Do not claim that the user is objectively improving based on insufficient evidence.

---

# Backend API

## Health

```text
GET /health
```

Example:

```json
{
  "status": "ok"
}
```

---

## Boss List

```text
GET /api/bosses
```

Return boss summaries.

Example:

```json
[
  {
    "id": "genichiro-ashina",
    "name": "Genichiro Ashina",
    "location": "Ashina Castle"
  }
]
```

---

## Boss Detail

```text
GET /api/bosses/{boss_id}
```

Return:

* boss metadata
* phases
* moves

Return HTTP 404 for unknown bosses.

---

## Record Attempt

```text
POST /api/bosses/{boss_id}/attempts
```

The request should contain only information needed to represent the attempt.

Example:

```json
{
  "result": "failed",
  "phase_reached": 2,
  "failure_move_id": "floating-passage",
  "notes": ""
}
```

Validate:

* boss exists
* phase exists
* selected move belongs to the relevant boss
* victory does not require a failure move

Do not overcomplicate validation.

---

## Attempt History

```text
GET /api/bosses/{boss_id}/attempts
```

Return attempts for the selected boss.

Prefer reverse chronological ordering when presenting history.

---

## Analytics

```text
GET /api/bosses/{boss_id}/analytics
```

Compute analytics from attempt records.

Potential response:

```json
{
  "total_attempts": 12,
  "defeated": false,
  "best_phase": 3,
  "main_bottleneck_phase": 2,
  "most_common_failure_move": "floating-passage",
  "failure_by_phase": {
    "1": 2,
    "2": 6,
    "3": 4
  },
  "failure_by_move": {
    "floating-passage": 4,
    "thrust": 2,
    "lightning": 2
  }
}
```

Analytics should normally be computed rather than stored separately.

---

# Backend Structure

Prefer:

```text
backend/
└── app/
    ├── main.py
    │
    ├── models/
    │   ├── boss.py
    │   └── attempt.py
    │
    ├── routers/
    │   ├── bosses.py
    │   └── attempts.py
    │
    ├── services/
    │   ├── boss_service.py
    │   ├── attempt_service.py
    │   └── analytics_service.py
    │
    └── data/
        ├── bosses.json
        └── attempts.json
```

Preferred flow:

```text
Router
   ↓
Service
   ↓
JSON
```

Analytics:

```text
Analytics Router
      ↓
Analytics Service
      ↓
Attempt Data
```

Avoid repository interfaces, dependency injection frameworks, factories, or enterprise patterns unless they solve a concrete V1 problem.

---

# Frontend Structure

Prefer approximately:

```text
frontend/src/
├── api/
├── components/
├── pages/
├── types/
└── App.tsx
```

Potential main pages:

```text
Boss Selection
Boss Dashboard
```

The Record Attempt interaction can be:

* a modal
* a form on the boss dashboard
* a small dedicated route

Choose whichever keeps the V1 experience simplest.

Do not create many pages unnecessarily.

---

# Boss Selection Page

The initial page should primarily answer:

> Which boss do you want to practice?

Example:

```text
Sekiro Boss Practice Analytics

Choose a Boss

┌──────────────────────┐
│ Genichiro Ashina     │
│ Ashina Castle        │
│                      │
│ [ View Boss ]        │
└──────────────────────┘
```

---

# Boss Dashboard Layout

Prefer a hierarchy approximately like:

```text
Boss Identity / Summary

[ Record Attempt ]

---------------------

Analytics

---------------------

Recent Attempts

---------------------

Boss Moveset Reference
```

Recording attempts and understanding current weaknesses should be visually more important than reading general boss information.

This is an analytics application, not primarily a Wiki.

---

# Attempt History

Keep the history concise.

Example:

```text
Attempt #12
Failed — Phase 3
Lightning Attack

Attempt #11
Failed — Phase 2
Floating Passage

Attempt #10
Victory
```

The user should be able to quickly understand progression without opening each attempt individually.

---

# TypeScript Types

Use explicit types.

Examples:

```text
BossSummary
Boss
BossPhase
BossMove
Attempt
CreateAttemptRequest
BossAnalytics
```

Avoid `any`.

Keep frontend types aligned with API contracts.

---

# API Client

Centralize frontend HTTP access.

Prefer:

```text
frontend/src/api/
├── bosses.ts
└── attempts.ts
```

Possible functions:

```text
getBosses()
getBossById()
createAttempt()
getBossAttempts()
getBossAnalytics()
```

Avoid putting raw fetch logic throughout UI components.

---

# JSON Persistence Rules

JSON is intentionally temporary persistence for V1.

Keep implementation simple.

Rules:

1. Keep boss metadata separate from attempt data.
2. Validate loaded data where practical.
3. Keep file reading/writing outside route handlers.
4. Do not silently discard malformed records.
5. Do not build database-like querying abstractions on top of JSON.
6. Assume a small local V1 dataset.
7. Do not design JSON persistence for large-scale concurrent multi-user writes.

If persistence complexity grows substantially, defer that work to the PostgreSQL migration in V2.

---

# Testing

Prioritize behavior that represents the product workflow.

Backend tests should include:

```text
GET /health
→ 200

GET /api/bosses
→ boss list

GET /api/bosses/genichiro-ashina
→ Genichiro data

GET /api/bosses/nonexistent
→ 404

POST attempt with valid phase and move
→ success

POST attempt with invalid boss
→ error

POST victory without failure move
→ success

POST failed attempt with Not Sure
→ success

GET attempt history
→ expected attempts

GET analytics
→ correct failure aggregation
```

Do not optimize for an arbitrary coverage percentage.

---

# Initial V1 Development Order

Build vertically.

```text
1. Initialize repository

2. Create Genichiro boss data

3. Create Pydantic boss models

4. GET /api/bosses

5. GET /api/bosses/{boss_id}

6. React boss selection page

7. React Genichiro dashboard

8. Attempt model

9. POST attempt API

10. Record Attempt UI

11. Attempt history

12. Failure-by-phase analytics

13. Failure-by-move analytics

14. Boss dashboard analytics UI

15. Tests

16. Docker
```

Do not start by collecting data for every Sekiro boss.

The first priority is:

```text
one boss
+
complete workflow
```

rather than:

```text
many bosses
+
incomplete workflow
```

---

# Future Versions

## V2

Potential additions:

* PostgreSQL
* relational boss/move/attempt schema
* larger Sekiro boss dataset
* improved search and filtering
* cleaner data ingestion
* richer analytics

---

## V3

Potential additions:

* user accounts
* persistent player profiles
* personalized long-term progress
* cross-session practice history
* more advanced recommendations

---

## V4

Gameplay analysis.

Instead of relying only on user memory:

```text
Gameplay Video
      ↓
Move Detection
      ↓
Player Response
      ↓
Success / Failure
      ↓
Detailed Analytics
```

Possible metrics:

* number of times a move appeared
* number of successful responses
* deflect success rate
* Mikiri success rate
* per-move failure probability

These metrics should NOT be requested manually from users in V1.

---

## V5

Multi-game boss practice analytics.

Potential games include:

```text
Sekiro
Black Myth: Wukong
```

Shared abstraction:

```text
Game
 └── Boss
      └── Phase
           └── Move
```

Game-specific mechanics may extend the shared model.

Do not implement multi-game abstractions prematurely unless they simplify the current code.

---

# Important Instructions for Claude

When working in this repository:

1. Treat V1 as a manual attempt logger and failure analytics application.
2. Do not turn V1 into detailed manual combat telemetry.
3. Never require users to remember every move encountered during a fight.
4. Keep attempt recording quick and lightweight.
5. Allow unknown failure causes.
6. Prefer structured move selection over free-text failure names.
7. Derive weaknesses from recorded attempt data instead of asking users to declare them manually.
8. Do not introduce PostgreSQL in V1.
9. Do not add authentication unless explicitly requested.
10. Do not introduce microservices.
11. Do not implement video analysis in V1.
12. Do not silently expand scope.
13. Prefer incremental changes.
14. Preserve working functionality.
15. Explain significant architectural changes before making them.
16. When debugging, identify the root cause instead of rewriting unrelated code.
17. Do not invent Sekiro gameplay mechanics or statistics when uncertain.
18. Keep JSON persistence isolated so it can later be replaced by PostgreSQL.
19. Compute analytics from attempt source data rather than storing unnecessary duplicated analytics.
20. Prioritize a complete user workflow over infrastructure sophistication.

---

# V1 Success Criteria

V1 is complete when a user can:

```text
Open App
   ↓
Choose Genichiro
   ↓
View Genichiro Dashboard
   ↓
Record Attempt
   ↓
Failed / Victory
   ↓
Select Phase Reached
   ↓
Select Failure Move / Other / Not Sure
   ↓
Save Attempt
   ↓
View Attempt History
   ↓
See Analytics
```

and the application can answer:

```text
How many times have I attempted this boss?

How far am I usually getting?

Which phase causes the most failures?

Which known move kills me most often?

Have I defeated the boss?
```

That is the complete V1 product scope.
