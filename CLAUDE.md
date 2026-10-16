# Sekiro Boss Practice Analytics — Claude Development Instructions

## 1. Project Overview

Sekiro Boss Practice Analytics is a full-stack application for tracking and eventually automatically analyzing player performance against bosses in *Sekiro: Shadows Die Twice*.

The project began as a lightweight manual attempt tracker.

The long-term direction is now:

```text
Manual Attempt Tracking
        ↓
Structured Multi-User Product
        ↓
Verified Combat Ground Truth
        ↓
Gameplay Video Analysis
        ↓
Automatic Practice Analytics
```

The project must evolve incrementally.

Do not pull later-stage technology into earlier versions without a concrete requirement.

---

# 2. Current Project Status

## V1 — Completed

V1 established the full manual-attempt workflow:

```text
Choose Boss
→ Boss Dashboard
→ Record Attempt
→ Result
→ Phase Reached
→ Failure Move / Other / Not Sure
→ Save
→ History
→ Analytics
```

V1 used:

- React
- TypeScript
- FastAPI
- Pydantic
- JSON persistence
- GitHub Actions
- Docker

---

## V2 — Completed

V2 migrated the application to a structured relational platform.

Delivered:

- PostgreSQL
- SQLAlchemy
- Alembic
- relational boss / phase / move data
- `phase_moves` mapping
- multiple Sekiro bosses
- richer move metadata
- progression analytics
- recent vs. historical analytics
- Sekiro-level dashboard
- integration tests
- Docker Compose
- four required CI jobs

Released as:

```text
v2.0.0
```

---

## V3 — Completed

V3 was re-scoped during development.

The old V3 goal was:

```text
Personalized Practice Coach
```

The new V3 goal is:

```text
Multi-User Product Foundation
```

This change is intentional.

During content expansion, Wiki-derived movesets were found to be incomplete or inconsistent.

Therefore:

> V3 must not pretend Wiki content is complete engine-level ground truth.

Ground-truth completeness is now explicitly a V3.1 concern.

Delivered:

- accounts and authentication (argon2, server-side sessions in an httpOnly cookie)
- user-owned attempts, with ownerless pre-account attempts kept until claimed
- per-user analytics and isolation
- English / 中文 interface
- existing-content cleanup, plus a cross-wiki move mapping for every boss in `research/ground_truth/semantic/wiki_mapping/`
- four required CI jobs, including a check that data survives a Docker restart

Released as:

```text
v3.0.0
```

---

## V3.1 — Completed

V3.1 established combat ground truth for castle Genichiro (vanilla, all three phases) and rebuilt the product's Genichiro moveset from it. It was first planned as V4 (see the numbering note in section 3).

Delivered:

- a research workspace and pipeline in `research/ground_truth/`: game-file and battle-AI extraction, and a reader for the dev-menu overlay that turns recordings into verified animation IDs
- two verified castle recordings, and a check that every recorded transition is explained by the AI chains
- the castle Genichiro move catalog (63 moves from 45 AI chains), every entry approved by the project owner
- a completeness review of all 353 TAE entries of c7100 and c7110
- the product's Genichiro moveset rebuilt from the catalog: 26 moves, Iaijutsu merged into Receding Tide, texts reviewed against the engine evidence
- `attempts.user_id` NOT NULL

Released as:

```text
v3.1.0
```

---

# 3. Current Development Focus

## V4 — Automated Gameplay Analysis

V4 answers:

> **What happened during the fight without requiring the player to manually enter everything?**

V4 Milestone 1, the failure attribution prototype on local Genichiro recordings, is done (owner confirmed, 2026-10-16). Its code and tools are in `research/failure_attribution/`, its results in `research/failure_attribution/results.md`: an owner-checked answer set of 7 castle recordings, all HUD failure events correct, and the move behind a failure the top candidate in 88% and among the top three in 93% of the failures in recordings never used for tuning. Current: V4 Milestone 2, reliability validation on more independent recordings (section 38). The V3.1 research in `research/ground_truth/` remains the input: the owner-approved move catalog, the AI chains, and the dev-menu recordings, which double as labelled reference data.

**Numbering.** The combat ground-truth stage was first planned as V4. It mainly added a research foundation and a Genichiro content update to the V3 product, so it became V3.1 and shipped as `v3.1.0` (owner decision, 2026-10-15). The later stages moved down by one: automated gameplay analysis is V4 and the multi-game platform V5. Commits, PR #23 and research notes written before that date use the old names.

