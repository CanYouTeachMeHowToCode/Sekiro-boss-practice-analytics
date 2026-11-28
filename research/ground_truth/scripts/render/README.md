# Rendering moves from the game files

These tools render a boss's moves straight from the game's model and animation files, with no recording. Each move
is drawn as a grey model, with its root motion, and with weapons shown or hidden as the game shows them. The project
owner judged the clips of castle Genichiro's 63 catalog moves enough to recognise and name moves (2026-11-28), so a
new boss's catalog is reviewed on them (CLAUDE.md sections 29 and 34).

Everything they produce is derived from the game's assets: the clips, frames and vertex files go to `render_dir`,
outside the repository, and are never committed (CLAUDE.md section 22). DS Anim Studio's libraries are referenced by
local path and never committed.

## Setup

1. Install the .NET 8 SDK and DS Anim Studio 4.9.3.
2. In `research/ground_truth/local.config`, under `[paths]`, set `game_dir` (as for the other scripts),
   `ds_anim_studio_dir` (the folder holding `SoulsAssetPipeline.dll` and `SoulsFormats.dll`), and optionally
   `render_dir` (default `~/.sekiro-research/render`) and `gt_work` (the AI and TAE dumps of `scripts/ai`, default
   `~/.sekiro-research/gt_work`).
3. Build the tools: `python -I build.py`.

Run everything with `python -I` in the research environment. The .NET tools get the game folder on `PATH`, so the
game's own `oo2core_6_win64.dll` decompresses the archives; the DLL is never copied.

## Tools

| Tool | What it does |
|---|---|
| `posexport/` | Poses a character's model with one animation and writes one vertex file per frame, plus a root-motion file. Usage: `posexport <chr>.chrbnd.dcx <chr>.anibnd.dcx <out dir> <animation id> <frames, e.g. 0-120>`. Its environment switches print diagnostics: `SCALES`, `ROOT`, `CLOTH`, `DEV`, `LIST`. |
| `meshexport/` | Writes a model's vertices and triangles, one row per triangle with its mesh number. |
| `gallery.py` | Renders every branch of every approved catalog move: `python -I gallery.py <worker> <count>` (run several workers at once), then `python -I gallery.py page` for `render_dir/gallery/index.html`. Clips are WebM/VP8: Chrome does not play OpenCV's `mp4v`, and this OpenCV cannot write H.264. |
| `clip_chain.py` | Puts a chain next to a dev-menu recording: recording above, render below, with a lock-on perspective camera. It needs `posexport` frames of each animation. |
| `tag0.py` | A minimal reader for Havok TAG0 tagfiles, such as the behavior graphs in `<chr>.behbnd.dcx`. `types <regex>` prints type layouts; `clips <regex>` prints the clip nodes' crop, start time and speed. |

## What the game files showed

- **Tagfiles**: Sekiro's HKX are TAG0 tagfiles. The animations read through
  `HKX.GenFakeFromTagFile(file, <chr>.compendium)` from the `anibnd`. The behavior graphs need `tag0.py`, because
  SoulsAssetPipeline only reads packfiles and the animation part of tagfiles.
- **Bones**: the model's bones and the animation skeleton share names and rest pose (median distance 0), so a vertex
  is skinned with `inverse(model bind) × animated world`. A bone's local transform needs its scale
  (`GetMatrixScale() * GetMatrix()`).
- **Weapons**: weapons are shown and hidden by bone scale 0/1. For example, in c7100 3020 the katana leaves the hand
  and appears in the sheath from about 0.4 s to 2.0 s.
- **Display masks**: the encounter's NpcParam picks model parts through material prefixes `#NN#`. Castle phase 3
  (c7110) shows mask 2, the katana and sheath, and hides mask 1, the Mortal Blade of the Isshin fight.
- **Root motion**: root motion is stored apart from the bones, one sample per frame or two. c7110 3009 dashes about
  4.8 m in 1.7 s; without it a render looks late.
- **Handedness**: the data is left-handed (the left eye is at +X while the face looks down −Z), so renders mirror X,
  as DS Anim Studio does.
- **TAE**: a TAE entry may play another file (c7100 3013 plays `a000_003014`) or import another entry (3092 imports
  8603). `gallery.py` resolves both from the TAE dump.
- **Cloth**: cloth such as c7100's cape (mesh 27) is simulated in the game. Here it hangs from the chest and turns
  with the shoulders.

## Known gaps

- **Hand-over points**: inside a chain they are estimated, 0.4 s after an animation's last damage window. A recording
  shows the real ones.
- **4110 timing**: the phase-3 throw's follow-up, c7110 4110, kicks about 0.2 s earlier in the game than in the raw
  animation. Its behavior graph clip node and the throw transition are both default (no crop, start 0, speed 1), so
  the cause is still unknown. Candidates are partial-body layers (`PartBlend_*`) and foot IK.
- **Not yet known**: whether rendered clips can serve as recognition references. The next experiment renders each
  attack from several lock-on cameras and measures them on the labelled development fights, alone and added to the
  current references.
