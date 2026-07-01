import argparse
import importlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORLD_SCRIPTS = Path(os.environ.get("NOVOATLAS_PIPELINE_ROOT", PROJECT_ROOT / "tools" / "pipeline"))
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
REAL_CACHE = Path(os.environ.get("NOVOATLAS_CACHE_ROOT", PROJECT_ROOT / "cache"))
GLOBAL_WIDTH = 163840
GLOBAL_HEIGHT = 92160


def slugify(text):
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text or "region"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lonlat_to_world(lon, lat):
    local_x = round((lon + 180.0) / 360.0 * (GLOBAL_WIDTH - 1))
    local_z = round((90.0 - lat) / 180.0 * (GLOBAL_HEIGHT - 1))
    return int(local_x - GLOBAL_WIDTH // 2), int(local_z - GLOBAL_HEIGHT // 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--west", type=float, required=True)
    parser.add_argument("--south", type=float, required=True)
    parser.add_argument("--east", type=float, required=True)
    parser.add_argument("--north", type=float, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(WORLD_SCRIPTS))
    shard = importlib.import_module("make_world_v2_200_east_asia_shard")
    original_get_worldcover_tile = shard.get_worldcover_tile

    def robust_get_worldcover_tile(z, x, y):
        last_error = None
        for attempt in range(5):
            try:
                return original_get_worldcover_tile(z, x, y)
            except Exception as exc:
                last_error = exc
                time.sleep(3.0 + attempt * 2.0)
        raise last_error

    shard.get_worldcover_tile = robust_get_worldcover_tile

    slug = slugify(args.name)
    width = round((args.east - args.west) / 360.0 * GLOBAL_WIDTH)
    height = round((args.north - args.south) / 180.0 * GLOBAL_HEIGHT)
    if width <= 0 or height <= 0:
        raise ValueError("Invalid bbox size")

    bbox = {"west": args.west, "south": args.south, "east": args.east, "north": args.north}
    pack = OUT_ROOT / f"NovoAtlas_World_1block200m_Region_{slug}_v1"
    cache = REAL_CACHE / (
        f"world_1_200_region_{slug}_{args.west:g}_{args.east:g}_{args.south:g}_{args.north:g}_{width}x{height}"
        .replace("-", "m")
        .replace(".", "p")
    )

    shard.BBOX = bbox
    shard.SIZE_X = width
    shard.SIZE_Y = height
    shard.OUT_ROOT = OUT_ROOT
    shard.PACK = pack
    shard.REAL_CACHE = REAL_CACHE
    shard.SHARD_CACHE = cache

    shard.build()

    fixed_preview = OUT_ROOT / "world_1_200_east_asia_shard_v5_preview.png"
    preview = OUT_ROOT / f"world_1_200_region_{slug}_v1_preview.png"
    if fixed_preview.exists():
        shutil.copy2(fixed_preview, preview)

    pack_meta = pack / "pack.mcmeta"
    if pack_meta.exists():
        meta = json.loads(pack_meta.read_text(encoding="utf-8"))
        meta["pack"]["description"] = f"NovoAtlas 1:200 region {args.name}: v5 real-data quality pipeline"
        write_json(pack_meta, meta)

    cx, cz = lonlat_to_world((args.west + args.east) / 2.0, (args.south + args.north) / 2.0)
    summary = {
        "name": args.name,
        "slug": slug,
        "pack": str(pack),
        "bbox": bbox,
        "size_blocks": {"x": width, "z": height},
        "scale": "1 block ~= 200 m",
        "center_tp": f"/tp @s {cx} 120 {cz}",
        "source_pipeline": "make_world_v2_200_east_asia_shard.py, parameterized for this region",
        "preview": str(preview) if preview.exists() else None,
    }
    summary_path = OUT_ROOT / f"world_1_200_region_{slug}_v1_summary.json"
    write_json(summary_path, summary)
    print(json.dumps({**summary, "summary": str(summary_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
