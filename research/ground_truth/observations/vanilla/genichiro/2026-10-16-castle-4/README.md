# Genichiro, Ashina Castle: dev-menu recording 4 of 2026-10-16

- Ruleset: vanilla 1.06, the owner's setup for V4 M1 (not confirmed separately for this recording).
- Encounter: Genichiro Ashina at the top of Ashina Castle, all three phases: 378 s, 2560×1440, 60 fps.
  - Phase 1: 0.0–88.3 s. It ends with the deathblow animation `012000` (83.1–88.3 s); the deathblow animations differ between fights.
  - Phase 2: 88.3–174.8 s, up to the cutscene.
  - Phase 3: 197.7–377.8 s.
  - The player won: three deathblows (85.1 s, 172.1 s, 363.8 s); the boss lies defeated (`010001`) from 375.6 s, with one death at 306.2 s, resurrected at 310.3 s.
- Purpose: V4 M1, more labelled reference fights for the failure attribution (`research/failure_attribution/`).
- The recording itself stays local. `recording.json` holds its SHA-256 and format.

**Status: automatic reads, not every read checked by eye.** The two V3.1 recordings were checked read by read; this one
was not. What was checked is listed under Verification. The phases were proposed from the HUD; the owner approved them on 2026-10-16, with the recording's
failure events and moves (`research/ground_truth/annotations/vanilla/genichiro/2026-10-16-castle-4/`).

## Files

Same format as `../2026-10-09-castle/`, whose README describes the overlay and the method.

| File | Content |
|---|---|
| `recording.json` | Video hash and format, the character ID on screen, the phases, the verification level. |
| `frames.csv` | One row per video frame: the character ID and the five "Active Anime" lines as `ID@time`. |
| `occurrences.csv` | 642 occurrences, with phase, frames, lines and animation times. |
| `ids.csv` | One row per animation ID seen (75). |
| `coverage.csv` | One row for each of the 196 IDs in the c7100 and c7110 TAE files. |
| `corrections.csv` | Animation-ID reads corrected by eye (18 frames). |
| `char_corrections.csv` | Character-ID reads corrected by eye (none). |
| `restart_review.csv` | Candidates for "the same animation started again". |

## Verification

- Digit and character templates come from 12 frames of this recording read by eye (`recording.json`).
- Reads are limited to the 196 TAE IDs; on line 1 the time read agrees with the independent reader on
  13963 of 13979 labelled frames.
- **The chain check** (`../chain_check.md`): every transition is checked against the owner-approved AI chains. A misread
  usually breaks a chain. Each flagged place was looked at in the video:
  - 18 frames were misreads under the boss-name banner, which covers the ID digits (3↔8, 0↔8: `003063` for
    `003068`, `003030` for `003080`, `003003` for `003000`, `003010` for `008010`, `003013` for `003018`); they are in
    `corrections.csv`;
  - a scan for short runs of a confusable ID inside another found no other misread.
  After the corrections, no transition in this recording is left unexplained.
- Restarts: 33 candidates found automatically; the two that the chain check flagged (`003062` at frame 19148, `003007` at frame 21671) were checked by eye and are not restarts; the other 31 were not checked.
- Not checked: the reads that the chain check and the scan cannot flag (a misread that still fits some chain).
