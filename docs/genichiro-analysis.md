# Automatic failure analysis for Genichiro: how it got here

[中文](genichiro-analysis.zh-CN.md)

A player uploads a recording of their fight against Genichiro Ashina (*Sekiro*). The site finds every time they lost HP,
had their posture broken or died, and says which of Genichiro's moves did it, with a short clip of each failure. When
the system is not sure, the report says so ("might be A or B") instead of guessing.

This page is the short story of how that pipeline was built: what each version changed, why, and what it fixed. The
full plans and measurements are in [`research/failure_attribution/`](../research/failure_attribution/).

## How it works

```text
recording ─► HUD reader ─► failure events (HP loss, posture break, death; phase from the HUD)
                                   │
                                   ▼
             boss crop around the lock-on point, 1.5 s before to 1.0 s after each hit
                                   │
                                   ▼
             DINOv2 image features ─► compared with labelled reference hits ─► move + "how sure"
                                   │
                                   ▼
                     failure report with a clip of each failure
```

The references come from two sources. The first is fights recorded with the game's developer overlay, which prints the
boss's current animation ID on screen, so every hit is labelled exactly. The second is fights the owner labelled by
hand. What counts as a "move" comes from the game itself. The boss's battle AI was decompiled and his animation data
(TAE) read, which gave a catalog of 63 moves from 45 AI chains. The project owner approved every entry.

## Iterations

| Version | When | What changed | Why | Result |
|---|---|---|---|---|
| Ground truth | Oct 9–15 | Decompiled the boss AI, read the animation event data, built a reader for the developer overlay, catalogued every move | Wiki move lists were incomplete and disagreed with each other; recognition needs a trustworthy list of what can actually happen | 63 moves, owner-approved; all 353 animation entries classified |
| v1: prototype | Oct 16 | HUD event detection; move recognition by looking back from each hit | First check that failures and their moves can be found without manual input | All failure events right; correct move first in 88% of failures, in the top three in 93% (optimistic: two rules were added after looking at one of the test fights) |
| Reliability test | Oct 25 | A fixed protocol: freeze the code, record new fights, label them blind, measure once, never tune on test fights | The v1 numbers came from fights the parameters had seen | Precision 97%, recall 100%; 81% of answers sure, 93% of those right |
| v2: what a "move" is | Nov 12–13 | A failure is classified by the action that hit and the response it needs, not by the AI chain (an arrow inside a combo is its own move; thrusts you must Mikiri are one move) | AI-chain moves did not match what a player has to practise, and look-alike chains caused errors | Precision and recall 100%; 86% sure, 93% right (100% after the owner rechecked four labels) |
| Upload and report | Nov 18 | Upload page, background worker, failure report with clips; the worker's output checked to equal the research tools' | Turn the research pipeline into a product | End to end, the report equals the research tools' output |
| v3: any frame rate | Nov 18 | Sample 30 frames a second whatever the recording's rate | The first testers recorded at 30 fps; timing assumed 60 fps | Identical to v2 at 60 fps |
| v4: phase from the HUD | Nov 20–24 | Read the fight's phase from the deathblow dots and the boss's name instead of counting deathblows | A tester's darker footage hid every deathblow, so every failure was "phase 1" and got phase-1 moves | 30 fps validated on six new blind fights: precision 95%, recall 100%, all sure answers right |
| v5: the moves it saw least | Nov 24–27 | Targeted recordings of perilous grabs; testers' labelled fights as references; the grabs' follow-up animations, which the ground truth had missed; tool to compare versions on all labelled data | A tester's upload had many "unsure" answers; grabs had only 5–7 references each | Grabs answered right and sure 3 → 8 of 11; no false failures |
| Rendering from game files | Nov 28 | Every catalog move rendered from the game's model and animation files: weapons, root motion and display masks as in the game | 17 bosses would need weeks of recording and review; the owner's time is the bottleneck | All 63 moves as clips; the owner judged them enough to recognise and name moves |

## Problems solved along the way

- **No ground truth.** Community wikis disagreed, so the move list comes from the game's own AI and animation data, and the project owner approves every entry.
- **Honest numbers.** Every version is measured the same way: frozen code, new fights labelled blind, one run. Results below the bar are reported as they are, not tuned away.
- **"Unsure" instead of wrong.** The report gives a move only when the best match clearly beats the others; otherwise it shows the top candidates.
- **Real players' recordings.** Each tester problem became a version: 30 fps recordings (v3), darker footage (v4), rare moves (v5).
- **Same results in research and production.** The worker decodes video exactly like the research tools (pinned OpenCV, checked frame by frame), and exported references reproduce research predictions byte for byte.
- **Scaling to more bosses.** The 17 refightable boss fights use 11 character models. Rendering moves from the game files replaces most recording for reviewing and naming moves.

## Stack

FastAPI, PostgreSQL, SQLAlchemy and Alembic; React and TypeScript; Docker Compose; a Python analysis package (OpenCV,
PyTorch and DINOv2) run by a background worker; .NET tools for the game files; a private test on a Google Cloud VM.
