"""The recording worker's data folder, from the research work folder (V4 M3).

Usage:
    python -I export_analysis_data.py write <folder>                 build the folder
    python -I export_analysis_data.py verify <folder> <recording id | all-test>...
        predict recordings with the folder's references and compare with move_match.py predict, row by row

The worker (analysis/sekiro_analysis/pipeline.py) reads, from this folder only:
    death_mask.npy                 the 死 glyph mask (death_screen.py)
    glyph_dalei.npy                the 打雷 glyph template (reversal.py)
    name_templates.npz             the boss-name templates (content_check.py)
    scene_refs.npz                 the castle-roof scene features (content_check.py)
    dinov2_small14.safetensors     the DINOv2 small14 weights timm downloaded (the worker has no network)
    references.npz/.json           the move references: what move_match.py predict uses for a recording that is not a
                                   development recording (every dev-menu reference, the owner's labelled hits, the merge
                                   windows), in the same order
The first four are cut from the game's images and the references come from the owner's recordings, so the folder
stays local like the work folder; never commit it.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, recordings, work_dir  # noqa: E402
from failure_answers import MOVES, read  # noqa: E402
from move_match import Rec, references, settings  # noqa: E402
from sekiro_analysis import moves as mm  # noqa: E402
from sekiro_analysis import references as saved  # noqa: E402
from sekiro_analysis.boss_features import MODEL  # noqa: E402
from sekiro_analysis.pipeline import WEIGHTS, Data  # noqa: E402


def weights_file():
    from huggingface_hub import try_to_load_from_cache
    path = try_to_load_from_cache("timm/" + MODEL, "model.safetensors")
    if not isinstance(path, str):
        sys.exit(f"the {MODEL} weights are not in the Hugging Face cache: run boss_features.py once to download them")
    return Path(path)


def write(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for src, name in [(WORK / "death_mask.npy", "death_mask.npy"), (WORK / "content" / "glyph_dalei.npy", "glyph_dalei.npy"),
                      (WORK / "content" / "name_templates.npz", "name_templates.npz"),
                      (WORK / "content" / "scene_refs.npz", "scene_refs.npz"), (weights_file(), WEIGHTS)]:
        shutil.copyfile(src, folder / name)
    st = settings()
    refs, gaps = references(recordings(), st)
    saved.save(folder, refs, gaps, MOVES, st, about="move references of version 2, from the research work folder")
    print(f"{folder}: {len(refs)} references, {len(gaps)} merge windows, {len(MOVES)} moves; missing: "
          f"{Data(folder).missing() or 'nothing'}")


def verify(folder, ids):
    """Each recording predicted twice, with the research references (in memory, as move_match.py predict) and with
    the folder's: the rows must be the same."""
    st, recs = settings(), recordings()
    refs, gaps, moves, st_saved = saved.load(folder)
    assert st_saved == st, (st_saved, st)
    if ids == ["all-test"]:
        ids = [i for i, r in recs.items() if r.get("set") in ("test", "scenario", "simulation")
               and (work_dir(i) / "boss_feats_small14.npy").exists()]
    differ = 0
    for rec_id in ids:
        q = Rec(rec_id, recs[rec_id], st["model"], st["part"], st["trend"])
        mem_refs, mem_gaps = references(recs, st, rec_id)
        a = mm.predict_rows(q, read(work_dir(rec_id) / "events.csv"), mem_refs, mem_gaps, MOVES, st)
        q2 = mm.Rec(work_dir(rec_id), st["model"], st["part"], st["trend"])
        b = mm.predict_rows(q2, read(work_dir(rec_id) / "events.csv"), refs, gaps, moves, st)
        # and against the failure_predictions.csv already there (written by the code before the package), byte by byte
        tmp = work_dir(rec_id) / "failure_predictions.verify.csv"
        mm.write_rows(b, tmp)
        old = work_dir(rec_id) / "failure_predictions.csv"
        as_before = old.exists() and old.read_bytes() == tmp.read_bytes()
        tmp.unlink()
        same = a == b and as_before
        differ += not same
        print(f"{rec_id}: {len(a)} failures, references {'same' if a == b else 'DIFFERENT'}, "
              f"file {'as before' if as_before else 'NOT as before'}", flush=True)
    print(f"{len(ids) - differ} of {len(ids)} recordings the same")
    return differ == 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "write":
        write(sys.argv[2])
    elif sys.argv[1] == "verify":
        sys.exit(0 if verify(sys.argv[2], sys.argv[3:]) else 1)
