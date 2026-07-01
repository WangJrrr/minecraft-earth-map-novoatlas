import json
import math
import os
import shutil
import sys
import io
import zipfile
import urllib.parse
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
CHINA_ROOT = ROOT
sys.path.insert(0, str(CHINA_ROOT))

import make_china_overworld_pack as base  # noqa: E402
import make_china_v23_4x_area_global_rules_pack as china_v23  # noqa: E402


# True 1:200 global-grid shard. The V23 4x China pack uses half this
# linear resolution. This tile is deliberately 512-aligned in dimensions
# for later MCA-region merge experiments.
BBOX = {"west": 116.0, "south": 24.0, "east": 143.0, "north": 48.0}
SIZE_X = 12288
SIZE_Y = 12288
SEA_LEVEL = base.SEA_LEVEL
WEB_MERCATOR_MAX_LAT = 85.05112878

OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
PACK = OUT_ROOT / "NovoAtlas_World_1block200m_EastAsiaShard_v5"
REAL_CACHE = Path(os.environ.get("NOVOATLAS_CACHE_ROOT", PROJECT_ROOT / "cache"))
VECTOR_CACHE = CHINA_ROOT / "vector_cache"
SHARD_CACHE = REAL_CACHE / f"world_1_200_east_asia_shard_116e_143e_24n_48n_{SIZE_X}x{SIZE_Y}"


def configure_modules():
    base.BBOX = BBOX
    base.SIZE_X = SIZE_X
    base.SIZE_Y = SIZE_Y
    base.ZOOM = 8
    base.CACHE = REAL_CACHE / "terrarium_tiles"
    base.VECTOR_CACHE = VECTOR_CACHE
    base.RIVER_MASK_CACHE = SHARD_CACHE / "hydrorivers_mask.npy"
    base.LAKE_MASK_CACHE = SHARD_CACHE / "natural_earth_lakes_mask.npy"

    china_v23.SIZE_X = SIZE_X
    china_v23.SIZE_Y = SIZE_Y
    china_v23.SEA_LEVEL = SEA_LEVEL
    china_v23.REAL_CACHE = REAL_CACHE
    china_v23.WORLDCOVER_ZOOM = 8
    china_v23.WORLDCOVER_CACHE = REAL_CACHE / "worldcover_2021_z8"
    china_v23.CLIMATE_CACHE = SHARD_CACHE / "worldclim_2.5m"
    china_v23.PACK = PACK
    china_v23.OUT_ROOT = OUT_ROOT
    china_v23.base.BBOX = BBOX
    china_v23.base.SIZE_X = SIZE_X
    china_v23.base.SIZE_Y = SIZE_Y
    china_v23.base.ZOOM = 8
    china_v23.base.CACHE = base.CACHE
    china_v23.base.RIVER_MASK_CACHE = base.RIVER_MASK_CACHE
    china_v23.base.LAKE_MASK_CACHE = base.LAKE_MASK_CACHE


def worldclim_source_crop(image):
    width, height = image.size
    left = round((BBOX["west"] + 180.0) / 360.0 * width)
    right = round((BBOX["east"] + 180.0) / 360.0 * width)
    top = round((90.0 - BBOX["north"]) / 180.0 * height)
    bottom = round((90.0 - BBOX["south"]) / 180.0 * height)
    return image.crop((left, top, right, bottom)).resize((SIZE_X, SIZE_Y), Image.Resampling.BILINEAR)


