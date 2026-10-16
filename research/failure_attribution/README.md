# Failure attribution (V4 Milestone 1)

Workspace for the first V4 milestone: in the player's own recordings of castle Genichiro (vanilla 1.06), find each failure (damage taken, posture broken, death) and the boss move that caused it. See ROADMAP.md (V4 Milestone 1) and CLAUDE.md sections 37–38.

| Path | What it holds |
|---|---|
| `plan.md` | The milestone plan, in Chinese: recordings, pipeline, labelling page, metrics and the owner's decisions. |
| `recordings.json` | The recordings used here: id, file name, SHA-256, ruleset, whether the dev-menu overlay is on. The videos stay in `local.config`'s `recordings_dir`. |
| `scripts/hud_pipeline.py` | One recording (or `all`): HUD cache, series, events and review thumbnails into `work/<id>/` (gitignored, rebuilt from the video). |
| `scripts/events.py` | Damage, death, resurrection and posture-break events from the HUD series, with the exclusions: drops right before the HUD fades (deathblow cutscenes, the boss's defeat), dark bars without a killing hit, and posture clears around a death or a resurrection. The posture-break rule is the owner's definition (2026-10-16). |
| `scripts/review_events.py` | Local review page (127.0.0.1:8770): each detected event with its thumbnail and a player that starts two seconds before it; the owner marks correct / wrong / unsure and adds missed events. Writes `research/ground_truth/annotations/<ruleset>/genichiro/<recording>/hud_events.csv`. Open it in Chrome or Edge: VS Code's built-in browser cannot play the H.264 recordings. |
| `scripts/common.py` | Shared paths: the recordings registry, the video location, the work and annotation folders. |
| `scripts/hud_read.py` | Reads Wolf's HP (red part, and the pale just-lost part) and posture (the bright part growing from the centre, yellow to orange-red as it fills) from the HUD. `cache` decodes a video once and keeps per-column HUD colours; `series` turns them into one row per frame. |
| `scripts/overlay_mask.py` | `mask_overlay(frame)`: paints the dev-menu overlay's live animation lines black. Every frame the pipeline reads goes through it. Run it on a video and a time to write a before/after check image. |

Inputs come from the V3.1 research in `../ground_truth/`: the owner-approved move catalog, the AI chains, and the dev-menu recordings, which are labelled reference data.

Rules:

- Recordings stay local and are never committed; scripts, labels and derived metadata are (CLAUDE.md section 22).
- The dev-menu overlay's live animation lines (below the "[Active Anime]" header) are masked on every frame the system reads: those IDs must never reach a model's input or an evaluation. Only the scripts that build the answer set read them. The header and the lines above it (the character ID, the boss HP bar) stay visible: the phase is visible in the video anyway (owner decision, 2026-10-16).
- The project owner confirms the answer set; the system proposes.