V3 and V3.1 are released. Sections 7–17 remain the reference for how the current product is built; their product rules (lightweight attempt recording, honest analytics, per-user isolation, one language per page) still apply. Sections 18–36 remain the reference for the ground-truth pipeline, which every later boss goes through (section 34).

Public deployment is V4 Milestone 4: it waits until a user can upload a recording and see which moves caused their failures (section 33).

Resurrection mod work is deferred (section 35). Boss expansion is deferred until the Genichiro end-to-end flow works in V4 (section 34).

Practice recommendations are part of V4.

---

# 4. Current Architecture

The production application follows:

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

Docker Compose provides the local application stack.

The frontend must not depend directly on PostgreSQL or raw persistence details.

The backend should preserve clear separation between:

```text
routers
services
database access
domain / API models
```

Do not place substantial database or analytics logic directly inside route handlers.

---

# 5. Current Core Domain Model

The current product model is conceptually:

```text
Game
 └── Boss
      ├── BossPhase
      └── Move

BossPhase
   ↕
PhaseMove
   ↕
Move
```

Player data:

```text
User
 └── Attempt
      ├── Boss
      ├── Result
      ├── Phase Reached
      ├── Failure Move
      ├── Failure Category
      ├── Notes
      └── Timestamp
```

Authentication:

```text
User
 └── UserSession
```

---

# 6. Important Meaning of `Move`

The current production `Move` model should be understood as:

> **a human-readable semantic move**

Examples:

```text
Floating Passage
Perilous Thrust
Sweep
Lightning Attack
```

It is **not** currently:

- a raw engine animation
- a TAE event
- a behavior state
- an HKS event
- an attack parameter
- a guaranteed one-to-one gameplay action

Do not assume:

```text
Move
=
Animation
```

This distinction becomes critical in V3.1.

---

# 7. V3 Product Principles

## 7.1 Preserve Lightweight Attempt Recording

The manual attempt form remains:

```text
Result
Phase Reached
Failure Move / Other / Not Sure
Optional Notes
```

Do not require users to manually record:

- every move encountered
- number of deflects
- Mikiri attempts
- posture events
- healing usage
- every player response
- detailed combat timelines

Those belong to future gameplay observation.

---

## 7.2 Preserve Honest Analytics

The application may derive:

```text
Floating Passage recorded failures: 5
```

It must not claim:

```text
Floating Passage success rate: 75%
```

unless the system knows how many times the move actually occurred.

Before V4 automated gameplay observation, the denominator usually does not exist.

---

## 7.3 Per-User Isolation Is Mandatory

Every user-owned attempt query must be scoped to the authenticated user.

A user must never:

- read another user's attempts
- alter another user's attempts
- affect another user's analytics
- submit another user's `user_id`

Boss reference content remains global.

User attempts remain personal.

---

# 8. V3 Milestone 1 — Accounts and Authentication ✅

Already completed.

Current expected behavior includes:

- registration
- login
- logout
- current-user lookup
- argon2 password hashing
- server-side sessions
- httpOnly cookie
- SameSite behavior appropriate for same-origin deployment
- only a hash of the session token stored in the database

Do not replace the existing session design with JWTs merely because JWTs are common.

The current same-origin server-side session model is appropriate.

---

# 9. V3 Milestone 2 — User-Owned Attempts ✅

Already completed.

Current expectations:

- new attempts belong to the authenticated user
- ownerless historical attempts are preserved
- ownerless historical attempts are hidden
- since V3.1 every attempt has an owner: `attempts.user_id` is NOT NULL (section 32)
- explicit claiming is supported
- request bodies do not control ownership

Do not silently delete historical attempts.

---

# 10. V3 Milestone 3 — Per-User Analytics and Isolation ✅

Already completed.

The following must remain user-scoped:

- attempt history
- boss analytics
- progression
- recent-attempt comparisons
- Sekiro dashboard

Do not change the mathematical definitions of V2 analytics solely because user identity was added.

---

# 11. V3 Milestone 4 — Bilingual Interface ✅

Implement English / Chinese product support.

## User Preference

Logged-in users:

```text
language preference
→ stored in user account
```

Visitors:

```text
language preference
→ browser storage
```

The initial visitor language may use browser language.