def sample_worldclim_for_shard():
    cache = SHARD_CACHE / "worldclim_2.5m_exact_bbox"
    cache.mkdir(parents=True, exist_ok=True)
    paths = {
        "annual_temp": cache / "annual_temp.npy",
        "coldest_temp": cache / "coldest_temp.npy",
        "warmest_temp": cache / "warmest_temp.npy",
        "temp_range": cache / "temp_range.npy",
        "annual_precip": cache / "annual_precip.npy",
        "driest_precip": cache / "driest_precip.npy",
        "wettest_precip": cache / "wettest_precip.npy",
        "precip_seasonality": cache / "precip_seasonality.npy",
        "warm_season_precip_ratio": cache / "warm_season_precip_ratio.npy",
    }
    if all(path.exists() for path in paths.values()):
        result = {key: np.load(path, mmap_mode="r") for key, path in paths.items()}
        if all(value.shape == (SIZE_Y, SIZE_X) for value in result.values()):
            return result

    tavg_zip = REAL_CACHE / "wc2.1_2.5m_tavg.zip"
    prec_zip = REAL_CACHE / "wc2.1_2.5m_prec.zip"
    if not tavg_zip.exists() or not prec_zip.exists():
        raise FileNotFoundError(f"Missing WorldClim tavg/prec ZIP files in {REAL_CACHE}")

    annual_temp = np.zeros((SIZE_Y, SIZE_X), dtype=np.float32)
    coldest_temp = np.full((SIZE_Y, SIZE_X), 100.0, dtype=np.float32)
    warmest_temp = np.full((SIZE_Y, SIZE_X), -100.0, dtype=np.float32)
    with zipfile.ZipFile(tavg_zip) as archive:
        names = sorted(name for name in archive.namelist() if name.lower().endswith(".tif"))
        for index, name in enumerate(names, start=1):
            with archive.open(name) as source:
                image = Image.open(io.BytesIO(source.read()))
                values = np.array(worldclim_source_crop(image), dtype=np.float32, copy=True)
            values[values < -1000] = np.nan
            annual_temp += np.nan_to_num(values, nan=0.0)
            coldest_temp = np.fmin(coldest_temp, values)
            warmest_temp = np.fmax(warmest_temp, values)
            print(f"WorldClim shard temperature: {index}/{len(names)}")
    annual_temp /= len(names)
    np.save(paths["annual_temp"], annual_temp)
    np.save(paths["coldest_temp"], coldest_temp)
    np.save(paths["warmest_temp"], warmest_temp)
    np.save(paths["temp_range"], warmest_temp - coldest_temp)
    del annual_temp, coldest_temp, warmest_temp

    annual_precip = np.zeros((SIZE_Y, SIZE_X), dtype=np.float32)
    driest_precip = np.full((SIZE_Y, SIZE_X), 100000.0, dtype=np.float32)
    wettest_precip = np.zeros((SIZE_Y, SIZE_X), dtype=np.float32)
    precip_square_sum = np.zeros((SIZE_Y, SIZE_X), dtype=np.float32)
    warm_season_precip = np.zeros((SIZE_Y, SIZE_X), dtype=np.float32)
    with zipfile.ZipFile(prec_zip) as archive:
        names = sorted(name for name in archive.namelist() if name.lower().endswith(".tif"))
        for index, name in enumerate(names, start=1):
            with archive.open(name) as source:
                image = Image.open(io.BytesIO(source.read()))
                values = np.array(worldclim_source_crop(image), dtype=np.float32, copy=True)
            values[values < 0] = np.nan
            clean = np.nan_to_num(values, nan=0.0)
            annual_precip += clean
            driest_precip = np.fmin(driest_precip, values)
            wettest_precip = np.fmax(wettest_precip, values)
            precip_square_sum += clean * clean
            if 5 <= index <= 9:
                warm_season_precip += clean
            print(f"WorldClim shard precipitation: {index}/{len(names)}")
    monthly_precip_mean = annual_precip / 12.0
    monthly_precip_variance = np.maximum(0.0, precip_square_sum / 12.0 - monthly_precip_mean ** 2)
    np.save(paths["annual_precip"], annual_precip)
    np.save(paths["driest_precip"], driest_precip)
    np.save(paths["wettest_precip"], wettest_precip)
    np.save(paths["precip_seasonality"], np.sqrt(monthly_precip_variance) / np.maximum(monthly_precip_mean, 1.0))
    np.save(paths["warm_season_precip_ratio"], warm_season_precip / np.maximum(annual_precip, 1.0))
    return {key: np.load(path, mmap_mode="r") for key, path in paths.items()}


def get_worldcover_tile(z, x, y):
    path = china_v23.WORLDCOVER_CACHE / str(z) / str(x) / f"{y}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            return Image.open(path).convert("RGB")
        except Exception:
            path.unlink()

    params = urllib.parse.urlencode(
        {
            "SERVICE": "WMTS",
            "REQUEST": "GetTile",
            "VERSION": "1.0.0",
            "LAYER": "esa-worldcover-map-10m-2021-v2_map",
            "STYLE": "default",
            "TILEMATRIXSET": "EPSG:3857",
            "TILEMATRIX": z,
            "TILEROW": y,
            "TILECOL": x,
            "FORMAT": "image/png",
            "TIME": "2021-01-01",
            "assets": "Map",
            "colormap_name": "worldcover",
        }
    )
    url = f"https://wmts.terrascope.be/?{params}"
    last_error = None
    for attempt in range(6):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "minecraft-earth-map-novoatlas"})
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
            image = Image.open(io.BytesIO(payload)).convert("RGB")
            image.save(path)
            return image
        except Exception as exc:
            last_error = exc
            time.sleep(1.5 + attempt)
    raise last_error


