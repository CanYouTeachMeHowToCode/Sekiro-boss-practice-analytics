# Sekiro Boss Practice Analytics — Roadmap

English | [简体中文](ROADMAP.zh-CN.md)

This roadmap defines the planned evolution of **Sekiro Boss Practice Analytics**.

The project began as a lightweight manual boss-attempt tracker, but development exposed an important constraint:

> Wiki-level boss movesets are useful for human-readable product content, but they are not reliable enough to serve as complete ground truth for gameplay analysis.

Some boss moves are missing, grouped inconsistently, or described inaccurately across community sources. Because later gameplay-analysis features depend on a trustworthy move taxonomy, engine/runtime ground truth must be established before automated video analysis.

The roadmap therefore separates:

```text
Product foundation
        ↓
Combat ground truth
        ↓
Automated gameplay understanding
        ↓
Multi-game generalization
```

Each version should answer one clear technical and product question.

---

# V1 — Manual Boss Attempt Analytics ✅

## Core Question

> **What killed me?**

V1 established the smallest complete product workflow.

Players manually record information they can realistically remember after a boss attempt:

- result: victory or failure
- phase reached
- failure move, `Other`, or `Not Sure`
- optional notes

The application provides:

- boss selection
- boss dashboard
- attempt recording
- attempt history
- total attempts
- best phase reached
- defeated status
- main bottleneck phase
- most common known failure move
- basic phase and failure-move analytics

## Technology

- React
- TypeScript
- Vite
- FastAPI
- Pydantic
- JSON persistence
- GitHub Actions
- Docker

V1 intentionally validated one complete vertical slice before expanding the dataset.

Released as `v1.0.0`.

---

# V2 — Structured Sekiro Analytics Platform ✅

## Core Question

> **Where am I improving or struggling?**

V2 evolved the JSON-backed MVP into a structured, relational, multi-boss application.

Delivered:

- PostgreSQL persistence
- SQLAlchemy ORM
- Alembic migrations
- relational `Game → Boss → Phase / Move` domain model
- `phase_moves` many-to-many mapping
- 8 major Sekiro bosses
- richer move metadata
- boss-level source provenance
- progression analytics
- all-time vs. recent-attempt comparisons
- attempts until first victory
- Sekiro-level analytics dashboard
- integration tests
- Docker Compose
- four required CI jobs:
  - backend
  - frontend
  - integration
  - docker

V2 intentionally remained locally deployed.

Released as `v2.0.0`.

---

# V3 — Multi-User Product Foundation ✅

## Core Question

> **Can different players reliably use the application with their own data?**

V3 turns the local single-user analytics application into a multi-user-capable product foundation.

V3 does **not** attempt to establish complete engine-level boss movesets.

The discovery that Wiki movesets are incomplete or inconsistent changes the role of V3 content:

> V3 boss data is product-level semantic content, not final gameplay ground truth.

---

## Milestone 1 — Accounts and Authentication ✅

Delivered:

- `users` table
- `user_sessions` table
- argon2 password hashing
- register
- login
- logout
- current-user endpoint
- server-side sessions
- httpOnly session cookie
- only a SHA-256 hash of session tokens stored in PostgreSQL
- login and registration UI

Boss reference data remains publicly browsable.

User analytics require authentication.

---

## Milestone 2 — User-Owned Attempts ✅

Delivered:

- `attempts.user_id`
- new attempts belong to the logged-in user
- historical ownerless attempts remain preserved
- ownerless attempts are hidden until explicitly claimed
- migration helper for assigning historical attempts

No request body may choose another user's `user_id`.

---

## Milestone 3 — Per-User Analytics and Isolation ✅

Delivered:

- per-user attempt history
- per-user boss analytics
- per-user progression analytics
- per-user Sekiro dashboard
- API-level isolation tests
- service-level isolation tests
- cross-user analytics isolation

A user must never read, modify, or influence another user's attempt analytics.

---

## Milestone 4 — Bilingual Product Interface ✅

Add English / Chinese language support for the existing product.

Delivered:

- language switch in the navigation
- logged-in users store their language preference in their account
- visitors use browser-local preference
- first visit may default from browser language
- interface text available in both languages
- each language displays only its own text
- no mixed English/Chinese pages except where technically unavoidable
- boss names and existing boss reference content support both languages

