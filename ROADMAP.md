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

## V2 — Structured Sekiro Analytics Platform ✅

**Core question:**
**Where am I improving or struggling?**

V2 expanded the MVP into a more complete Sekiro analytics application.

Delivered:

* persistence migrated from JSON to PostgreSQL
* SQLAlchemy and Alembic for relational persistence and migrations
* 8 major Sekiro bosses with different phase counts and movesets
* richer move metadata (type, description, telegraph, counter, common mistakes) with a source page for each boss
* attempt progression analytics
* all-time vs. last 10 attempts comparisons
* attempts until first victory
* an overall Sekiro-level analytics dashboard with a boss comparison
* database, integration, and Docker checks in CI, all required before merging
* reliable local deployment with Docker Compose

V2 remains focused specifically on **Sekiro**.

Not included in V2:

* boss search and filtering, which was skipped because 8 bosses fit on one page
* public deployment, which moved into V3: with a single user and no accounts, a public instance would let anyone record attempts

### Completion target (met)

A stable multi-boss Sekiro analytics application backed by PostgreSQL, running locally, that can show both boss-specific and game-level player progression.

Released as `v2.0.0`.

---

## V3 — Personalized Practice Coach 🚧

**Core question:**
**What should I practice next?**

V3 introduces individual player identity, public deployment and practice recommendations.

Milestones:

1. ✅ **Accounts and authentication:** register, log in, log out, with hashed passwords and session cookies
2. ✅ **User-owned attempts:** every attempt belongs to a user; existing attempts move to the owner's account
3. ✅ **Per-user analytics:** boss analytics, progression and the Sekiro dashboard show only the user's own data
4. **Public deployment:** a stable URL with HTTPS, backups and deployment from `main`
5. **Practice recommendations:** rule-based suggestions derived from the user's own attempts, each showing its evidence
6. **Integration testing, CI and release**

Example output:

```text id="7v1njg"
Recommended Practice

1. Genichiro Ashina — Phase 2
   6 of your last 10 attempts ended in Phase 2.

2. Floating Passage
   4 of those 6 Phase 2 failures were recorded as Floating Passage.
```

Recommendations are based on recorded failures, not success rates, because the app does not know how often each move actually occurred.

Not included in V3:

* long-term practice tracking as a separate feature, since V2's progression analytics already cover it
* practice goals

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
      ├── Phase
      └── Move

Phase ←── many-to-many ──→ Move
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

Public hosting
→ needed once there are multiple users, after V3 adds accounts

Video / ML pipeline
→ needed for gameplay observation in V4

Multi-game abstraction
→ needed for Black Myth: Wukong and other games in V5
```

Keep each version focused, complete, and independently releasable before moving to the next.
