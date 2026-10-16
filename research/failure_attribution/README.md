# Failure attribution (V4 Milestone 1)

Workspace for the first V4 milestone: in the player's own recordings of castle Genichiro (vanilla 1.06), find each failure (damage taken, posture broken, death) and the boss move that caused it. See ROADMAP.md (V4 Milestone 1) and CLAUDE.md sections 37–38.

| Path | What it holds |
|---|---|
| `plan.md` | The milestone plan, in Chinese: recordings, pipeline, labelling page, metrics and the owner's decisions. |
| `recordings.json` | The recordings used here: id, file name, SHA-256, ruleset, whether the dev-menu overlay is on. The videos stay in `local.config`'s `recordings_dir`. |
| `scripts/register.py` | Adds new videos in `recordings_dir` to `recordings.json` (id from the file date, SHA-256, overlay off unless `--overlay`) and prints their size, frame rate and length. |
| `scripts/hud_pipeline.py` | One recording (or `all`): HUD cache, series, events, boss track and features, the moves behind the failures (answers from the overlay for a dev-menu recording, predictions for any other) and review thumbnails into `work/<id>/` (gitignored, rebuilt from the video). |
| `scripts/events.py` | Damage, death, resurrection, posture-break and deathblow events from the HUD series, with the exclusions: drops right before the HUD fades (deathblow cutscenes, the boss's defeat), dark bars without a killing hit, and posture clears around a death, a resurrection or Wolf's own deathblow. A posture break is its break frame (the bar turns into a wide red line); a deathblow is the boss HP bar cleared in one frame. The rules are the owner's (2026-10-16). |
| `scripts/failure_answers.py` | For the dev-menu recordings: the move behind every failure, from the overlay's animation IDs (V3.1 observations), the TAE attack windows, the chain check and the product moveset, with the owner's merge rules (one play of a move is one failure; a death joins the hit that killed; a posture break takes the hit that broke it and the hits while staggered). Writes `work/<id>/failure_answers.csv`. |
| `scripts/review_events.py` | Local review page (127.0.0.1:8770). 事件 view: each detected event with its thumbnail and a player that starts two seconds before it; the owner marks correct / wrong / unsure and adds missed events (`hud_events.csv`). 招式 view: each failure with its move, from the overlay for a dev-menu recording or predicted with three candidate buttons for any other; the owner confirms or picks the right product move and can merge a failure into the one before (`failure_moves.csv`), and a side panel counts failures per move. Both files are in `research/ground_truth/annotations/<ruleset>/genichiro/<recording>/`. Open it in Chrome or Edge: VS Code's built-in browser cannot play the H.264 recordings. |
| `scripts/common.py` | Shared paths: the recordings registry, the video location, the work and annotation folders. |
| `scripts/hud_read.py` | Reads Wolf's HP (red part, and the pale just-lost part), posture (the bright part growing from the centre, yellow to orange-red as it fills), the posture-break line and the boss HP bar from the HUD. `cache` decodes a video once and keeps per-column HUD colours; `series` turns them into one row per frame. |
| `scripts/lockon.py` | Finds the white lock-on dot that the game draws on the locked-on boss: a disc template on the half-size frame, a full-size check (bright, even, unsaturated, brighter than its ring), and a tracker that prefers the dot near the last one. |
| `scripts/boss_track.py` | One recording (or `all`): the lock-on dot every second frame and a 640-pixel crop of the boss below it, after `mask_overlay()`, into `work/<id>/boss_track.csv` and `boss_crops.npz`. |
| `scripts/boss_features.py` | DINOv2 features (timm, on the GPU) of the boss crops into `work/<id>/boss_feats_<model>.npy`: class token and mean patch token, each normalised. |
| `scripts/move_match.py` | Move recognition, first version. The boss crops from 1.5 s before a failure's hit to 1.0 s after it are compared with the same span around every reference hit in the dev-menu recordings (labelled from the overlay as in `failure_answers.py`). The local mean feature is subtracted first so the arena and light drop out. The product moves of the phase are ranked by their best reference. `eval` measures it on the owner-checked answers; `predict` writes a recording's failures with the top three moves (`work/<id>/failure_predictions.csv`), merging hits of one move without the overlay's AI chain. |
| `scripts/overlay_mask.py` | `mask_overlay(frame)`: paints the dev-menu overlay's live animation lines black. Every frame the pipeline reads goes through it. Run it on a video and a time to write a before/after check image. |

Inputs come from the V3.1 research in `../ground_truth/`: the owner-approved move catalog, the AI chains, and the dev-menu recordings, which are labelled reference data.

Rules:

- Recordings stay local and are never committed; scripts, labels and derived metadata are (CLAUDE.md section 22).
- The dev-menu overlay's live animation lines (below the "[Active Anime]" header) are masked on every frame the system reads: those IDs must never reach a model's input or an evaluation. Only the scripts that build the answer set read them. The header and the lines above it (the character ID, the boss HP bar) stay visible: the phase is visible in the video anyway (owner decision, 2026-10-16).
- The project owner confirms the answer set; the system proposes.
