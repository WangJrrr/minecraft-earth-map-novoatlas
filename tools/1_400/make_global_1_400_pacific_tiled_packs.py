import json
import math
import os
import shutil
from pathlib import Path

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
SOURCE_PACK = OUT_ROOT / "NovoAtlas_World_Overworld_1block400m_v1_hscale10_GlobalRichOre_Stable64"
TOP100_LAYER = OUT_ROOT / "rich_ore_top100" / "generated_layer"
TOP100_MAP_INFO_PATCH = OUT_ROOT / "rich_ore_top100" / "global_top100_rich_ore_map_info_patch.json"
TOP100_ORE_1_200 = TOP100_LAYER / "data/world/novoatlas/global_1_200_full_tiled_v1/ore"

FINAL_ROOT = OUT_ROOT / "FINAL_PACKS_1_400_Pacific"
ORIGINAL_PACK = FINAL_ROOT / "OriginalRichOre_1_400_Pacific_Tiled"
TOP100_PACK = FINAL_ROOT / "Top100RichOre_1_400_Pacific_Tiled"
DOCS = FINAL_ROOT / "_previews_and_docs"

DATA_ID = "global_1_400_pacific_tiled_v1"
WIDTH = 81920
HEIGHT = 46080
TILE = 2048
TILES_X = math.ceil(WIDTH / TILE)
TILES_Z = math.ceil(HEIGHT / TILE)
PACIFIC_WEST = -31.5

