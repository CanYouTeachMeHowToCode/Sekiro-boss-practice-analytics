# Sekiro Boss Practice Analytics — Roadmap

This roadmap defines the planned evolution of **Sekiro Boss Practice Analytics**.

Each version should introduce one clear new user capability without prematurely adding complexity from later stages.

---

## V1 — Manual Boss Attempt Analytics ✅

**Core question:**
**What killed me?**

V1 is the MVP.

Players manually record the information they can realistically remember after each boss attempt:

* result: victory or failure
* phase reached
* failure move, `Other`, or `Not Sure`
* optional notes

The app provides:

* boss selection
* boss moveset reference
* attempt history
* total attempts
* best phase reached
* main bottleneck phase
* most common known failure move
* basic failure analytics

### Technology

* React + TypeScript
* FastAPI + Pydantic
* JSON persistence
* GitHub Actions CI
* Docker

V1 intentionally focuses on a small dataset and a complete end-to-end workflow rather than broad boss coverage.

---

## V2 — Structured Sekiro Analytics Platform

**Core question:**
**Where am I improving or struggling?**

V2 expands the MVP into a more complete Sekiro analytics application.

Main goals:

* migrate persistence from JSON to PostgreSQL
* use SQLAlchemy and Alembic for relational persistence and migrations
* support multiple major Sekiro bosses
* enrich boss and move metadata
* add progression analytics across attempts
* compare recent performance with historical performance
* add an overall Sekiro-level analytics dashboard
* add lightweight boss search and filtering
* strengthen integration testing and deployment

V2 remains focused specifically on **Sekiro**.

### Completion target

A stable multi-boss Sekiro analytics application backed by PostgreSQL that can show both boss-specific and game-level player progression.

---

## V3 — Personalized Practice Coach

**Core question:**
**What should I practice next?**

V3 introduces individual player identity and personalized training.

Main goals:

* user accounts and authentication
* user-specific attempt histories
* long-term practice tracking
* practice goals
* personalized weakness identification
* practice recommendations

Example output:

```text id="7v1njg"
Recommended Practice

1. Floating Passage
2. Phase 3 Lightning

Next Goal:
Reach Phase 3 for 3 consecutive attempts
```

V3 turns the application from an analytics tracker into a personalized practice assistant.

---

## V4 — Gameplay Analysis

**Core question:**
**What actually happened during the fight?**

V4 reduces reliance on user memory by analyzing gameplay itself.

Main goals:

* gameplay video upload
* move occurrence annotation
* player response tracking
* manual or semi-automatic gameplay labeling
* computer vision / ML-based boss move detection
* automatic or semi-automatic success/failure detection
* true per-move performance metrics

Example:

```text id="ngyp00"
Floating Passage

Encountered: 10
Successfully Handled: 7
Failed: 3

Success Rate: 70%
```

Unlike V1–V3, V4 can calculate true per-move success rates because the system knows both how often a move occurred and how the player responded.

---

## V5 — Multi-Game Boss Analytics Platform

**Core question:**
**Can the same analysis work across games?**

V5 generalizes the platform beyond Sekiro.

The first planned additional game is:

**Black Myth: Wukong**

Main goals:

* generalize the domain model across games
* support multiple games within the same application
* preserve game-specific combat mechanics
* reuse attempt and gameplay analytics across games
* explore cross-game weakness and performance analysis

Shared structure:

```text id="iiqf8a"
Game
 └── Boss
      └── Phase
           └── Move
```

Examples of game-specific mechanics:

### Sekiro

* Deflect
* Mikiri Counter
* Jump Counter
* Lightning Reversal
* Posture

### Black Myth: Wukong

* Dodge
* Stance
* Spell
* Transformation
* Focus

At this stage, the project evolves from a Sekiro-specific application into a generalized gameplay performance analytics platform.

---

# Version Summary

```text id="v5nnj2"
V1
What killed me?
→ Manual attempt analytics

V2
Where am I improving or struggling?
→ Structured Sekiro analytics

V3
What should I practice next?
→ Personalized practice coach

V4
What actually happened during the fight?
→ Gameplay / video analysis

V5
Can this work across games?
→ Multi-game analytics platform
```

---

# Guiding Principle

Do not add technology simply because it is commonly used in production systems.

Each major technical addition should support a clear product need:

```text id="3cxkh4"
JSON
→ enough for the V1 MVP

PostgreSQL
→ needed for richer structured persistence in V2

Authentication
→ needed for personalized users in V3

Video / ML pipeline
→ needed for gameplay observation in V4

Multi-game abstraction
→ needed for Black Myth: Wukong and other games in V5
```

Keep each version focused, complete, and independently releasable before moving to the next.
