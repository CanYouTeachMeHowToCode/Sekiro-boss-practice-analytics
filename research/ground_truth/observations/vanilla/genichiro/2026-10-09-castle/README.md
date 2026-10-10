# Genichiro, Ashina Castle: dev-menu recording of 2026-10-09

- Ruleset: vanilla. Resurrection was off (confirmed by the project owner).
- Game version: 1.06, the latest. Sekiro-Debug-Patch: the latest version; the exact build was not noted.
- Encounter: Genichiro Ashina at the top of Ashina Castle. All three phases are in one recording: 412 s, 2560×1440, 60 fps. The player died in phase 3.
- The recording itself stays local. `recording.json` holds its SHA-256, size and format.

**Status.**

- Every animation ID read from the recording has been verified. See [Verification](#verification).
- The project owner confirmed the phase boundaries on 2026-10-10.
- Which animations make up which semantic move is not decided here. That is plan step 7, and the project owner confirms it.

## Files

| File | Content |
|---|---|
| `recording.json` | Video hash and format, tool and library versions, the character ID on screen, and the phases. |
| `frames.csv` | One row per video frame: the character ID, then the five "Active Anime" lines written as `ID@time` (for example `003068@0.25`). An empty cell means that line is not on screen. |
| `occurrences.csv` | 732 occurrences. One occurrence is one play of one animation. Each row gives its phase, first and last frame, which lines showed it, and its first and last animation time. |
| `ids.csv` | One row per animation ID (85). Each row says whether the ID is in the c7100 or c7110 TAE, how often it occurred in each phase, and which lines showed it. |
| `coverage.csv` | One row for each of the 196 IDs in the c7100 and c7110 TAE files. Each row says which TAE has the ID, how often it occurred in each phase, and whether it was seen as c7100 (phases 1–2) or as c7110 (phase 3). |
| `corrections.csv` | Animation-ID reads corrected by eye. |
| `char_corrections.csv` | Character-ID reads corrected by eye. |
| `restart_review.csv` | Every candidate for "the same animation started again", each checked by eye and marked `restart` or `no_restart`. |

## What the overlay shows

```text
[●c7100_0000](*)                                         character ID of the target
[Active Anime](64)
◇a000_003068 (0.25) [  7/ 81]                           line 1
 a000_009600 (0.70) [ 21/ 25](完全使いまわし>ID:9700)     line 2 (up to 5 lines seen)
```

- `(t.tt)` is the elapsed time of the animation.
- `[cur/tot]` is the current frame, at 30 fps, over the animation's length.
- Some lines end with a reuse note:
  - `完全使いまわし>ID:n` means the entry fully reuses entry n.
  - `アニメのみ使いまわし>ID:n` means it reuses the motion of n but has its own events.
- At this resolution the lines are 26.7 px apart.
- **The list order does not mean "main animation first".**
  - Example: from 181.8 s to 184.2 s, line 1 stays on the `041500` loop while `003037`, `008010` and `003005` run on lines 2–4.
  - So every line is read, and occurrences are built from all lines together.
  - Reading line 1 alone would miss 132 occurrences of 27 IDs. That count leaves out the `0071xx`/`009xxx` group, which never reaches line 1.
- The same ID never appears on two lines in the same frame.

## Method

The scripts are in `research/ground_truth/scripts/overlay/`, and their run order is in that folder's README.

1. **Animation ID.**
   - Each frame is binarized at the threshold that fits the whitelist best.
   - The six digits sit in fixed 14 px cells.
   - Decoding is limited to the 196 TAE IDs of c7100 and c7110.
   - An unconstrained digit-by-digit read is kept as a cross-check.
2. **Character ID.** Grayscale correlation, computed only over the pixels where `c7100_0000` and `c7110_0001` differ.
3. **Animation time.** Each digit position has its own templates. They are trained on frames where two independent readers agree.
4. **Occurrences.**
   - An occurrence is the longest stretch of frames where an ID is on any line, allowing gaps of up to 2 frames.
   - It is split only at restarts that were checked by eye.

## Verification

- **Line 1.** All 392 runs from the second pass were checked by eye against the overlay, at each run's middle frame.
  - One was misread: `003063` for `003068` at 404.2 s. The background banner text broke the strokes.
  - The adaptive-threshold reader fixes it, and otherwise agrees with the checked reads frame for frame.
- **Lines 2–5.** There are 887 runs.
  - 382 are supported by the same ID on line 1 within 15 frames, so two independent reads agree.
  - The other 505 were checked by eye. The one misread (`003010` for `008010`) is in `corrections.csv`.
- **Restarts.**
  - Two detection passes found 60 candidates. All were checked by eye on the `[cur/tot]` counter: 46 are restarts and 14 are not.
  - One restart frame was set by hand: `041500` at frame 7909.
- **Hidden restarts.**
  - For each occurrence, compare its wall-clock duration with how far its animation time advanced.
  - Every gap between the two is explained, to within 0.1 s, by frames where the animation time stands still (hit-stop or a pause).
  - The one exception was checked by eye: its last time read was wrong, and there was no restart.
- **Character ID.** Six frames under the first deathblow's glow were corrected by eye.
- **Coverage of the recording.** The overlay is missing only at 0–0.52 s and during the phase transition (276.2–324.9 s), never during combat.

## Results

The project owner confirmed these phase boundaries on 2026-10-10.

| Phase | Frames | Time (s) | Character | Ends with | Occurrences | Distinct IDs |
|---|---|---|---|---|---|---|
| 1 | 0–10787 | 0.00–179.80 | c7100_0000 | `012100` → `012110` (first deathblow) | 351 | 48 |
| 2 | 10788–16570 | 179.81–276.19 | c7100_0000 | `013500` → `013510` (second deathblow) | 231 | 52 |
| – | 16571–19493 | 276.21–324.91 | – | transition, no overlay | – | – |
| 3 | 19494–24719 | 324.93–412.02 | c7110_0001 | the player died; the recording ends during `405001` | 150 | 47 |

- **Distinct IDs.** The recording shows 85 distinct IDs.
  - Every ID seen in phases 1–2 is in the c7100 TAE.
  - Every ID seen in phase 3 is in the c7110 TAE.
  - This, with the character line, is the evidence that castle phase 3 is c7110 (Way of Tomoe).
- **Not seen in this recording.**
  - 124 of the 189 c7100 TAE IDs in phases 1–2.
  - 117 of the 164 c7110 TAE IDs in phase 3.
  - Which of these are attacks is plan step 2 (TAE events).
- **Seen only in phase 3:** `003000 003001 003007 003008 003012 003019 003031 003039 003042 003043 005202 008050 008051 008210 008220 008230 008510 405001 405401 405402`.
- **Restarts (46).**
  - Most are loops that reach their last frame and start again: `041500` and `405000/405002/405003` (60–61 frames), `405010` (16 frames) and `008210` (10 frames).
  - The rest are mostly `009600`, which often restarts before it ends.
- **A 1.2 s freeze at 224.2–225.4 s.** The whole picture stands still, as if the game was paused or hitched. `008400` stays at 0.07 s throughout.
- **Reuse notes seen on screen.** These should also be readable from the TAE in step 2.
  - Full reuse: `003092` reuses 8603, `008505` reuses 8504, and `009600` reuses 9700.
  - Animation-only reuse: `003101`–`003103` reuse 3100, and `008050` and `008140` reuse 8010.

## Answered by the project owner (2026-10-10)

1. The phase boundaries are right.
   - Phase 1 ends with the first deathblow.
   - Phase 2 ends with the second.
   - Phase 3 is `c7110_0001`.
2. Phase 3 was not finished: the player died. The owner judges the data from this recording to be enough.
3. The game version is 1.06, the latest.
4. Sekiro-Debug-Patch was the latest version. The exact build was not noted.

## Limitations

- If an animation restarts within its first ~0.1 s, the restart cannot be told apart from one continuous play.
- Anything shown for less than one video frame (1/60 s) cannot be in the recording.
- This is one recording of one fight, so animations that did not happen here are simply absent. Coverage is plan step 6.
