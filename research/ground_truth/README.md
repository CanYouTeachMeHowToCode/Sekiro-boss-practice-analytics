# Ground truth research

Workspace for V4, Combat Ground Truth. See ROADMAP.md and CLAUDE.md (sections 18–36) for the plan.

It is kept separate from the production application: nothing here is read by the backend or the frontend, and nothing here changes the production database.

## Rules

- **The project owner decides what is ground truth.** Tools and Claude gather evidence, compare sources and propose; they never mark a semantic move, an engine mapping or a phase structure as verified.
- Every observation carries its ruleset (`vanilla`, `resurrection`).
- Do not commit proprietary game assets: game binaries, extracted archives, animation bundles, models or textures. Commit scripts, metadata, mappings, identifiers, hashes and annotations only.

## Contents

| Path | What it holds |
|---|---|
| `genichiro-plan.md` | Step-by-step plan (in Chinese) for capturing every vanilla Genichiro move with verified accuracy: static animation set, overlay extraction, recording protocol, coverage review, semantic catalog. |
| `semantic/wiki_mapping/` | Per-boss mapping between product moves, Fextralife entries and Fandom entries, made during V3 M5. It is the starting candidate list for the V4 semantic catalog and the baseline for measuring the gap to engine-level ground truth. |
| `scripts/wiki_mapping_report.py` | Rebuilds `semantic/wiki_mapping/README.md` from the JSON files, and checks that every product move is mapped exactly once (`--check`). |

The remaining folders from the roadmap (`rulesets/`, `characters/`, `engine/`, `observations/`, `annotations/`) are added when V4 work needs them.