def sample_worldcover_for_shard():
    cache_path = SHARD_CACHE / "worldcover_2021_exact_bbox.npy"
    if cache_path.exists():
        cached = np.load(cache_path)
        if cached.shape == (SIZE_Y, SIZE_X):
            return cached

    z = china_v23.WORLDCOVER_ZOOM
    tile_count = 2 ** z
    sample_north = min(BBOX["north"], WEB_MERCATOR_MAX_LAT)
    sample_south = max(BBOX["south"], -WEB_MERCATOR_MAX_LAT)
    if sample_south >= sample_north:
        classes = np.full((SIZE_Y, SIZE_X), 70, dtype=np.uint8)
        np.save(cache_path, classes)
        return classes

    west_x, north_y = base.lonlat_to_tile_float(BBOX["west"], sample_north, z)
    east_x, south_y = base.lonlat_to_tile_float(BBOX["east"], sample_south, z)
    min_tx = max(0, min(tile_count - 1, math.floor(west_x)))
    max_tx = max(0, min(tile_count - 1, math.ceil(east_x) - 1))
    min_ty = max(0, min(tile_count - 1, math.floor(north_y)))
    max_ty = max(0, min(tile_count - 1, math.ceil(south_y) - 1))
    tiles = [(tx, ty) for ty in range(min_ty, max_ty + 1) for tx in range(min_tx, max_tx + 1)]

    print(f"Downloading/loading {len(tiles)} exact-bbox ESA WorldCover tiles...")
    loaded = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(get_worldcover_tile, z, tx, ty): (tx, ty) for tx, ty in tiles}
        for index, future in enumerate(as_completed(futures), start=1):
            loaded[futures[future]] = future.result()
            if index % 50 == 0 or index == len(tiles):
                print(f"WorldCover exact-bbox tiles: {index}/{len(tiles)}")

    mosaic = Image.new("RGB", ((max_tx - min_tx + 1) * 256, (max_ty - min_ty + 1) * 256))
    for (tx, ty), tile in loaded.items():
        mosaic.paste(tile, ((tx - min_tx) * 256, (ty - min_ty) * 256))

    mosaic_rgb = np.asarray(mosaic, dtype=np.uint8)
    lon_values = np.linspace(BBOX["west"], BBOX["east"], SIZE_X, dtype=np.float64)
    lat_values = np.linspace(BBOX["north"], BBOX["south"], SIZE_Y, dtype=np.float64)
    lat_values = np.clip(lat_values, -WEB_MERCATOR_MAX_LAT, WEB_MERCATOR_MAX_LAT)
    tile_x = (lon_values + 180.0) / 360.0 * (2 ** z)
    tile_x = np.clip(tile_x, 0.0, np.nextafter(float(tile_count), 0.0))
    lat_radians = np.radians(lat_values)
    tile_y = (1.0 - np.arcsinh(np.tan(lat_radians)) / np.pi) / 2.0 * (2 ** z)
    xs = np.clip(np.round((tile_x - min_tx) * 256).astype(np.int32), 0, mosaic_rgb.shape[1] - 1)
    ys = np.clip(np.round((tile_y - min_ty) * 256).astype(np.int32), 0, mosaic_rgb.shape[0] - 1)
    rgb = mosaic_rgb[ys[:, None], xs[None, :]]
    classes = np.zeros((SIZE_Y, SIZE_X), dtype=np.uint8)
    for color, class_id in china_v23.WORLDCOVER_RGB_TO_CLASS.items():
        classes[np.all(rgb == color, axis=2)] = class_id
    np.save(cache_path, classes)
    return classes


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def classify_water_layers_for_shard(land, cover, lake_mask, water_lakes=None, water_rivers=None):
    """Protect vector lakes/rivers before deciding what is sea-connected ocean.

    ESA WorldCover water is useful evidence, but in dense coastal deltas it
    contains canals, tidal flats, aquaculture ponds, and connected shallow
    sea pixels. Treating all class-80 water as inland lake water creates
    duplicate lakes and lets river networks become ocean biomes. For this
    shard, Natural Earth lakes and HydroRIVERS are the authoritative inland
    hydrology layers.
    """
    water_lakes = np.zeros_like(land, dtype=bool) if water_lakes is None else water_lakes
    water_rivers = np.zeros_like(land, dtype=bool) if water_rivers is None else water_rivers
    protected_inland = water_lakes | water_rivers | (lake_mask & (land | water_lakes))
    true_ocean = china_v23.connected_ocean_mask((~land) & ~protected_inland)
    inland_lake_water = (water_lakes | (lake_mask & ~true_ocean)) & ~true_ocean
    river_water = water_rivers & ~true_ocean

    # Keep only disconnected WorldCover water as small inland ponds; never let
    # connected coastal WorldCover water override vector rivers/lakes.
    disconnected_cover_water = (cover == 80) & ~true_ocean & ~protected_inland
    inland_water = (inland_lake_water | river_water | disconnected_cover_water) & ~true_ocean
    coast_band = base.dilate(true_ocean, rounds=3) & land
    return {
        "land": land,
        "true_ocean_water": true_ocean,
        "inland_lake_water": inland_lake_water,
        "river_water": river_water,
        "inland_water": inland_water,
        "coast_band": coast_band,
    }