---

## Interface Translation

Use a lightweight translation layer.

Example concept:

```typescript
t("nav.dashboard")
t("auth.login")
t("attempt.record")
```

For only English and Chinese, do not introduce a heavy localization framework unless the current simple approach becomes inadequate.

---

## Boss Content

Existing supported boss content should have both English and Chinese display forms where practical:

- boss name
- location
- phase names
- move name
- description
- telegraph
- counter
- common mistakes

Do not claim a Chinese term is official unless the source supports that claim.

If a translation is authored manually, treat it as a translation.

---

## Language Rule

A page should normally display one language at a time.

Avoid mixed-language content such as:

```text
Floating Passage 浮舟渡
```

unless there is a deliberate product reason.

---

## Delivered

- language switch in the nav bar; `users.preferred_language` (set through `PATCH /api/auth/me`) for logged-in users, `localStorage` for visitors, and the browser language on a first visit
- every interface string in `frontend/src/i18n/messages.ts`; the Chinese table must have exactly the same keys as the English one, enforced by the TypeScript type
- Chinese boss names, locations, phase names, move names, descriptions, telegraphs, counters and common mistakes for the existing bosses
- the seed rejects an English text field without its Chinese version, and a move without a Chinese name
- `moves.name_zh_source` is `wiki` (with `name_zh_source_url`, checked by a database constraint) only when the full name appears on a Chinese wiki page; everything else is `translation`
- Chinese move descriptions are translations of the sourced English text; the Chinese moveset shows one note saying so
- move descriptions appear as a hover tooltip and under the move select when recording an attempt

The user reviewed all Chinese content.

---

# 12. V3 Milestone 5 — Existing-Content Cleanup ✅

This milestone has changed significantly from the old roadmap.

## Old Requirement

The previous plan required:

```text
all main bosses
+
reviewed Wiki movesets
```

That is no longer the V3 target.

---

## New Requirement

Review the content already present.

Goals:

- fix obvious inaccuracies
- remove misleading descriptions
- preserve source links
- avoid placeholder content
- preserve phase relationships
- identify uncertain content
- do not invent missing moves

Do not bulk-add every remaining Sekiro boss from Wiki data solely to finish a checklist.

---

## Progress

The existing content was reviewed against both Fextralife and Fandom, and the user decided each item. Done on `dev`:

- fixed: True Corrupted Monk phase 2 keeps her phase-1 moves; Guardian Ape gains the phase-2 Jumping Sweep; misattributed or misleading text corrected; Owl (Father)'s Shadowfall named as the combat art 秘传·巨型忍者落杀
- the Isshin fight starts with a Genichiro, Way of Tomoe phase (only the moves both wikis agree on); Isshin's own phases are now 2-4, and existing Isshin attempts were moved up one phase by a migration
- actions that cannot end an attempt were removed from the movesets (Owl's zig-zag, Guardian Ape's roar, Lady Butterfly's rafter jump, Great Shinobi Owl's Shinobi Charm)
- both Owls gained Mikiri Counter, from Fandom, using the new move-level source fields
- move types made consistent
- the cross-wiki mapping for every boss is in `research/ground_truth/semantic/wiki_mapping/`; it records what both wikis say, including what the product does not use

Decided: Lady Butterfly and Guardian Ape keep their current move lists. Fandom's more specific lists are recorded in the mapping, and V3.1 rebuilds these movesets from engine evidence.

---

# 13. Wiki Data Policy

Wiki sources are useful for:

- move names
- human descriptions
- strategy descriptions
- community terminology
- discovery

Wiki sources are **not assumed to be complete ground truth**.

If two sources disagree:

```text
do not silently pick one
```

If the application cannot confidently resolve the disagreement:

```text
record uncertainty
or
defer to V3.1 research
```

Do not manufacture a confident answer.

Optional move fields:

Only fill `telegraph` and `common_mistakes` when the source explicitly states them.

Leave them null rather than inferring them from the description or from general game knowledge.

---

# 14. V3 Content Completeness Definition

V3 requires:

> **product-level content quality**

V3 does not require:

> **engine-level combat completeness**

Product-level quality means:

- the existing content is useful
- obviously wrong content is corrected
- major user-facing moves are represented
- uncertain information is not presented as fact

Engine completeness belongs to V3.1.

---

# 15. V3 Milestone 6 — Hardening and Release ✅

