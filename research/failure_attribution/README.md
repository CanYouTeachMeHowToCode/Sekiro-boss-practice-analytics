# Failure attribution (V4 Milestone 1)

Workspace for the first V4 milestone: in the player's own recordings of castle Genichiro (vanilla 1.06), find each failure (damage taken, posture broken, death) and the boss move that caused it. See ROADMAP.md (V4 Milestone 1) and CLAUDE.md sections 37–38.

| Path | What it holds |
|---|---|
| `plan.md` | The milestone plan, in Chinese: recordings, pipeline, labelling page, metrics and the owner's decisions. |

Inputs come from the V3.1 research in `../ground_truth/`: the owner-approved move catalog, the AI chains, and the dev-menu recordings, which are labelled reference data.

Rules:

- Recordings stay local and are never committed; scripts, labels and derived metadata are (CLAUDE.md section 22).
- The dev-menu overlay is masked on every frame the system reads: its animation and character IDs must never reach a model's input or an evaluation. Only the scripts that build the answer set read it.
- The project owner confirms the answer set; the system proposes.