def biome_color_image(surface):
    image = np.zeros((SIZE_Y, SIZE_X, 3), dtype=np.uint8)
    for key, color in china_v23.SURFACE_COLORS.items():
        rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        image[surface == key] = rgb
    return Image.fromarray(image, "RGB")


def apply_polar_cap_fast_rule(height, surface, land, water_layers):
    if BBOX["north"] <= -84.0:
        z = np.linspace(0.0, 1.0, SIZE_Y, dtype=np.float32)[:, None]
        x = np.linspace(0.0, 1.0, SIZE_X, dtype=np.float32)[None, :]
        dome = 98.0 + 42.0 * (1.0 - z) + 4.0 * np.sin(x * math.tau * 2.0)
        height[:, :] = np.clip(dome, SEA_LEVEL + 18, 190).astype(np.uint8)
        land[:, :] = True
        for key, value in water_layers.items():
            value[:, :] = False
        surface.data[:, :] = china_v23.BIOME_CODES["snowy_plains"]
        surface.data[height >= 132] = china_v23.BIOME_CODES["frozen_peaks"]
        surface.data[(height >= 112) & (height < 132)] = china_v23.BIOME_CODES["snowy_slopes"]
        return True

    if BBOX["south"] >= 84.0:
        height[:, :] = SEA_LEVEL - 10
        land[:, :] = False
        for key, value in water_layers.items():
            value[:, :] = False
        water_layers["true_ocean_water"][:, :] = True
        surface.data[:, :] = china_v23.BIOME_CODES["frozen_ocean"]
        surface.data[height < SEA_LEVEL - 6] = china_v23.BIOME_CODES["deep_frozen_ocean"]
        return True

    return False


def write_preview(height, surface, cover, climate):
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    preview = np.zeros((SIZE_Y, SIZE_X, 3), dtype=np.uint8)
    for key, color in china_v23.SURFACE_COLORS.items():
        rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        preview[surface == key] = rgb
    shade = np.clip((height.astype(np.float32) - 43) / 172.0, 0.38, 1.12)[..., None]
    preview = np.clip(preview.astype(np.float32) * shade, 0, 255).astype(np.uint8)
    Image.fromarray(preview, "RGB").resize((1800, 1800), Image.Resampling.LANCZOS).save(
        OUT_ROOT / "world_1_200_east_asia_shard_v5_preview.png"
    )

    cover_colors = {
        0: (80, 80, 80), 10: (0, 100, 0), 20: (255, 187, 34), 30: (255, 255, 76),
        40: (240, 150, 255), 50: (250, 0, 0), 60: (180, 180, 180), 70: (240, 240, 240),
        80: (0, 100, 200), 90: (0, 150, 160), 95: (0, 207, 117), 100: (250, 230, 160),
    }
    cover_rgb = np.zeros((SIZE_Y, SIZE_X, 3), dtype=np.uint8)
    for class_id, color in cover_colors.items():
        cover_rgb[cover == class_id] = color
    Image.fromarray(cover_rgb, "RGB").resize((1800, 1800), Image.Resampling.NEAREST).save(
        OUT_ROOT / "world_1_200_east_asia_shard_v5_worldcover.png"
    )

    temp = climate["annual_temp"]
    precip = climate["annual_precip"]
    climate_rgb = np.zeros((SIZE_Y, SIZE_X, 3), dtype=np.uint8)
    climate_rgb[..., 0] = np.clip((temp + 15) / 45 * 255, 0, 255).astype(np.uint8)
    climate_rgb[..., 1] = np.clip(precip / 2200 * 255, 0, 255).astype(np.uint8)
    climate_rgb[..., 2] = np.clip((30 - temp) / 45 * 255, 0, 255).astype(np.uint8)
    Image.fromarray(climate_rgb, "RGB").resize((1800, 1800), Image.Resampling.LANCZOS).save(
        OUT_ROOT / "world_1_200_east_asia_shard_v5_worldclim.png"
    )