Before releasing V3:

- backend tests pass
- frontend tests pass
- TypeScript typecheck passes
- lint passes
- frontend build passes
- frontend-backend integration tests pass
- Docker Compose build passes
- Docker smoke test passes
- authentication isolation remains covered
- bilingual behavior is tested
- data survives a Docker Compose restart (checked by the `docker` CI job)

The application remains locally deployable through Docker Compose.

Release:

```text
v3.0.0
```

---

# 16. V3 Non-Goals

Do not implement in V3 unless explicitly requested:

- public cloud deployment
- production domain / HTTPS
- complete engine-derived movesets
- exhaustive character animation extraction
- full reverse engineering pipeline
- practice recommendation algorithms
- video upload
- computer vision
- automatic move detection
- automatic response detection
- gameplay telemetry
- true per-move success rates
- Black Myth: Wukong
- Redis without a demonstrated need
- Kafka without a demonstrated need
- Kubernetes solely for portfolio complexity
- microservices without a demonstrated need

---

# 17. V3 Success Criteria

V3 is complete when a user can:

```text
Open Application
      ↓
Choose English / 中文
      ↓
Register / Log In
      ↓
Browse Existing Boss Content
      ↓
Record Attempts
      ↓
See Only Personal Attempts
      ↓
See Only Personal Analytics
      ↓
Restart Docker Stack
      ↓
Data Persists
```

V3 proves the product architecture.

It does not claim complete combat knowledge.

---

# 18. V3.1 — Combat Ground Truth Foundation

V3.1 answers:

> **What boss actions actually exist, and what evidence supports the semantic moves used by the product?**

This version exists because the Wiki-only approach is not sufficiently reliable for later automated gameplay analysis.

V3.1 is primarily:

```text
runtime instrumentation
+
reverse engineering
+
data engineering
+
semantic mapping
```

Do not treat V3.1 primarily as a machine-learning milestone.

---

# 19. V3.1 Evidence Model

Ground truth should be based on several evidence layers.

Conceptually:

```text
Gameplay Observation
        ↕
Runtime Behavior/Event
        ↕
Engine Animation
        ↕
TAE / Attack / Projectile / Effect Data
        ↕
Semantic Move
```

No single source should automatically override all others.

**The project owner decides what is ground truth.** Claude and any tooling gather evidence, compare sources and propose, stating their uncertainty. They never mark a semantic move, an engine mapping or a phase structure as verified on their own.

---

# 20. Rulesets

Every dataset carries its combat ruleset.

V3.1 covers only:

```text
Vanilla Sekiro
```

The Resurrection mod is a separate ruleset. Its work is deferred until after `v3.1.0` (section 35), but the ruleset label stays on every dataset so it can be added later without reworking vanilla data.

Version metadata should be preserved where possible.

Do not combine Vanilla and Resurrection observations into one unlabeled dataset.

The same semantic move may have different:

- animations
- timing
- combo structure
- runtime events
- phase behavior

across rulesets.

---

# 21. Ground Truth Research Must Stay Separate Initially

Do not immediately add unstable reverse-engineering concepts to production PostgreSQL.

Begin with a research workspace.

Recommended:

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

Example responsibilities:

```text
rulesets/
→ ruleset version metadata (vanilla in V3.1)

characters/
→ product boss ↔ character ID mappings

engine/
→ animation / runtime / TAE metadata

semantic/
→ semantic move mappings

observations/
→ runtime gameplay observations

annotations/
→ video timestamp labels

scripts/
→ extraction / validation utilities
```

`research/ground_truth/` already exists. V3 Milestone 5 added `semantic/wiki_mapping/`: one JSON file per boss that lines up product moves with Fextralife and Fandom entries, plus `scripts/wiki_mapping_report.py`, which rebuilds the readable report and checks that every product move is mapped exactly once. Use it as the starting candidate list for the semantic catalog and as the baseline for measuring the gap to engine-level ground truth.

---

# 22. Copyright / Repository Rule

Do not commit proprietary game assets to Git.

Do not commit:

- original game binaries
- extracted full game archives
- FromSoftware animation bundles
- proprietary model/texture files
- large copyrighted gameplay assets without a clear reason and permission

Prefer committing:

- scripts
- hashes
- derived metadata
- mappings
- identifiers
- annotations
- documentation

Raw extracted game assets should remain local and gitignored.

