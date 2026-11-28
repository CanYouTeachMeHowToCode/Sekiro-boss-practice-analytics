"""Build the .NET render tools against the local DS Anim Studio libraries: python -I build.py"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DSANIM, HERE  # noqa: E402

if not (DSANIM / "SoulsAssetPipeline.dll").exists():
    sys.exit(f"set ds_anim_studio_dir in research/ground_truth/local.config (now: {DSANIM})")
for tool in ("posexport", "meshexport"):
    subprocess.run(["dotnet", "build", str(HERE / tool), "-nologo", "-v", "q", f"-p:DSAnimStudioDir={DSANIM}"], check=True)
    print("built", tool)