def write_surface_safety_overrides():
    never_place = {
        "type": "minecraft:block_predicate_filter",
        "predicate": {
            "type": "minecraft:matching_blocks",
            "blocks": "minecraft:barrier",
        },
    }
    overrides = {
        "spring_lava": "minecraft:spring_lava_overworld",
        "spring_lava_frozen": "minecraft:spring_lava_frozen",
        "lake_lava_surface": "minecraft:lake_lava",
        "lake_lava_underground": "minecraft:lake_lava",
        "disk_sand": "minecraft:disk_sand",
        "disk_clay": "minecraft:disk_clay",
        "disk_gravel": "minecraft:disk_gravel",
    }
    for name, feature in overrides.items():
        write_json(
            PACK / f"data/minecraft/worldgen/placed_feature/{name}.json",
            {"feature": feature, "placement": [never_place]},
        )


def global_coordinates(lon, lat):
    full_x = int(round((lon + 180.0) / 360.0 * (163840 - 1)))
    full_z = int(round((90.0 - lat) / 180.0 * (92160 - 1)))
    centered_x = int(round(lon / 360.0 * 163840))
    centered_z = int(round(-lat / 180.0 * 92160))
    local_x = int(round((lon - BBOX["west"]) / (BBOX["east"] - BBOX["west"]) * (SIZE_X - 1)))
    local_z = int(round((BBOX["north"] - lat) / (BBOX["north"] - BBOX["south"]) * (SIZE_Y - 1)))
    return {
        "lon": lon,
        "lat": lat,
        "local_x": local_x,
        "local_z": local_z,
        "global_image_x": full_x,
        "global_image_z": full_z,
        "global_centered_x": centered_x,
        "global_centered_z": centered_z,
    }


def sample_points(surface, height):
    points = {
        "Shanghai": (121.47, 31.23),
        "Taihu": (120.20, 31.20),
        "Beijing": (116.40, 39.90),
        "Seoul": (126.98, 37.56),
        "Tokyo": (139.70, 35.70),
        "Osaka": (135.50, 34.69),
        "Taipei": (121.56, 25.04),
        "Sapporo": (141.35, 43.06),
    }
    reverse = {code: biome for biome, code in china_v23.BIOME_CODES.items()}
    result = {}
    for name, (lon, lat) in points.items():
        item = global_coordinates(lon, lat)
        if BBOX["west"] <= lon <= BBOX["east"] and BBOX["south"] <= lat <= BBOX["north"]:
            x = int(np.clip(item["local_x"], 0, SIZE_X - 1))
            z = int(np.clip(item["local_z"], 0, SIZE_Y - 1))
            item["height"] = int(height[z, x])
            item["biome"] = reverse[int(surface.data[z, x])]
        else:
            item["outside_this_shard"] = True
        result[name] = item
    return result