---

# 23. V3.1 Milestone 1 — Research Foundation

Create:

- vanilla ruleset metadata (Resurrection metadata is deferred with the rest of the Resurrection work)
- research folder structure
- ground-truth schema drafts
- local asset paths through configuration
- `.gitignore` rules
- scripts for safe metadata extraction

Do not modify the production DB merely to anticipate later needs.

---

# 24. V3.1 Milestone 2 — Genichiro Runtime Pilot

Use Genichiro as the first vertical slice.

Vanilla only.

Objectives:

1. identify relevant character IDs
2. enable the available debug/developer instrumentation
3. record gameplay
4. observe runtime behavior/event/animation identifiers
5. align identifiers with visible attacks

First prove:

```text
visible action
→ runtime identifier
```

for a small number of representative attacks.

Do not attempt full game extraction before proving this bridge works.

Once the bridge is proven, recording is targeted at gaps in the semantic catalog (section 29): moves with only static or ambiguous evidence, and moves the product will support that lack a reference clip. Do not try to record every animation in the game files.

---

# 25. V3.1 Runtime-First Principle

Prefer:

```text
observe action in game
        ↓
capture runtime identifier
        ↓
search relevant files
        ↓
trace engine evidence
```

over:

```text
extract thousands of animations
        ↓
inspect everything manually
        ↓
guess which animation matches gameplay
```

Runtime instrumentation should shrink the static reverse-engineering search space.

---

# 26. V3.1 Milestone 3 — Static Engine Mapping

After obtaining runtime identifiers, trace them into engine data.

Possible chain:

```text
runtime event
    ↓
HKS / behavior logic
    ↓
animation
    ↓
TAE
    ↓
AtkParam / Bullet / SpEffect
```

Use:

- Debug Menu / developer runtime information
- targeted original-game extraction
- DSAnimStudio or equivalent animation inspection
- TAE extraction
- parameter inspection

only as required.

Do not introduce tooling simply because it exists.

---

# 27. Resurrection Analysis Strategy (Deferred)

Deferred until after `v3.1.0`, together with section 35. Kept here for when that work starts.

Treat Resurrection as:

> **a separate ruleset and a useful differential clue**

The mod override directory shows which resources Resurrection replaces.

Prefer:

```text
Mod Override First
        ↓
Trace Changed Resources
        ↓
Vanilla Extraction On Demand
```

instead of extracting the entire vanilla game immediately.

Later compare:

```text
Vanilla
    ↕
Resurrection
```

at the levels of:

- runtime behavior
- combo transitions
- animation sequence
- TAE timing
- attack/projectile/effect parameters

---

# 28. Engine Action vs. Semantic Move

Do not force:

```text
1 Engine Animation
=
1 Semantic Move
```

A semantic move may contain:

```text
Animation A
Animation B
Animation C
```

One low-level action may also be reused in several contexts.

Expect the eventual relationship to possibly be:

```text
SemanticMove
      ↕
many-to-many
      ↕
EngineAction
```

Preserve this uncertainty until actual data confirms the schema.

---

# 29. V3.1 Milestone 4 — Genichiro Semantic Catalog

The catalog lists every action that can hit the player, cause a mistake, break the player's posture or kill. Guards, deflects, steps, dashes and hit reactions are engine actions, not moves. An animation can be only part of a move.

Build the draft from the battle AI (each AI option usually requests one complete move chain, with branches and trigger conditions), TAE, runtime recordings, wiki names as candidates, and animation previews. Group variants under a move family: Genichiro's three Floating Passage variants are one family.

Every entry carries an evidence status: `runtime observed`, `static evidence only` or `to confirm`. The project owner confirms every name, grouping and variant.

Outputs: a reviewable move ↔ animation table, and time-labelled reference clips for the moves the product will support.

For each semantic move, gather evidence such as:

- ruleset
- character ID
- phase
- runtime events
- animation IDs
- TAE evidence
- parameter references
- gameplay observations
- video examples
- confidence

Example conceptual record:

```json
{
  "move_slug": "floating-passage",
  "ruleset": "vanilla",
  "phases": [1, 2],
  "runtime_events": [],
  "animation_ids": [],
  "observed_clip_count": 0,
  "tae_verified": false,
  "confidence": "unknown"
}
```

This is an illustrative schema only.

Do not lock production architecture to it prematurely.

