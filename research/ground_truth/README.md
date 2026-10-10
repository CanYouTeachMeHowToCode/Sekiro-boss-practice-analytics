# Ground truth research

Workspace for V4, Combat Ground Truth. See ROADMAP.md and CLAUDE.md (sections 18–36) for the plan.

It is kept separate from the production application: nothing here is read by the backend or the frontend, and nothing here changes the production database.

## Rules

- **The project owner decides what is ground truth.** Tools and Claude gather evidence, compare sources and propose; they never mark a semantic move, an engine mapping or a phase structure as verified.
- Every observation carries its ruleset (`vanilla`, `resurrection`).
- Do not commit proprietary game assets: game binaries, extracted archives, animation bundles, models or textures. Commit scripts, metadata, mappings, identifiers, hashes and annotations only.

## Third-party tools

The research relies on these community tools. They are run locally and are **not** included in this repository; get them from their own pages.

| Tool | Author | Used for | License / terms |
|---|---|---|---|
| [Sekiro-Debug-Patch](https://github.com/yuiamoroll/Sekiro-Debug-Patch) | yuiamoroll (overlay with help from Enlisted; sub-option patches found by Pav) | Enables Sekiro's developer debug menu, whose overlay shows the boss's current animation ID during recorded fights | No license file. The README describes it as a modder's resource that may be used freely, and asks to be contacted before it is packaged with another mod that is sold. Do not redistribute it from this repository. |
| [DS Anim Studio](https://github.com/Meowmaritus/DSAnimStudio) | Meowmaritus | Opening and inspecting character animation files (TAE events, AtkParam references, animation previews) | GPL-3.0 |

Every recording and extracted dataset records the tool versions it was made with, for example the Sekiro-Debug-Patch commit (latest is `88d51093de`, 2021-11-06, as there are no tagged releases) and the DS Anim Studio version (2.4.1 at the start of V4).

## Contents

| Path | What it holds |
|---|---|
| `genichiro-plan.md` | Step-by-step plan (in Chinese) for capturing every vanilla Genichiro move with verified accuracy: static animation set, overlay extraction, recording protocol, coverage review, semantic catalog. |
| `semantic/wiki_mapping/` | Per-boss mapping between product moves, Fextralife entries and Fandom entries, made during V3 M5. It is the starting candidate list for the V4 semantic catalog and the baseline for measuring the gap to engine-level ground truth. |
| `scripts/wiki_mapping_report.py` | Rebuilds `semantic/wiki_mapping/README.md` from the JSON files, and checks that every product move is mapped exactly once (`--check`). |
| `rulesets/` | One file per ruleset with the game version and the tool versions used to observe it (`vanilla.json`). |
| `local.config.example` | Template for `local.config` (gitignored), which holds this machine's game and recording folders. |
| `engine/` | Animation IDs listed in each character's TAE file (`c7100_tae_ids.txt`, `c7110_tae_ids.txt`), extracted with `scripts/engine/`. |
| `scripts/engine/` | Read-only extraction from the game's `.anibnd.dcx` files: BND4 file list, single-file extraction, TAE animation IDs. |
| `scripts/overlay/` | Reads the dev-menu overlay from a recording (character ID, every "Active Anime" line, animation time), builds per-animation occurrences, and makes the review sheets used to check them by eye. Run order is in its README. |
| `observations/<ruleset>/<boss>/<recording>/` | Verified observations from one recording, with its hash, tool versions, corrections and open questions. The recording itself stays local. |

The remaining folders from the roadmap (`characters/`, `annotations/`) are added when V4 work needs them.
