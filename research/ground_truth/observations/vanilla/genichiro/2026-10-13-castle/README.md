# Genichiro, Ashina Castle: second dev-menu recording (2026-10-13)

- Ruleset: vanilla, assuming Resurrection was off as in the first recording; **to be confirmed by the project owner**.
- Game version: 1.06, assumed unchanged; to be confirmed.
- Encounter: Genichiro Ashina at the top of Ashina Castle. All three phases are in one recording: 450 s, 2560×1440, 60 fps.
  - Phases 1–2 were short, 169 s together.
  - Phase 3 is about 262 s long, three times as long as in the first recording.
  - The player won: the last deathblow is at 428.9–442.7 s, and the boss lies defeated (`010001`) until the end.
- Purpose: plan step 6, targeted recording for the move catalog (`semantic/genichiro_catalog.md`).
- The recording itself stays local. `recording.json` holds its SHA-256, size and format.

**Status.**

- Every animation ID read from the recording has been verified. See [Verification](#verification).
- The phase boundaries are Claude's proposal and wait for the project owner. See [Results](#results).

## Files

The files have the same format as in `../2026-10-09-castle/`, whose README describes the overlay and the method.

| File | Content |
|---|---|
| `recording.json` | Video hash and format, tool versions, the character ID on screen, and the proposed phases. |
| `frames.csv` | One row per video frame: the character ID and the five "Active Anime" lines as `ID@time`. |
| `occurrences.csv` | 705 occurrences, with phase, frames, lines and animation times. |
| `ids.csv` | One row per animation ID seen (84). |
| `coverage.csv` | One row for each of the 196 IDs in the c7100 and c7110 TAE files, made by `scripts/overlay/coverage.py`. |
| `corrections.csv` | Animation-ID reads corrected by eye (15 frames). |
| `char_corrections.csv` | Character-ID reads corrected by eye (5 frames). |
| `restart_review.csv` | Every candidate for "the same animation started again", checked by eye. |

## Method

The pipeline is the one used for the first recording, with three settings now read from the work directory instead of fixed for the first recording:

- `labeled.json`: the frames read by eye for the templates (13 frames of this recording, listed in `recording.json`);
- `segments.json`: the frame ranges with the character line on screen, used by a self-check in `time_read2.py`;
- `video.json`: the frame rate, now also used by `occurrences.py`.

## Verification

- **Line 1.** All 429 runs from the second pass were checked by eye at each run's middle frame.
  - 10 runs were misread by the second pass. Most are 3 and 8 confused under the boss-name banner, plus `008010` read as `003010` (as in the first recording) and `003003` read as `003063`.
  - The adaptive-threshold reader used for the occurrences fixes part of them. The 11 frames it still gets wrong are isolated frames inside a run of the right ID; they are in `corrections.csv`.
  - Run #293, `003063` at 288.9 s, was checked at 3× zoom: it is `003063` (7/81 → 12/81), not `003068`.
- **Lines 2–5.** There are 824 runs.
  - 398 are supported by the same ID on line 1 within 15 frames.
  - The other 426 were checked by eye. Two were misread (`003068` read as `003063`, 4 frames) and are corrected.
  - No `003063` appears on lines 2–5.
- **Restarts.**
  - Two detection passes on the position-specific time reads (W=6 with drop 0.15, then W=4 with drop 0.1) found 55 candidates.
  - All were checked by eye on the `[cur/tot]` counter: 47 are restarts, 8 are not.
- **Hidden restarts.**
  - 12 occurrences advance their animation time less than the wall clock.
  - 9 gaps are explained by frames where the time stands still (hit-stop).
  - The other three were checked:
    - `405002` (frames 306–358) and `009500` (19595–19645) have a misread last time read and no restart;
    - `010001` from 442.65 s is the defeated boss, whose animation time stays at 0.
- **Character ID.** 5 frames under the glow of the first and the last deathblow were corrected by eye.
- **Coverage of the recording.** The overlay is missing only in the first 0.12 s and during the phase transition (169.4–188.4 s), never during combat.

## Results

Proposed phases (to be confirmed by the project owner):

| Phase | Frames | Time (s) | Character | Ends with | Occurrences | Distinct IDs |
|---|---|---|---|---|---|---|
| 1 | 0–4003 | 0.00–66.72 | c7100_0000 | `013100` → `013110` (first deathblow) | 146 | 42 |
| 2 | 4004–10164 | 66.74–169.41 | c7100_0000 | `012000` (second deathblow) | 238 | 49 |
| – | 10165–11192 | 169.42–186.54 | – | transition, no overlay | – | – |
| 3 | 11193–27000 | 186.56–450.02 | c7110_0001 | final deathblow `012000` → `020200` → `013700`, then `010001` | 321 | 60 |

- **Why phase 1 ends at the first deathblow.** The castle AI ends the clash response Kengeki38 (`3030`) with `3067` only when one deathblow is left.
  - The four `3030` before 63 s all end with `3025`.
  - Two of the three after 66.7 s end with `3067`.
  - `3067` occurs only after 66.7 s.
- **The deathblow animations differ from the first recording.** There, phase 1 ended with `012100` → `012110` and phase 2 with `013500` → `013510`.
- **IDs.** 84 distinct IDs; 100 over both recordings. New in this recording: `003032 003040 003041 003063 003080 008011 008012 008551 008704 010001 012000 013100 013110 013700 020200`.
- **Catalog entries that gain runtime evidence** (all phase 3):

  | Entry | Move |
  |---|---|
  | P3-20 | Floating Passage set 1, `3040` → `3041` (at 202.4 s and 225.4 s; the second continues to `3067`) |
  | P3-30 | `3080`, the thrust after the last perfect deflect |
  | P3-17 | `3032`, the third ending of the perilous follow-up |
  | P3-23 | `3050` |
  | P3-26 | `3063`, the other opener of Floating Passage set 2 |
  | P3-03 | `3005` |

- **The 3080 trigger.**
  - In phase 3, `3080` follows `008604` (219.6 s → 220.7 s) and `008704` (312.8 s → 313.8 s). `008704` reuses `008604` in full.
  - In phase 2, `008604` occurs twice (78.0 s and 155.8 s) with no `3080`.
  - This agrees with the AI: only the phase-3 AI answers SpEffect 5030 with `3080`.
- **Act01 was not seen.** `3000` started once in phase 1 (5.8 s) and four times in phase 3, but never continued to `3001`/`3010`. No `3010` occurs; the two second-pass `003010` reads were `008010`.

## Open questions for the project owner

1. Are the phase boundaries right (first deathblow at 63.1–66.7 s, second at 164.6–169.4 s)?
2. Was Resurrection off, and is the game still version 1.06?