---

# 30. Confidence

Ground-truth mappings should support an evidence/confidence concept.

Possible values:

```text
high
medium
low
unknown
```

Confidence should be based on evidence, not intuition.

For example:

```text
high:
runtime observed
+
animation matched
+
TAE / attack evidence
+
multiple gameplay examples
```

Do not automatically treat a Wiki description as `high`.

Confidence values are proposals until the project owner confirms them.

---

# 31. V3.1 Milestone 5 — Completeness Review

For each supported boss define:

```text
E = engine combat candidates
R = runtime-observed actions
S = semantic moves
```

Classify every engine candidate as:

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

Investigate unexplained combat candidates.

The goal is:

```text
unknown combat-relevant actions
→ as close to zero as practical
```

Do not claim absolute mathematical completeness unless evidence supports it.

---

# 32. V3.1 Milestone 6 — Product Integration

Only after the research schema stabilizes:

- correct inaccurate production moves
- improve phase mappings
- sync verified semantic content
- preserve attempt foreign-key integrity
- make `attempts.user_id` NOT NULL through a migration. V3 left it nullable so attempts recorded before accounts existed could stay ownerless until claimed with `python -m scripts.claim_attempts <username>`. The migration should fail loudly if any ownerless attempts remain.
- consider adding ruleset support
- consider adding engine-action mappings

**Delivered for castle Genichiro (owner decisions, 2026-10-15):**

- the product moveset rebuilt from the owner-approved catalog: 26 moves instead of 22, five new ones that neither wiki lists, Iaijutsu merged into Receding Tide, several moves extended to phase 3, and the owner's English and Chinese names (`research/ground_truth/semantic/genichiro_product_moveset.md`)
- move texts reviewed against the engine evidence; new moves have no text yet (`semantic/genichiro_content_review.md`)
- a migration that moves Iaijutsu attempts to Receding Tide before deleting the move
- `attempts.user_id` NOT NULL; the migration refuses to run while ownerless attempts remain
- the cross-wiki mapping marks every Genichiro row `owner_confirmed`, with the catalog entries behind it
- the moveset source line reads "Some descriptions from:", since not every text comes from the wiki
- no engine-mapping tables: the research catalog stays the source of the move ↔ animation chains (owner decision)

The product seed is written from the research files by `research/ground_truth/scripts/ai/sync_seed.py`; change the moveset there, not by hand. Importing V1 history now needs an owner: `python -m scripts.import_v1_data --attempts <file> --owner <username>`.

Potential future tables:

```text
rulesets
boss_variants
engine_actions
move_engine_actions
```

These are not mandatory names.

Let the actual research data determine the relational model.

---

# 33. Public Deployment (V4)

Public deployment moved from V3.1 to V4 (owner decision, 2026-10-12). The public product starts with the end-to-end flow: a user uploads a recording and sees their failures and the moves that caused them. It comes right after the video upload and failure report (section 38).

Before deployment ensure:

- the upload → failure report flow works and has passed reliability validation
- authentication works reliably
- user isolation is tested, uploaded recordings included
- bilingual UI works
- database migrations are reproducible
- verified content is distinguishable from uncertain content

Rehearse with a private deployment once the upload work begins. A small invite-only deployment is fine if outside feedback is needed sooner.

Production concerns may include:

- HTTPS
- production PostgreSQL
- secure environment variables
- database backups
- migration execution
- secure cookies
- deployment workflow
- logging
- recovery
- object storage for uploaded recordings
- background processing for video analysis, and its cost
- upload size limits
- retention and privacy rules for users' recordings

Choose infrastructure based on actual hosting requirements.

Do not introduce Kubernetes by default.

---

# 34. Deferred — Boss Expansion

Not part of V3.1 (owner decision, 2026-10-13). It starts after the V4 end-to-end flow works for Genichiro and is publicly deployed (section 33); when exactly is the project owner's decision.

Each new boss then goes through the whole pipeline once: the ground truth (V3.1 tooling) and the data that V4's recognition needs, such as reference clips and labels. Expanding earlier would mean redoing those bosses once V4 shows what it needs.

Expand boss-by-boss.

Do not immediately process every boss in parallel.

Prefer representative progression:

```text
Genichiro
↓
another humanoid boss
↓
beast boss
↓
projectile/special-effect-heavy boss
↓
late-game complex boss
```

