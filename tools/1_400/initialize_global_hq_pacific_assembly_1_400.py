import json
import os
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
SOURCE = OUT_ROOT / "FINAL_PACKS_1_400_Pacific" / "OriginalRichOre_1_400_Pacific_Tiled"
HQ_ROOT = Path(os.environ.get(
    "NOVOATLAS_1_400_HQ_ROOT",
    str(OUT_ROOT / "HQ_1_400_Pacific_FullRoute"),
))
ASSEMBLY = HQ_ROOT / "OriginalRichOre_1_400_HQ_Pacific_FullRoute"
MANIFEST = HQ_ROOT / "world_1_400_global_hq_pacific_manifest.json"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    HQ_ROOT.mkdir(parents=True, exist_ok=True)
    if not ASSEMBLY.exists():
        shutil.copytree(SOURCE, ASSEMBLY)

    meta_path = ASSEMBLY / "pack.mcmeta"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["pack"]["description"] = "NovoAtlas global 1:400 Pacific HQ full-route assembly: original rich ore"
    write_json(meta_path, meta)

    map_info = ASSEMBLY / "data/world/novoatlas/map_info/world.json"
    info = json.loads(map_info.read_text(encoding="utf-8"))
    info["horizontal_scale"] = 1
    info["width"] = 81920
    info["height"] = 46080
    info["description"] = "1:400 Pacific-centered HQ tiled map assembled from the same geographic shard pipeline as the validated 1:200 build."
    write_json(map_info, info)

    if not MANIFEST.exists():
        write_json(
            MANIFEST,
            {
                "assembly_pack": str(ASSEMBLY),
                "scale": "1 block ~= 400 m",
                "route": "Full 1:200-style geographic shard route, 432 regions, Pacific-centered final assembly.",
                "width": 81920,
                "height": 46080,
                "tile_size": 2048,
                "seam_west_lon": -31.5,
                "regions": [],
            },
        )
    print(json.dumps({"hq_root": str(HQ_ROOT), "assembly": str(ASSEMBLY), "manifest": str(MANIFEST)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