Use a lightweight in-house translation dictionary for interface text unless a larger i18n framework becomes justified.

Boss-content translations must preserve the meaning of the source material.

Do not describe translated terminology as official unless an authoritative source supports that claim.

---

## Milestone 5 — Existing Content Cleanup ✅

Review the boss data already present in the application.

The purpose is **not** to prove moveset completeness.

Goals:

- remove obvious inaccuracies
- correct misleading descriptions
- preserve source provenance
- avoid placeholder moves
- mark or document uncertainty rather than inventing information
- avoid adding large numbers of new Wiki-derived moves merely to appear complete

If a move cannot be verified confidently:

```text
do not invent
do not silently guess
do not force completeness
```

It may remain explicitly uncertain or be deferred to V4 ground-truth research.

This milestone also records a per-boss mapping between the product's moves and the Fextralife and Fandom entries (`research/ground_truth/semantic/wiki_mapping/`). It measures how far the two wikis disagree, which is a lower bound on the gap to ground truth, and it becomes the starting point for V4.

Delivered: obvious errors and misleading descriptions fixed, phase structures corrected (True Corrupted Monk; Genichiro, Way of Tomoe added to the Isshin fight), actions that cannot end an attempt removed from the movesets, move-level sources for moves taken from another page, and the mapping for all 8 bosses. Across 106 product moves, 52 match one-to-one between the two wikis.

### Important Boundary

V3 does **not** require:

- every Sekiro boss
- every boss animation
- every combat action
- engine-level completeness
- Resurrection moveset completeness
- automatic gameplay observation

Those belong to V4.

---

## Milestone 6 — V3 Hardening and Release ✅

Before release:

- backend tests pass
- frontend unit tests pass
- frontend typecheck passes
- frontend lint passes
- frontend-backend integration tests pass
- Docker Compose build and smoke test pass
- authentication isolation remains covered
- bilingual behavior is tested
- data survives a Docker Compose restart
- documentation reflects the new roadmap

The application remains reproducibly runnable locally with Docker Compose.

Release:

```text
v3.0.0
```

Released as `v3.0.0`.

---

## V3 Non-Goals

Do not introduce in V3:

- full engine-derived boss movesets
- gameplay reverse engineering as production architecture
- public hosting
- production cloud infrastructure
- practice recommendation algorithms
- video upload
- computer vision
- automatic move detection
- player-action recognition
- success-rate estimation
- Black Myth: Wukong
- Redis without a demonstrated need
- Kafka or message queues without a demonstrated need
- Kubernetes solely for portfolio complexity
- microservices without a demonstrated need

---

## V3 Completion Target

V3 is complete when:

```text
Open Application
      ↓
Choose English / 中文
      ↓
Register / Log In
      ↓
Browse Existing Boss Reference Data
      ↓
Record Attempts
      ↓
See Only Personal History
      ↓
See Only Personal Analytics
      ↓
Restart Through Docker Compose
      ↓
Data Persists
```

V3 proves the application architecture is ready for real user identity and persistent personal data.

It does not claim the move taxonomy is complete.

---

# V4 — Combat Ground Truth Foundation

## Core Question

> **What boss actions actually exist, and what evidence supports each semantic move?**

V4 establishes the trustworthy combat-data foundation required before video automation.

This is primarily a:

```text
reverse engineering
+
runtime instrumentation
+
dataset engineering
+
semantic modeling
```

version.

It is **not primarily a machine-learning version**.

---

# V4 Ground Truth Principle

No single source is sufficient.

Ground truth should combine:

```text
Runtime Truth
+
Engine/File Truth
+
Semantic Truth
+
Gameplay Evidence
```

Conceptually:

```text
Visible Gameplay Action
        ↕
Runtime Behavior / Event
        ↕
Animation / TAE
        ↕
Attack / Bullet / Effect Data
        ↕
Semantic Move
```

Wiki and community documentation remain useful for:

- human-readable names
- descriptions
- terminology
- discovery

They are not treated as final completeness authorities.

The project owner makes the final decision on what counts as ground truth. Tooling and assistants gather evidence and propose; they do not mark anything as verified on their own.

---

# V4 Data Layers

## 1. Ruleset

Every ground-truth observation belongs to a specific ruleset.

Examples:

```text
Sekiro Vanilla
Sekiro Resurrection
```