def write_pack(height, surface):
    if PACK.exists():
        shutil.rmtree(PACK)
    for relative in [
        "data/world/novoatlas/heightmap",
        "data/world/novoatlas/biome_map",
        "data/world/novoatlas/map_info",
        "data/minecraft/dimension",
        "data/minecraft/worldgen/placed_feature",
    ]:
        (PACK / relative).mkdir(parents=True, exist_ok=True)

    Image.fromarray(height, "L").save(PACK / "data/world/novoatlas/heightmap/east_asia.png")
    biome_color_image(surface).save(PACK / "data/world/novoatlas/biome_map/east_asia.png")
    map_info = {
        "starting_y": 0,
        "horizontal_scale": 1,
        "vertical_scale": 1,
        "height_map": "world:east_asia",
        "surface_biomes": {
            "map": "world:east_asia",
            "biomes": [
                {"biome": china_v23.SURFACE_BIOMES[key], "color": china_v23.SURFACE_COLORS[key]}
                for key in china_v23.SURFACE_COLORS
            ],
        },
    }
    write_json(PACK / "data/world/novoatlas/map_info/east_asia.json", map_info)
    write_json(
        PACK / "data/minecraft/dimension/overworld.json",
        {
            "type": "minecraft:overworld",
            "generator": {
                "type": "novoatlas:image_map",
                "map_info": "world:east_asia",
                "settings": "minecraft:overworld",
                "underground_density_function": "novoatlas:caves",
                "biome_source": {
                    "type": "novoatlas:color_map",
                    "map_info": "world:east_asia",
                    "default_biome": "minecraft:the_void",
                },
            },
        },
    )
    write_json(
        PACK / "pack.mcmeta",
        {
            "pack": {
                "pack_format": 48,
                "description": "NovoAtlas World V2 East Asia shard: true 1 block ~= 200m grid, horizontal_scale=1, no rich ore overlay",
            }
        },
    )
    write_surface_safety_overrides()


def build():
    configure_modules()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    SHARD_CACHE.mkdir(parents=True, exist_ok=True)

    climate = sample_worldclim_for_shard()
    raw_cover = sample_worldcover_for_shard()
    cover = china_v23.stabilize_landcover(raw_cover)
    elev = china_v23.sample_elevation_equirectangular()
    height, land = china_v23.minecraft_height_with_bathymetry(elev, raw_cover)
    lakes = base.lake_mask()
    height, water_lakes, _ = base.carve_lakes(height, lakes)
    rivers = base.river_mask(land & ~water_lakes)
    height, water_rivers = china_v23.conservative_river_pass(height, rivers, land)
    water_layers = classify_water_layers_for_shard(land, raw_cover, lakes, water_lakes, water_rivers)
    surface_land = land & ~water_layers["inland_lake_water"]
    surface = china_v23.geographic_surface_biomes(
        height,
        elev,
        surface_land,
        cover,
        climate,
        water_layers["river_water"],
        water_layers["inland_lake_water"],
        water_layers,
    )
    polar_fast_rule = apply_polar_cap_fast_rule(height, surface, land, water_layers)
    consistency_audit = china_v23.validate_surface_biome_consistency(
        surface, land, water_layers, height, elev, climate
    )

    write_pack(height, surface)
    write_preview(height, surface, cover, climate)
    write_json(
        OUT_ROOT / "world_1_200_east_asia_shard_v5_report.json",
        {
            "pack": str(PACK),
            "bbox": BBOX,
            "size_blocks": {"x": SIZE_X, "z": SIZE_Y},
            "scale": {
                "relationship_to_china_4x": "2x linear resolution; 4x China matches the previous 1:400 global grid.",
                "horizontal_scale": 1,
                "target_global_grid_blocks": {"x": 163840, "z": 92160},
            },
            "chunky_local_radius_hint": {
                "center": {"x": SIZE_X // 2, "z": SIZE_Y // 2},
                "radius": max(math.ceil(SIZE_X / 2 / 16), math.ceil(SIZE_Y / 2 / 16)),
                "note": "For this standalone shard, use a square or radius pregen around the shard center only after creating a fresh world with this datapack.",
            },
            "surface_biome_counts": surface.counts(),
            "polar_fast_rule": polar_fast_rule,
            **consistency_audit,
            "sample_points": sample_points(surface, height),
            "real_data": [
                "AWS Terrarium elevation/bathymetry z8",
                "WorldClim 2.1 2.5-minute monthly mean temperature and precipitation",
                "ESA WorldCover 2021 WMTS z8",
                "HydroRIVERS real river vectors",
                "Natural Earth real lake polygons",
            ],
            "v5_fix": "WorldCover is sampled into a bbox-specific shard cache; vector lakes and HydroRIVERS are protected before sea-connected ocean classification, preventing old-bbox duplicate land/water layers.",
        },
    )
    print(f"Built {PACK}")


if __name__ == "__main__":
    build()
