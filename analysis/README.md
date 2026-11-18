# analysis: the failure attribution pipeline

The V4 failure attribution pipeline (version 2: frozen 2026-11-12, passed its blind test 2026-11-13; version 3,
2026-11-18, reads other frame rates and is version 2 at 60 fps) as one Python package, `sekiro_analysis`. The research scripts in `research/failure_attribution/scripts/` and the recording worker
(`backend/app/worker/`) run the same code from here.

| Module | Step |
|---|---|
| `overlay_mask.py` | masks the dev-menu overlay's animation lines in every frame the pipeline reads |
| `hud_read.py` | Wolf's HP, posture and the boss HP from the HUD (cache, then a series per frame) |
| `death_screen.py` | the 死 death screen |
| `events.py` | failure events: damage, death, posture break (and deathblows, resurrections) |
| `reversal.py` | lightning reversals that cost HP, which are not failures |
| `lockon.py`, `boss_track.py` | the boss's position from the lock-on dot, and a crop of the boss per frame |
| `boss_features.py` | DINOv2 features of the crops |
| `moves.py` | the move behind each failure, merged failures, how sure |
| `references.py` | the move references, saved for the worker |
| `content_check.py` | the upload check: Sekiro HUD, castle Genichiro's name, the castle roof |
| `pipeline.py` | the worker's entry point: `check()` and `analyze()` |
| `decode.py` | checks that OpenCV decodes video exactly as in the research, on a synthetic sample (`decode_sample.mp4`) |
| `sampling.py` | how often the steps read a video: 30 samples a second at any frame rate (version 3) |

## The data folder

The pipeline reads everything taken from the game's images and the owner's recordings from a local folder, never
from the repository: the 死 mask, the 打雷 glyph, the boss-name templates, the castle-roof scene features, the move
references and the DINOv2 weights. Write it from the research work folder:

```bash
python -I research/failure_attribution/scripts/export_analysis_data.py write <folder>
python -I research/failure_attribution/scripts/export_analysis_data.py verify <folder> all-test
```

`verify` predicts every test, scenario and simulation recording with the folder's references and checks the result is
byte for byte what `move_match.py predict` wrote. Docker Compose mounts the folder into the worker
(`ANALYSIS_DATA` in `.env`, default `./analysis-data`).

## Changing the code

Version 2 is frozen: a change here must leave every labelled recording's outputs exactly as they were, or be measured
as a new version (research/failure_attribution/plan_m2.md). The move of the steps into this package was checked that
way: the whole pipeline rerun from the videos on three recordings, and the predictions of every labelled recording.

On the GPU (`device="cuda"`) the features are computed as in research, in fp16; on the CPU, in fp32, which can move
the scores slightly.

## Decoding

Every step reads decoded pixels, and OpenCV decodes with the FFmpeg bundled in its wheel. The research ran on Windows
with opencv-python-headless 5.0.0.93 (FFmpeg 7.1). The Linux wheel of the same version bundles FFmpeg 8, whose
colour conversion gives other pixels (up to 21 levels apart in about half the values); in the worker that brought back
a false damage event on a test recording. The Linux 4.12.0.88 wheel (FFmpeg 5.1) gives the research's pixels, so
`requirements.txt` pins it on Linux. With it, the steps that read the video gave byte-identical outputs on every
labelled recording without the overlay. `python -m sekiro_analysis.decode` checks a platform's decoding on a synthetic
sample, and the worker refuses to analyse when it differs; change OpenCV only together with that check and a rerun.

## Frame rates (version 3)

Version 2 was built and measured on 60 fps recordings, read every other frame: 30 samples a second, and every constant
that counts samples (events.py's LINE_HOLD and LINE_GAP, moves.py's RATE and the windows it turns into rows) means a
30th of a second. A 30 fps upload read the same way gave 15 samples a second: the windows covered twice the time, the
boss's motion ran at twice the references' speed, and a window near the start of the video ran past it (every
candidate -1). Version 3 (`sampling.py`) reads 30 samples a second whatever the rate: every frame at 30 fps, every
other at 60. The steps that sample at other rates (the lightning reversal at 20 a second, the content check's name
window at 10) follow the same rule, from the nominal rate (the multiple of 30 nearest the file's).

At 60 fps version 3 reads the same frames as version 2, so its outputs are version 2's, byte for byte: every registered
recording reads as 59.5–60.005 fps, and a full rerun of both versions on three of them gave identical files. The
attribution has been measured at 60 fps only: the worker accepts 30 fps, and the report says its results are for
reference only (`checks.VALIDATED_FRAME_RATES`), until new 30 fps fights labelled blind pass under the plan_m2.md
protocol. `research/failure_attribution/scripts/sim_frame_rate.py` is a development check on frame-dropped copies of
the labelled recordings, not that measurement.