Reuse tooling aggressively.

The ground-truth pipeline should become more automated with each boss.

---

# 35. Deferred — Resurrection Ground Truth

Not part of V3.1's vanilla milestones. It starts after `v3.1.0`; whether in a v3.x release or after V4 is the project owner's decision.

Once the vanilla pipeline is understood, build the Resurrection mapping.

Classify differences as:

```text
unchanged
modified
new_in_resurrection
vanilla_only
same_semantic_move_different_engine_sequence
```

Every gameplay/video observation must carry its ruleset.

This becomes essential for future CV training.

---

# 36. V3.1 Release Boundary

Do not block `v3.1.0` on ground-truth completeness for every Sekiro boss.

Recommended `v3.1.0` target:

```text
Genichiro ground-truth pipeline proven
+
castle Genichiro move catalog confirmed by the project owner
+
verified production integration
```

Public deployment is not part of `v3.1.0`; it comes in V4 (section 33).

Boss expansion is not part of V3.1 either. It follows the Genichiro end-to-end flow (section 34), so ground-truth completeness for other bosses never blocks a release.

Resurrection is not part of `v3.1.0` (section 35).

---

# 37. V4 — Automated Gameplay Analysis

V4 answers:

> **What happened during the fight without requiring the player to manually enter everything?**

The desired long-term flow is:

```text
Upload Gameplay
      ↓
Detect Boss / Ruleset
      ↓
Detect Phase
      ↓
Detect Move Occurrences
      ↓
Detect Player Responses
      ↓
Compute Analytics
      ↓
Recommend Practice
```

---

# 38. V4 Development Order

Do not jump directly to full automatic fight understanding.

Use:

```text
1. Failure attribution prototype on local recordings
   (hand-labelled answer set; detect damage / posture break / death
    → look back → identify the move → merge one failure → failure report)
2. Reliability validation on independent recordings
3. Video upload and failure report (failure counts per move)
4. Public deployment (section 33)
5. Whole-fight move detection (short clips first, then temporal segmentation)
6. Player-response detection
7. True per-move analytics
8. Recommendations
```

At first the system proposes move candidates and a person confirms them. Recordings made with the dev-menu overlay are labelled reference data; mask the overlay when training or evaluating.

Every stage should produce useful intermediate tooling.

---

# 39. V4 Video Data Model Principles

PostgreSQL should hold:

- metadata
- user ownership
- analysis records
- annotations
- processing status
- references

Large video blobs should generally use appropriate file/object storage rather than database byte columns.

Do not choose a storage provider until public deployment requirements justify it.

---

# 40. V4 Analytics Rule

True per-move success rates become valid only when move occurrences and responses are actually observed.

Before that:

```text
failure count
```

is valid.

After reliable gameplay observation:

```text
success / occurrence count
```

may become valid.

Do not mix the two definitions.

---

# 41. Practice Recommendations Move to V4

Do not build a sophisticated recommendation engine from incomplete manual failure labels.

Recommendations become significantly more valuable when based on observed move occurrences.

They should remain explainable.

Example:

```text
Floating Passage occurred 8 times.
You handled 2 cleanly.
You were hit or failed 6 times.

Suggested focus:
Floating Passage.
```

Avoid opaque skill scores.

---

# 42. V5 — Multi-Game Platform

V5 generalizes the architecture beyond Sekiro.

The first planned additional game is:

```text
Black Myth: Wukong
```

Do not begin V5 abstractions during V3–V4 unless a real shared requirement emerges.

Avoid speculative generic schemas.

---

# 43. Backend Engineering Rules

Use:

- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL

Keep:

```text
router
→ service
→ database
```

separation.

Do not put complex queries directly in route handlers.

Use database constraints where domain invariants clearly belong in the database.

---

# 44. Alembic Rules

Every production schema change must have a reviewed Alembic migration.

Do not rely on:

```python
Base.metadata.create_all(...)
```

as a production migration strategy.

Check migration/model drift in tests.

Do not edit already-released migrations unless there is a compelling repository-specific reason.

Prefer a new migration.

---

# 45. Seed Data Rules

Boss reference data may continue to be maintained in source-controlled seed files.

Runtime product reads should come from PostgreSQL.

Seed sync must not silently delete rows that existing attempts reference.

If a semantic move needs to be removed:

1. check whether attempts reference it
2. decide how those attempts should be preserved
3. migrate deliberately
4. only then remove or hide the move

