"""Paths for the render tools, from research/ground_truth/local.config ([paths]):

    game_dir             the Sekiro install (read only; its oo2core_6_win64.dll decompresses the archives)
    ds_anim_studio_dir   DS Anim Studio 4.9.3's folder (SoulsAssetPipeline.dll, SoulsFormats.dll; never committed)
    render_dir           where renders go (default ~/.sekiro-research/render): game-derived, never committed
    gt_work              the AI and TAE dumps of scripts/ai (default ~/.sekiro-research/gt_work)
"""
import configparser
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
GT = HERE.parents[1]
_cfg = configparser.ConfigParser()
_cfg.read(GT / "local.config", encoding="utf-8")
_paths = _cfg["paths"] if _cfg.has_section("paths") else {}
GAME = Path(_paths.get("game_dir", ""))
CHR = GAME / "chr"
DSANIM = Path(_paths.get("ds_anim_studio_dir", ""))
RENDER = Path(_paths.get("render_dir", str(Path.home() / ".sekiro-research" / "render")))
GT_WORK = Path(_paths.get("gt_work", str(Path.home() / ".sekiro-research" / "gt_work")))


def exe(tool):
    """The built .NET tool (python -I build.py builds both)."""
    return HERE / tool / "bin" / "Debug" / "net8.0" / f"{tool}.exe"


def tool_env(**extra):
    """Environment for the .NET tools: the game folder on PATH for oo2core (the DLL is not copied)."""
    return dict(os.environ, PATH=f"{GAME};" + os.environ["PATH"], **extra)