CITY_POINTS = {
    "Beijing": (116.4074, 39.9042),
    "Shanghai": (121.4737, 31.2304),
    "Singapore": (103.8198, 1.3521),
    "Tokyo": (139.6917, 35.6895),
    "London": (-0.1276, 51.5072),
    "New York": (-74.0060, 40.7128),
    "Sydney": (151.2093, -33.8688),
    "Cape Town": (18.4241, -33.9249),
    "Rio de Janeiro": (-43.1729, -22.9068),
    "Dubai": (55.2708, 25.2048),
    "Taihu": (120.2, 31.2),
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rotate_pacific(image, resample):
    src_w, src_h = image.size
    shift = round(((PACIFIC_WEST + 180.0) / 360.0) * src_w)
    arr = np.asarray(image)
    rotated = np.roll(arr, -shift, axis=1)
    return Image.fromarray(rotated, mode=image.mode if image.mode != "P" else None)


def split_scaled_rotated(source, target_dir, resample, mode=None):
    image = Image.open(source)
    if mode:
        image = image.convert(mode)
    image = rotate_pacific(image, resample)
    src_w, src_h = image.size
    target_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for tz in range(TILES_Z):
        top = tz * TILE
        tile_h = min(TILE, HEIGHT - top)
        for tx in range(TILES_X):
            left = tx * TILE
            tile_w = min(TILE, WIDTH - left)
            src_box = (
                left * src_w / WIDTH,
                top * src_h / HEIGHT,
                (left + tile_w) * src_w / WIDTH,
                (top + tile_h) * src_h / HEIGHT,
            )
            tile = image.crop(src_box).resize((tile_w, tile_h), resample)
            if tile.size != (TILE, TILE):
                padded = Image.new(tile.mode, (TILE, TILE))
                padded.paste(tile, (0, 0))
                tile = padded
            tile.save(target_dir / f"{tx}_{tz}.png", optimize=True)
            count += 1
        print(f"{target_dir.name}: row {tz + 1}/{TILES_Z}", flush=True)
    return {
        "width": WIDTH,
        "height": HEIGHT,
        "tile_size": TILE,
        "tiles_x": TILES_X,
        "tiles_z": TILES_Z,
        "tile_count": count,
        "source": str(source),
        "source_size": [src_w, src_h],
        "pacific_west": PACIFIC_WEST,
    }


def copy_top100_ore_tiles(target_dir):
    target_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for tz in range(TILES_Z):
        real_h = min(TILE, HEIGHT - tz * TILE)
        for tx in range(TILES_X):
            src_canvas = Image.new("RGB", (TILE * 2, real_h * 2))
            sx0 = tx * 2
            sy0 = tz * 2
            for dy in range(2):
                for dx in range(2):
                    src_path = TOP100_ORE_1_200 / f"{sx0 + dx}_{sy0 + dy}.png"
                    if not src_path.exists():
                        continue
                    with Image.open(src_path) as src:
                        crop_h = min(TILE, src_canvas.height - dy * TILE)
                        crop = src.convert("RGB").crop((0, 0, TILE, crop_h))
                        src_canvas.paste(crop, (dx * TILE, dy * TILE))
            tile = src_canvas.resize((TILE, real_h), Image.Resampling.NEAREST)
            if tile.size != (TILE, TILE):
                padded = Image.new("RGB", (TILE, TILE), "#FFFFFF")
                padded.paste(tile, (0, 0))
                tile = padded
            tile.save(target_dir / f"{tx}_{tz}.png", optimize=True)
            count += 1
        print(f"top100 ore: row {tz + 1}/{TILES_Z}", flush=True)
    return {
        "width": WIDTH,
        "height": HEIGHT,
        "tile_size": TILE,
        "tiles_x": TILES_X,
        "tiles_z": TILES_Z,
        "tile_count": count,
        "source": str(TOP100_ORE_1_200),
        "method": "2x2 nearest downsample from validated 1:200 Top100 rich ore layer",
    }


def tile_config(kind):
    return {
        "tile_size": TILE,
        "tiles": f"world:novoatlas/{DATA_ID}/{kind}/{{tx}}_{{tz}}.png",
        "width": WIDTH,
        "height": HEIGHT,
    }


def lonlat_to_world(lon, lat):
    x = round(((lon - PACIFIC_WEST) % 360.0) / 360.0 * WIDTH - WIDTH / 2)
    z = round((90.0 - lat) / 180.0 * HEIGHT - HEIGHT / 2)
    return {"lon": lon, "lat": lat, "x": x, "y": 120, "z": z, "tp": f"/tp @s {x} 120 {z}"}


def update_pack_meta(pack, desc):
    meta_path = pack / "pack.mcmeta"
    meta = read_json(meta_path)
    meta["pack"]["description"] = desc
    write_json(meta_path, meta)


def remove_single_images(pack):
    for old in [
        pack / "data/world/novoatlas/heightmap/world.png",
        pack / "data/world/novoatlas/biome_map/world.png",
        pack / "data/world/novoatlas/biome_map/ore_zones.png",
    ]:
        old.unlink(missing_ok=True)


def write_previews(pack, name):
    surf_dir = pack / f"data/world/novoatlas/{DATA_ID}/surface"
    height_dir = pack / f"data/world/novoatlas/{DATA_ID}/height"
    ore_dir = pack / f"data/world/novoatlas/{DATA_ID}/ore"
    preview_w, preview_h = 2400, 1350

    surface = Image.new("RGB", (preview_w, preview_h))
    height = Image.new("L", (preview_w, preview_h))
    ore = Image.new("RGB", (preview_w, preview_h), "#FFFFFF")
    for tz in range(TILES_Z):
        y0 = round(tz * preview_h / TILES_Z)
        y1 = round((tz + 1) * preview_h / TILES_Z)
        for tx in range(TILES_X):
            x0 = round(tx * preview_w / TILES_X)
            x1 = round((tx + 1) * preview_w / TILES_X)
            box_size = (x1 - x0, y1 - y0)
            with Image.open(surf_dir / f"{tx}_{tz}.png") as im:
                surface.paste(im.convert("RGB").resize(box_size, Image.Resampling.NEAREST), (x0, y0))
            with Image.open(height_dir / f"{tx}_{tz}.png") as im:
                height.paste(im.convert("L").resize(box_size, Image.Resampling.BILINEAR), (x0, y0))
            with Image.open(ore_dir / f"{tx}_{tz}.png") as im:
                ore.paste(im.convert("RGB").resize(box_size, Image.Resampling.NEAREST), (x0, y0))
    shade = Image.merge("RGB", (height, height, height))
    shaded = Image.blend(surface, shade, 0.22)
    out_surface = DOCS / f"{name}_surface_preview.png"
    out_ore = DOCS / f"{name}_ore_preview.png"
    shaded.save(out_surface, optimize=True)
    ore.save(out_ore, optimize=True)
    return {"surface_preview": str(out_surface), "ore_preview": str(out_ore)}


def copy_source_pack(target):
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(SOURCE_PACK, target)


def build_original():
    copy_source_pack(ORIGINAL_PACK)
    tile_root = ORIGINAL_PACK / f"data/world/novoatlas/{DATA_ID}"
    height_stats = split_scaled_rotated(
        SOURCE_PACK / "data/world/novoatlas/heightmap/world.png",
        tile_root / "height",
        Image.Resampling.BILINEAR,
        "L",
    )
    surface_stats = split_scaled_rotated(
        SOURCE_PACK / "data/world/novoatlas/biome_map/world.png",
        tile_root / "surface",
        Image.Resampling.NEAREST,
        "RGB",
    )
    ore_stats = split_scaled_rotated(
        SOURCE_PACK / "data/world/novoatlas/biome_map/ore_zones.png",
        tile_root / "ore",
        Image.Resampling.NEAREST,
        "RGB",
    )
    map_info_path = ORIGINAL_PACK / "data/world/novoatlas/map_info/world.json"
    map_info = read_json(map_info_path)
    map_info["horizontal_scale"] = 1
    map_info["height_map"] = tile_config("height")
    map_info["surface_biomes"]["map"] = tile_config("surface")
    map_info["cave_biomes"]["layers"][0]["biomes"]["map"] = tile_config("ore")
    write_json(map_info_path, map_info)
    remove_single_images(ORIGINAL_PACK)
    update_pack_meta(ORIGINAL_PACK, "NovoAtlas global 1:400 Pacific tiled: original Stable64 rich ore")
    previews = write_previews(ORIGINAL_PACK, "original_rich_ore_1_400_pacific")
    return {"height": height_stats, "surface": surface_stats, "ore": ore_stats, **previews}


def build_top100():
    if TOP100_PACK.exists():
        shutil.rmtree(TOP100_PACK)
    shutil.copytree(ORIGINAL_PACK, TOP100_PACK)
    ore_dir = TOP100_PACK / f"data/world/novoatlas/{DATA_ID}/ore"
    if ore_dir.exists():
        shutil.rmtree(ore_dir)
    ore_stats = copy_top100_ore_tiles(ore_dir)

    for sub in ["data/world/worldgen", "data/minecraft/tags/worldgen"]:
        src = TOP100_LAYER / sub
        dst = TOP100_PACK / sub
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    patch = read_json(TOP100_MAP_INFO_PATCH)
    patch["cave_biomes"]["layers"][0]["biomes"]["map"] = tile_config("ore")
    map_info_path = TOP100_PACK / "data/world/novoatlas/map_info/world.json"
    map_info = read_json(map_info_path)
    map_info["cave_biomes"] = patch["cave_biomes"]
    write_json(map_info_path, map_info)
    update_pack_meta(TOP100_PACK, "NovoAtlas global 1:400 Pacific tiled: Top100 rich ore")
    previews = write_previews(TOP100_PACK, "top100_rich_ore_1_400_pacific")
    return {"ore": ore_stats, **previews}


def validate_pack(pack):
    tile_root = pack / f"data/world/novoatlas/{DATA_ID}"
    result = {"pack": str(pack)}
    for kind in ["height", "surface", "ore"]:
        files = list((tile_root / kind).glob("*.png"))
        result[f"{kind}_tile_count"] = len(files)
        result[f"{kind}_missing"] = TILES_X * TILES_Z - len(files)
    map_info = read_json(pack / "data/world/novoatlas/map_info/world.json")
    result["horizontal_scale"] = map_info.get("horizontal_scale")
    result["height_map"] = map_info.get("height_map")
    result["surface_map"] = map_info.get("surface_biomes", {}).get("map")
    result["ore_map"] = map_info.get("cave_biomes", {}).get("layers", [{}])[0].get("biomes", {}).get("map")
    return result


def main():
    if not SOURCE_PACK.exists():
        raise FileNotFoundError(SOURCE_PACK)
    if not TOP100_ORE_1_200.exists():
        raise FileNotFoundError(TOP100_ORE_1_200)
    DOCS.mkdir(parents=True, exist_ok=True)
    original = build_original()
    top100 = build_top100()
    coords = {name: lonlat_to_world(lon, lat) for name, (lon, lat) in CITY_POINTS.items()}
    write_json(DOCS / "city_coordinates_1_400_pacific.json", coords)
    summary = {
        "final_root": str(FINAL_ROOT),
        "scale": "1 block = 400 m",
        "projection": "Pacific-centered equirectangular",
        "pacific_west": PACIFIC_WEST,
        "center_longitude": 148.5,
        "width": WIDTH,
        "height": HEIGHT,
        "tile_size": TILE,
        "tiles_x": TILES_X,
        "tiles_z": TILES_Z,
        "original_pack": str(ORIGINAL_PACK),
        "top100_pack": str(TOP100_PACK),
        "original_build": original,
        "top100_build": top100,
        "validation": {
            "original": validate_pack(ORIGINAL_PACK),
            "top100": validate_pack(TOP100_PACK),
        },
        "coordinates": str(DOCS / "city_coordinates_1_400_pacific.json"),
        "notes": [
            "This 1:400 build reuses validated source rasters and the validated 1:200 Top100 ore layer.",
            "Surface, height, and ore maps are all tiled for the rebuilt NovoAtlas mod.",
            "Old single-image maps are removed from the final packs.",
        ],
    }
    write_json(FINAL_ROOT / "FINAL_DELIVERY_SUMMARY_1_400_PACIFIC.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
