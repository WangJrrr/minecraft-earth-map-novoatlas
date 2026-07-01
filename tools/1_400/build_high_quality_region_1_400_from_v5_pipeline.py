import argparse
import importlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from global_hydrorivers import make_reader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORLD_SCRIPTS = Path(os.environ.get("NOVOATLAS_PIPELINE_ROOT", PROJECT_ROOT / "tools" / "pipeline"))
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
REAL_CACHE = Path(os.environ.get("NOVOATLAS_CACHE_ROOT", PROJECT_ROOT / "cache"))
GLOBAL_WIDTH = 81920
GLOBAL_HEIGHT = 46080


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


def apply_antarctic_snow_rule(shard, north, south, height_map, surface, land):
    row_latitudes = np.linspace(north, south, land.shape[0], dtype=np.float32)[:, None]
    antarctic_land = land & (row_latitudes <= -60.0)
    if not np.any(antarctic_land):
        return False
    surface.data[antarctic_land] = shard.china_v23.BIOME_CODES["snowy_plains"]
    surface.data[antarctic_land & (height_map >= 112)] = shard.china_v23.BIOME_CODES["snowy_slopes"]
    surface.data[antarctic_land & (height_map >= 150)] = shard.china_v23.BIOME_CODES["frozen_peaks"]
    return True


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

    # 1:400 极地区域使用完整真实数据管线，不使用 fast rule
    slug = slugify(args.name)
    width = round((args.east - args.west) / 360.0 * GLOBAL_WIDTH)
    height = round((args.north - args.south) / 180.0 * GLOBAL_HEIGHT)
    if width <= 0 or height <= 0:
        raise ValueError("Invalid bbox size")

    bbox = {"west": args.west, "south": args.south, "east": args.east, "north": args.north}
    pack = OUT_ROOT / f"NovoAtlas_World_1block400m_HQ_Region_{slug}_v1"
    cache = REAL_CACHE / (
        f"world_1_400_hq_region_{slug}_{args.west:g}_{args.east:g}_{args.south:g}_{args.north:g}_{width}x{height}"
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

    original_configure_modules = shard.configure_modules

    def configure_modules_with_global_river_cache():
        original_configure_modules()
        river_mask_cache = cache / "hydrorivers_global_v10_mask.npy"
        shard.base.RIVER_MASK_CACHE = river_mask_cache
        shard.china_v23.base.RIVER_MASK_CACHE = river_mask_cache

    shard.configure_modules = configure_modules_with_global_river_cache

    # The inherited China pipeline only includes HydroRIVERS Asia. Load the
    # continental archives intersecting this 1:400 shard instead.
    river_archive_cache = REAL_CACHE / "hydrorivers_v10_continents"
    shard.base.read_hydrorivers = make_reader(shard.base, bbox, river_archive_cache)

    # Preserve real Antarctic coastlines and elevation, but override land
    # biomes after global classification so missing climate/cover data cannot
    # turn the continent green.
    def antarctic_real_data_snow_rule(height_map, surface, land, water_layers):
        return apply_antarctic_snow_rule(
            shard, args.north, args.south, height_map, surface, land
        )

    shard.apply_polar_cap_fast_rule = antarctic_real_data_snow_rule

    shard.build()

    fixed_preview = OUT_ROOT / "world_1_200_east_asia_shard_v5_preview.png"
    preview = OUT_ROOT / f"world_1_400_hq_region_{slug}_v1_preview.png"
    if fixed_preview.exists():
        shutil.copy2(fixed_preview, preview)

    pack_meta = pack / "pack.mcmeta"
    if pack_meta.exists():
        meta = json.loads(pack_meta.read_text(encoding="utf-8"))
        meta["pack"]["description"] = f"NovoAtlas 1:400 HQ region {args.name}: full v5 real-data shard pipeline"
        write_json(pack_meta, meta)

    cx, cz = lonlat_to_world((args.west + args.east) / 2.0, (args.south + args.north) / 2.0)
    summary = {
        "name": args.name,
        "slug": slug,
        "pack": str(pack),
        "bbox": bbox,
        "size_blocks": {"x": width, "z": height},
        "scale": "1 block ~= 400 m",
        "center_tp": f"/tp @s {cx} 120 {cz}",
        "source_pipeline": "make_world_v2_200_east_asia_shard.py, parameterized for 1:400 HQ geographic region",
        "river_sources": list(shard.base.read_hydrorivers.archive_codes),
        "antarctic_rule": "real coastline/elevation; land south of 60S forced to snowy plains/slopes/frozen peaks",
        "preview": str(preview) if preview.exists() else None,
    }
    summary_path = OUT_ROOT / f"world_1_400_hq_region_{slug}_v1_summary.json"
    write_json(summary_path, summary)
    print(json.dumps({**summary, "summary": str(summary_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