Rulesets must include version metadata where possible.

Do not mix Vanilla and Resurrection observations without explicitly labeling them.

---

## 2. Character Identity

Map product bosses to game-engine character identities.

Conceptually:

```text
Boss
    ↓
Boss Variant / Ruleset
    ↓
Character ID
```

One product boss may involve multiple internal character IDs or encounter variants.

---

## 3. Runtime Observation

Capture what the game reports while a boss action actually occurs.

Possible evidence includes:

- current behavior
- fired behavior events
- runtime state
- runtime animation identifiers
- timestamps
- phase
- gameplay context

Debug/developer tooling should be preferred where it exposes reliable runtime state.

---

## 4. Engine Action

Represent low-level game actions separately from semantic moves.

An engine action may contain:

- character ID
- animation ID
- runtime event
- TAE metadata
- attack parameter references
- projectile references
- effect references
- ruleset
- phase/context information

Do not assume:

```text
1 animation = 1 semantic move
```

---

## 5. Semantic Move

The existing product-level `Move` concept should be treated conceptually as a semantic move:

```text
Floating Passage
Perilous Thrust
Sweep Follow-Up
Lightning Attack
```

A semantic move may map to several engine actions.

An engine action may also be reused in several semantic contexts.

The likely relationship is therefore:

```text
SemanticMove
      ↕
many-to-many
      ↕
EngineAction
```

Do not force a one-to-one schema before the evidence supports it.

---

## 6. Gameplay Evidence

Every high-confidence mapping should eventually include observed gameplay examples.

Example:

```text
video
timestamp_start
timestamp_end
boss
ruleset
phase
semantic_move
runtime_events
engine_actions
```

These clips later become the foundation of the V5 video dataset.

---

# V4 Milestone 1 — Ground Truth Research Workspace

Create a research area separate from production application data.

Suggested structure:

```text
research/
└── ground_truth/
    ├── README.md
    ├── rulesets/
    ├── characters/
    ├── engine/
    ├── semantic/
    ├── observations/
    ├── annotations/
    └── scripts/
```

Do not commit copyrighted raw game assets.

Do not commit:

- extracted game archives
- proprietary animation files
- full game binaries
- large captured gameplay videos unless distribution rights are clear

Commit only:

- metadata
- mappings
- scripts
- annotations
- hashes
- derived research data that is safe to distribute

---

# V4 Milestone 2 — Genichiro Runtime Ground Truth Pilot

Use Genichiro as the first complete vertical slice.

Start with Vanilla.

Objectives:

- identify relevant character IDs
- enable runtime/debug instrumentation
- record gameplay with debug information visible or logged
- observe representative attacks
- capture runtime event/state/animation identifiers
- align timestamps with visible gameplay actions

Initial success does not require every move.

First prove:

```text
Visible Genichiro Action
        ↓
Runtime Identifier
```

for several representative attacks.

---

# V4 Milestone 3 — Static Engine Mapping

Starting from known runtime identifiers, trace backward into game/mod data.

Possible layers:

```text
Runtime Event
    ↓
HKS / Behavior Logic
    ↓
Animation
    ↓
TAE
    ↓
AtkParam / Bullet / SpEffect
```

Use tools only where they provide necessary evidence.

Avoid full-game extraction when selective inspection is sufficient.

Prefer:

```text
runtime-first
↓
targeted static analysis
```

over:

```text
extract everything
↓
manually inspect thousands of animations
```

---

# V4 Milestone 4 — Genichiro Semantic Move Catalog

Create a reviewed mapping between engine actions and semantic moves.

Each mapping should retain evidence.

Example shape:

```json
{
  "move_slug": "floating-passage",
  "ruleset": "vanilla",
  "character_ids": ["..."],
  "phases": [1, 2],
  "runtime_events": ["..."],
  "animation_ids": ["..."],
  "observed_clip_count": 5,
  "tae_verified": true,
  "confidence": "high"
}
```

Actual field names may change as research reveals the real relationships.

Do not prematurely migrate this schema into production PostgreSQL.

---

# V4 Milestone 5 — Completeness Validation

For the supported boss, define three sets:

```text
E = engine combat candidates
R = runtime-observed actions/events
S = semantic moves
```

Every engine combat candidate should eventually be classified as one of:

