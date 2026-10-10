# Battle AI analysis

These scripts read Genichiro's battle AI from the game files and work out which animations each fight can play. The game files are read-only. Everything decompiled stays in a local work directory: the decompiled AI is a derivative of game code and is not committed. What is committed is the derived results.

Run every script with `python -I` in the research environment. Paths to the game come from `research/ground_truth/local.config`.

## Results

| File | What it holds |
|---|---|
| `characters/genichiro.json` | Every placed Genichiro (c7100 / c7110) in the game. For each placement: map, entity ID, AI script, NpcParam, the boss SpEffects that the AI checks, its health bar (event file, name ID, English and Chinese name), and the encounter this suggests. The encounter labels are proposals until the project owner confirms them. |
| `engine/genichiro_castle_ai_reachability.csv` | One row per TAE entry of c7100 (compared with castle phases 1–2) and c7110 (castle phase 3). Columns: category (`attack` / `bullet` / `other`), recorded occurrences per phase, whether the castle AI can request it in each phase and through which functions, why not when it cannot, and which other Genichiro AI requests it. |
| `engine/genichiro_castle_ai.md` | Flowcharts of the castle AI: the move-selection ladder, adjustments, the choice after a deflect, interrupt reactions, and the animations each option plays. |

`castle_status` values:

- `recorded`: seen in the recording.
- `reachable_not_recorded`: the AI can request it, but the recording does not have it; a candidate to record next.
- `not_reachable`: the castle AI never requests it.
- `recorded_not_requested_by_ai`: seen but not requested by the AI. These are reactions the engine plays itself, such as being hit, guarding, or a deathblow.

## Pipeline

```text
game files (read-only)          scripts                                output
------------------------        -------------------------------        -----------------------------
script/m11_01_00_00.luabnd.dcx  engine/bnd_extract.py  -> <ai>_battle.lua
                                ai/lua50_decompile.py  -> <ai>_battle.txt    (local only)
                                ai/ai_moves.py         -> <ai>_moves.json    (local only)
chr/c7100|c7110.anibnd.dcx      engine/bnd_extract.py  -> <c>.tae
  + DS Anim Studio template     engine/tae_dump.py     -> <c>_tae.json       (local only)
observations/.../coverage.csv   ai/reachability.py     -> engine/genichiro_castle_ai_reachability.csv
maps, params, events, text      ai/encounters.py       -> characters/genichiro.json
                                ai/ai_flowchart.py     -> engine/genichiro_castle_ai.md (with a hand-written head)
```

Example, with `<work>` outside the repository:

```text
python -I research/ground_truth/scripts/engine/bnd_extract.py <game>/script/m11_01_00_00.luabnd.dcx 710000_battle.lua <work>/710000_battle.lua
python -I research/ground_truth/scripts/ai/lua50_decompile.py <work>/710000_battle.lua <work>/710000_battle.txt
python -I research/ground_truth/scripts/ai/ai_moves.py <work>/710000_battle.txt <work>/710000_moves.json
    (repeat for 711000, 710300, 711300)
python -I research/ground_truth/scripts/engine/bnd_extract.py <game>/chr/c7100.anibnd.dcx c7100.tae <work>/c7100.tae
python -I research/ground_truth/scripts/engine/tae_dump.py <work>/c7100.tae <DS Anim Studio>/Res/TAE.Template.SDT.xml <work>/c7100_tae.json
    (repeat for c7110)
python -I research/ground_truth/scripts/ai/reachability.py <work> <work> research/ground_truth/observations/vanilla/genichiro/2026-10-09-castle/coverage.csv research/ground_truth/engine/genichiro_castle_ai_reachability.csv
python -I research/ground_truth/scripts/ai/encounters.py <work> research/ground_truth/characters/genichiro.json
python -I research/ground_truth/scripts/ai/ai_flowchart.py <work>/710000_battle.txt "AI 710000(c7100)"
```

## Scripts

| Script | What it does |
|---|---|
| `lua50_decompile.py` | Decompiles stripped Lua 5.0 bytecode (FromSoftware AI scripts) into readable pseudo-Lua: registers become r0, r1, …; single-use temporaries are inlined; if / elseif / else are rebuilt where the jumps allow. |
| `ai_moves.py` | For each function of a battle goal, lists the animation IDs it requests (`AddSubGoal`), and whether Activate / Kengeki_Activate ever weights it or something calls it. Also lists the IDs that appear only as cooldown keys. |
| `reachability.py` | The castle result table. The castle-specific rules it applies on top of `ai_moves.py`, each read from the decompiled script, are listed in its docstring. |
| `encounters.py` | Finds every c7100 / c7110 placement and what it is wired to (maps, params, events, text). |
| `ai_flowchart.py` | Draws one battle goal as Mermaid flowcharts and Markdown trees. |
| `params.py`, `emevd.py` | Minimal readers for PARAM tables and event scripts (EMEVD). |

## Validation

The method was checked against the 2026-10-09 recording. Every recorded attack and bullet animation is reachable by the castle AI in the phase where it was recorded:

- phases 1–2: 22 of 22 attack, 6 of 6 bullet;
- phase 3: 16 of 16 attack, 4 of 4 bullet.

The two phase-2-only requests (3017 and 3067) agree with the recording: 3067 occurs 0 times in phase 1 and 4 times in phase 2.

## Limits

- "Reachable" means some condition lets the AI request the animation. It says nothing about how often.
- Most SpEffect, timer and counter numbers in the conditions have no known meaning yet.
- Reactions the engine plays itself (hit, guard, deathblow) are not in the AI scripts.