Sources are recorded per boss (`bosses.source_name`, `bosses.source_url`). When a move's data comes from a different page, set that move's own `source_name` and `source_url`; leave them null otherwise. The frontend shows a move-level source under the move.

When the product's moves change, update `research/ground_truth/semantic/wiki_mapping/` and run `python research/ground_truth/scripts/wiki_mapping_report.py`.

---

# 46. API Compatibility

Preserve existing API contracts where practical.

If a contract changes:

- update backend schema
- update frontend types
- update API client
- update tests
- update integration tests

Do not create hidden frontend/backend contract drift.

---

# 47. Frontend Rules

Keep frontend structure clear:

```text
api/
components/
pages/
types/
utils/
```

Prefer explicit TypeScript types for backend responses.

Keep persistence knowledge out of React components.

Do not let UI components know about SQLAlchemy or database tables.

---

# 48. Testing Rules

Maintain coverage at several layers.

## Backend

- unit tests
- service tests
- API tests
- PostgreSQL-backed tests
- migration tests
- user-isolation tests

## Frontend

- component tests
- typecheck
- lint
- build

## Integration

Test real frontend/backend contracts against PostgreSQL.

Important flows include:

```text
register
→ login
→ record attempt
→ read attempt
→ analytics update
```

Future V3.1/V4 tests should be added incrementally as those systems exist.

---

# 49. CI Rules

Current required checks should remain:

```text
backend
frontend
integration
docker
```

Do not add CI jobs solely to increase complexity.

A CI job should protect a real failure mode.

---

# 50. Docker Rules

Docker Compose remains the canonical local full-stack environment.

A developer should be able to bring up:

```text
frontend
backend
postgres
```

with documented environment variables.

Do not make public-cloud infrastructure necessary for local development.

---

# 51. Branch Workflow

Continue:

```text
main
↑
dev
↑
feature/*
```

Meaning:

```text
main
= released/stable

dev
= current integration branch

feature/*
= focused implementation branches
```

Ground-truth experiments may use focused branches such as:

```text
feature/ground-truth-genichiro
feature/bilingual
feature/content-cleanup
```

Do not use a `stg` branch merely to represent a deployment environment.

---

# 52. Scope Discipline

Do not add technology because it sounds production-grade.

Before adding a technology, answer:

```text
What current problem does this solve?
```

If there is no concrete answer, do not add it.

Examples currently not justified by default:

- Redis
- Kafka
- RabbitMQ
- Kubernetes
- service mesh
- microservices
- distributed tracing stack
- vector database
- LLM agent framework

---

# 53. Current Priority Order

V3 and V3.1 are released. V4 order (section 38):

```text
1. Failure attribution prototype on local recordings (V4 Milestone 1) — done (2026-10-16)
2. Reliability validation on independent recordings (V4 Milestone 2) — current
3. Video upload and failure report (V4 Milestone 3)
4. Public deployment (V4 Milestone 4)
```

The later V4 milestones (whole-fight move detection, player responses, per-move analytics, recommendations) follow. Boss expansion is deferred until the Genichiro end-to-end flow works (section 34). Resurrection is deferred (section 35).

Keep the released product working: fix product bugs on `dev` as they appear.

---

# 54. When Content Is Uncertain

If asked to add or describe a move and the evidence is weak:

```text
STOP
```

Then:

1. identify the uncertainty
2. inspect available sources
3. compare runtime evidence if available
4. defer to V3.1 research if unresolved

Never fabricate combat behavior to complete a data file.

---

# 55. Current Definition of Success

The project should optimize for:

```text
correctness
+
traceability
+
useful product behavior
```

not:

```text
maximum number of features
+
maximum number of technologies
+
maximum number of boss rows
```

A smaller verified dataset is preferable to a larger unreliable one.

---

# 56. Long-Term Product Direction

The final product goal is:

> **A player uploads gameplay and receives trustworthy, explainable boss-practice analytics with minimal manual input.**

The project should reach this incrementally:

```text
V1
Manual attempt capture

V2
Structured analytics

V3
Multi-user product foundation

V3.1
Combat ground truth

V4
Automated gameplay analysis

V5
Multi-game platform
```

Every major version should leave the application in a coherent, working state.

Do not sacrifice a stable earlier layer merely to reach a more ambitious later feature.