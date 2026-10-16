# Failure attribution (V4 Milestone 1)

Workspace for the first V4 milestone: in the player's own recordings of castle Genichiro (vanilla 1.06), find each failure (damage taken, posture broken, death) and the boss move that caused it. See ROADMAP.md (V4 Milestone 1) and CLAUDE.md sections 37–38.

| Path | What it holds |
|---|---|
| `plan.md` | The milestone plan, in Chinese: recordings, pipeline, labelling page, metrics and the owner's decisions. |
| `scripts/overlay_mask.py` | `mask_overlay(frame)`: paints the dev-menu overlay's live animation lines black. Every frame the pipeline reads goes through it. Run it on a video and a time to write a before/after check image. |

Inputs come from the V3.1 research in `../ground_truth/`: the owner-approved move catalog, the AI chains, and the dev-menu recordings, which are labelled reference data.

Rules:

- Recordings stay local and are never committed; scripts, labels and derived metadata are (CLAUDE.md section 22).
- The dev-menu overlay's live animation lines (below the "[Active Anime]" header) are masked on every frame the system reads: those IDs must never reach a model's input or an evaluation. Only the scripts that build the answer set read them. The header and the lines above it (the character ID, the boss HP bar) stay visible: the phase is visible in the video anyway (owner decision, 2026-10-16).
- The project owner confirms the answer set; the system proposes.