```text
mapped_to_semantic_move
non_combat
locomotion
hit_reaction
cinematic_or_scripted
duplicate_or_shared
unused_or_unreachable
unknown
```

Every runtime-observed combat action should map to:

```text
runtime observation
→ engine evidence
→ semantic move
```

The objective is not to prove mathematical completeness of every possible game state.

The objective is to make unexplained combat-relevant actions approach zero for the supported boss.

---

# V4 Milestone 6 — Resurrection Mapping

After Vanilla Genichiro is understood, analyze the Resurrection variant.

Treat Resurrection as a separate ruleset.

Use the mod override files as a differential clue:

```text
Vanilla
   ↓
Compare
   ↓
Resurrection Override
```

Classify moves/actions as:

```text
unchanged
modified
new_in_resurrection
vanilla_only
shared_semantic_move_with_different_engine_sequence
```

Do not mix Resurrection training examples with Vanilla examples without ruleset labels.

---

# V4 Milestone 7 — Product Integration

Once the ground-truth schema is stable enough:

- connect verified semantic moves back to the application
- correct inaccurate V3 move records
- add verified phase relationships
- expose provenance where useful
- optionally expose verification status internally
- preserve existing attempt references safely

Only now should production schema changes for engine-action mappings be considered.

Potential future concepts include:

```text
rulesets
boss_variants
engine_actions
move_engine_actions
```

Do not introduce them until actual research demonstrates the required cardinality and fields.

---

# V4 Milestone 8 — Expand Boss-by-Boss

After the Genichiro pipeline is proven, expand systematically.

Prioritize bosses that exercise different combat structures, for example:

```text
humanoid sword boss
beast boss
multi-phase boss
ranged/projectile-heavy boss
complex late-game boss
```

For each boss repeat:

```text
runtime discovery
↓
static engine tracing
↓
semantic mapping
↓
controlled gameplay validation
↓
completeness review
```

Do not return to Wiki-only bulk content expansion.

---

# V4 Milestone 9 — Public Deployment

Public deployment moves here from V3.

Deployment should happen only after:

- authentication is stable
- personal data isolation is tested
- bilingual UI works
- the application clearly distinguishes verified vs. uncertain combat content
- at least one complete ground-truth vertical slice is integrated
- database migration strategy is stable
- `attempts.user_id` is made NOT NULL, after confirming no ownerless pre-account attempts remain

Production concerns include:

- HTTPS
- production PostgreSQL
- environment secrets
- database backups
- migration execution
- secure cookies
- deployment from `main`
- recovery procedures
- observability appropriate to the actual hosting environment

Do not introduce infrastructure that is not required by the selected deployment platform.

---

# V4 Release Strategy

Do **not** block the first V4 release on reverse-engineering every main boss.

Recommended release model:

```text
v4.0.0
=
ground-truth pipeline proven
+
Genichiro complete vertical slice
+
production integration
+
public deployment
```

Then expand verified coverage incrementally:

```text
v4.1
v4.2
v4.3
...
```

Each release can add additional verified bosses.

This prevents ground-truth completeness from becoming an unbounded release blocker.

---

# V5 — Automated Gameplay Analysis

## Core Question

> **What actually happened during this fight without asking the player to manually record everything?**

V5 uses the V4 ground-truth catalog to reduce or eliminate manual attempt entry.

The long-term user experience becomes:

```text
Upload Gameplay
      ↓
Processing
      ↓
Detected Boss / Phase / Moves
      ↓
Detected Player Responses
      ↓
Fight Analytics
      ↓
Practice Suggestions
```

---

## V5 Milestone 1 — Video Upload and Storage

Add:

- gameplay video upload
- user ownership
- metadata
- processing status
- storage lifecycle

Video blobs do not need to live inside PostgreSQL.

PostgreSQL should store metadata and references.

---

## V5 Milestone 2 — Annotation Pipeline

Before automatic ML detection:

- build manual annotation tooling
- use V4 ground-truth IDs
- label move start/end timestamps
- label phase
- label ruleset
- preserve uncertain labels

The annotation tool should be useful even if ML never works perfectly.

---

## V5 Milestone 3 — Semi-Automatic Move Recognition

Start with assistance rather than full automation.

Example:

```text
System:
"This looks like Floating Passage."

[Confirm]
[Choose Different Move]
```

Measure:

