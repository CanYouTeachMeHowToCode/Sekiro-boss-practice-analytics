# Overlay extraction

These scripts read the Sekiro-Debug-Patch overlay from a recording, then build per-animation occurrences. From each frame they read:

- the target's character ID;
- every line of the "Active Anime" list, as an animation ID and an animation time.

## Assumptions and setup

- The recording is 2560×1440, with the dev menu at its default top-left position.
- The pixel positions are constants in `overlay_extract.py`, `time_read2.py` and `cache_lines.py`.
- Run every script with `python -I` in the research environment, which has OpenCV and numpy.
- Use a work directory outside the repository. It holds large caches and review images, and neither is committed. A 412 s recording needs about 2.6 GB of `.npy` caches.
- Before step 1, prepare the work directory:
  1. Copy `research/ground_truth/engine/c7100_tae_ids.txt` and `c7110_tae_ids.txt` into it.
  2. Write their sorted union as `whitelist_c7100_c7110.txt`.

## Run order

| # | Script | Reads | Writes |
|---|---|---|---|
| 1 | `overlay_extract.py templates <video> <work>`, then `extract` | video; hand-labeled frames in `LABELED` | `templates.npz`, `frames.csv`, `video.json` |
| 2 | `overlay_extract2.py <video> <work>` | `frames.csv` (bootstrap labels) | `frames2.csv`, `templates_bootstrap.npy` |
| 3 | `cache_crops.py <video> <work>` | video | `line_min.npy`, `char_min.npy` |
| 4 | `overlay_extract3.py <work>` | caches, `frames2.csv` | `frames3.csv` (character ID; grayscale time reads) |
| 5 | `time_read.py <work>` | caches | `time_bin.npy` (binary time reads) |
| 6 | `overlay_extract4.py <work>` | caches | `frames4.csv` (line 1, adaptive threshold) |
| 7 | `cache_lines.py <video> <work>` | video | `line2_min.npy` … `line5_min.npy` |
| 8 | `read_line.py <work> lineK_min.npy lineK.csv`, for K = 2…5 | caches | `line2.csv` … `line5.csv` |
| 9 | `time_read2.py <work>` | reads from steps 4 and 5 that agree, used as labels | `time2_line1.npy` … `time2_line5.npy` |
| 10 | `occurrences.py <work> <sheet.png> [W DROP] [--auto]` | `corrections.csv`, `restart_review.csv` | `occ_frames.csv`, `occurrences.csv`, restart review sheets |
| 11 | `summarize.py <work> <phase_bounds_json>` | `occurrences.csv`, TAE ID lists | `ids.csv` |
| 12 | `export_observation.py <work> <out_dir> <phase_bounds_json>` | all of the above, plus `char_corrections.csv` | the committed files under `observations/…` |

## Review tools

These scripts make images for checking reads by eye. The results of those checks are recorded in each observation's README and CSV files, not here.

- **Line 1:** `runs.py`, then `sheets.py`. This produces contact sheets of every run.
- **Lines 2–5:**
  1. `lines_union.py` groups lines 2–5 into runs.
  2. `lower_support.py` finds the runs that line 1 does not support.
  3. `lower_sheets.py` makes contact sheets of those runs.
- **Restarts:**
  - Candidates and their sheets: run `occurrences.py --auto` without `restart_review.csv`.
  - Hidden restarts: `occ_span_check.py` and `stall_check.py`.
- **Close-ups:** `zoom_frames.py`, `zoom_region.py`, `full_frames.py`, `strip.py`, `occ_strip.py`, `stack_sheet.py`.
- **Layout probes:** `line_pitch.py`, `pitch_probe.py`, `probe_time_cells.py`, `cell_probe.py`.