- annotation speed improvement
- precision
- recall
- confidence calibration

---

## V5 Milestone 4 — Automatic Move Detection

Progress from:

```text
short clip
→ move classification
```

to:

```text
full fight
→ temporal segmentation
→ move classification
```

Do not require whole-fight understanding as the first ML milestone.

---

## V5 Milestone 5 — Player Response Detection

Detect or infer responses such as:

- deflect
- block
- dodge
- Mikiri Counter
- jump counter
- Lightning Reversal
- hit taken
- death

Only calculate metrics supported by observed events.

---

## V5 Milestone 6 — True Per-Move Analytics

Once move occurrences and outcomes are observable:

```text
Floating Passage

Occurrences: 12
Handled Successfully: 8
Failed / Damaged: 4
```

True rates become valid because the denominator is known.

This is fundamentally different from V1–V3 failure-count analytics.

---

## V5 Milestone 7 — Practice Recommendations

Practice recommendations move here from the old V3 roadmap.

Recommendations should use actual observed gameplay evidence where possible.

Example:

```text
Floating Passage

Observed: 8 times
Cleanly handled: 2
Damaged or failed: 6

Suggested focus:
Practice the final sequence of Floating Passage.
```

Recommendations must remain explainable.

Do not introduce LLM-generated or opaque skill scores unless a real product need emerges.

---

# V6 — Multi-Game Boss Analytics Platform

## Core Question

> **Can the same ground-truth and gameplay-analysis architecture work beyond Sekiro?**

The first planned additional game is:

**Black Myth: Wukong**

Goals:

- generalize game/ruleset abstractions
- preserve game-specific mechanics
- reuse video-analysis infrastructure
- reuse annotation infrastructure
- reuse semantic-move concepts where appropriate
- avoid pretending different combat systems share identical mechanics

Shared high-level hierarchy may remain:

```text
Game
 └── Boss
      ├── Phase
      └── Semantic Move
```

Game-specific concepts remain separate.

### Sekiro Examples

- Deflect
- Mikiri Counter
- Jump Counter
- Lightning Reversal
- Posture

### Black Myth: Wukong Examples

- Dodge
- Stance
- Spell
- Transformation
- Focus

---

# Version Summary

```text
V1
What killed me?
→ Manual attempt analytics

V2
Where am I improving or struggling?
→ Structured relational analytics

V3
Can different players reliably use it?
→ Multi-user product foundation

V4
What moves actually exist?
→ Combat ground truth + public product

V5
What happened in the fight automatically?
→ Video / CV gameplay analysis

V6
Can this work across games?
→ Multi-game analytics platform
```

---

# Guiding Principles

## Correctness Before Apparent Completeness

Do not add uncertain moves merely so the dataset looks complete.

```text
verified smaller dataset
>
large unreliable dataset
```

---

## Runtime and Engine Evidence Before Wiki Authority

Wiki data is useful for semantic naming and documentation.

It is not assumed to be complete ground truth.

---

## Preserve Lightweight Manual Tracking

Until video automation is reliable, the manual workflow remains:

```text
Result
Phase Reached
Failure Move / Other / Not Sure
Optional Notes
```

Do not turn manual attempt entry into combat telemetry.

---

## Maintain Honest Analytics

Before gameplay observation:

```text
failure count
```

is valid.

Without move-occurrence counts:

```text
success rate
```

is not valid.

True success rates begin only when V5 provides denominators.

---

## Add Technology Only for a Product or Research Need

```text
JSON
→ sufficient for V1

PostgreSQL
→ relational persistence in V2

Authentication
→ multi-user ownership in V3

Runtime / reverse-engineering tooling
→ trustworthy combat ground truth in V4

Public hosting
→ useful once product and content reliability justify exposure

Video / CV
→ reducing manual data-entry friction in V5

Multi-game abstraction
→ required only in V6
```

Avoid:

- unnecessary microservices
- Redis without a concrete need
- Kafka without a concrete need
- Kubernetes solely for complexity
- speculative infrastructure

---

# Final Project Direction

The long-term product goal is no longer merely:

> manually record boss attempts and view statistics.

The long-term goal is:

> **turn gameplay footage into trustworthy, explainable boss-practice analytics while minimizing manual input from the player.**

The project should progress toward that goal incrementally, with each version establishing the foundation required by the next.