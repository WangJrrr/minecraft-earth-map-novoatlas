import io
import json
import math
import shutil
import time
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import make_china_overworld_pack as base


ROOT = Path(__file__).resolve().parent

# Four times the V19 area means doubling both horizontal axes.
base.SIZE_X *= 2
base.SIZE_Y *= 2
base.ZOOM = 8
_base_hydroriver_radius = base.hydroriver_radius
base.hydroriver_radius = lambda flow, upland: _base_hydroriver_radius(flow, upland) * 2

OUT_ROOT = base.OUT_ROOT
PACK = OUT_ROOT / "NovoAtlas_China_Overworld_4xArea_v23_GlobalRules_BalancedOre"
ORE_SOURCE = OUT_ROOT / "NovoAtlas_China_Overworld_Scale_Japan2048_v17_Balanced_CompositeOre"
REAL_CACHE = ROOT / "real_data_cache"
base.CACHE = REAL_CACHE / "terrarium_tiles"
base.RIVER_MASK_CACHE = REAL_CACHE / f"hydrorivers_river_mask_v23_{base.SIZE_X}x{base.SIZE_Y}.npy"
base.LAKE_MASK_CACHE = REAL_CACHE / f"ne_lakes_mask_v23_{base.SIZE_X}x{base.SIZE_Y}.npy"

SIZE_X = base.SIZE_X
SIZE_Y = base.SIZE_Y
SEA_LEVEL = base.SEA_LEVEL
WORLDCOVER_ZOOM = 8
WORLDCOVER_CACHE = REAL_CACHE / f"worldcover_2021_z{WORLDCOVER_ZOOM}"
CLIMATE_CACHE = REAL_CACHE / f"china_worldclim_2.5m_{SIZE_X}x{SIZE_Y}"
WEB_MERCATOR_MAX_LAT = 85.05112878

TAVG_ZIP = REAL_CACHE / "wc2.1_2.5m_tavg.zip"
PREC_ZIP = REAL_CACHE / "wc2.1_2.5m_prec.zip"

SURFACE_COLORS = {
    **base.SURFACE_COLORS,
    "flower_forest": "#7BAE55",
    "old_growth_birch_forest": "#769F54",
    "old_growth_pine_taiga": "#2B6646",
    "windswept_hills": "#76816A",
    "windswept_gravelly_hills": "#7C7A70",
    "windswept_savanna": "#A89F50",
    "savanna_plateau": "#A79F55",
    "frozen_peaks": "#E8F0F2",
    "ice_spikes": "#C5E7EE",
    "snowy_beach": "#D8D8C8",
}
SURFACE_BIOMES = {key: f"minecraft:{key}" for key in SURFACE_COLORS}
BIOME_CODES = {key: index for index, key in enumerate(SURFACE_COLORS)}
OCEAN_BIOMES = {
    "warm_ocean",
    "lukewarm_ocean",
    "ocean",
    "cold_ocean",
    "frozen_ocean",
    "deep_lukewarm_ocean",
    "deep_ocean",
    "deep_cold_ocean",
    "deep_frozen_ocean",
}
LAND_BIOMES = set(SURFACE_COLORS) - OCEAN_BIOMES - {"river", "frozen_river"}


class EncodedBiomeMap:
    """Compact biome-key raster; object arrays are too large at V20 scale."""

    def __init__(self, shape, default):
        self.data = np.full(shape, BIOME_CODES[default], dtype=np.uint8)
        self.shape = shape

    def __setitem__(self, mask, biome):
        self.data[mask] = BIOME_CODES[biome]

    def __eq__(self, biome):
        return self.data == BIOME_CODES[biome]

    def counts(self):
        counts = np.bincount(self.data.ravel(), minlength=len(BIOME_CODES))
        return {
            biome: int(counts[code])
            for biome, code in BIOME_CODES.items()
            if counts[code]
        }

WORLDCOVER_RGB_TO_CLASS = {
    (0, 100, 0): 10,       # tree cover
    (255, 187, 34): 20,    # shrubland
    (255, 255, 76): 30,    # grassland
    (240, 150, 255): 40,   # cropland
    (250, 0, 0): 50,       # built-up
    (180, 180, 180): 60,   # bare / sparse vegetation
    (240, 240, 240): 70,   # snow and ice
    (0, 100, 200): 80,     # permanent water
    (0, 150, 160): 90,     # herbaceous wetland
    (0, 207, 117): 95,     # mangroves
    (250, 230, 160): 100,  # moss and lichen
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def neighborhood_count(mask):
    padded = np.pad(mask.astype(np.uint8), 1, mode="edge")
    count = np.zeros(mask.shape, dtype=np.uint8)
    for dy in range(3):
        for dx in range(3):
            count += padded[dy:dy + SIZE_Y, dx:dx + SIZE_X]
    return count


def stabilize_landcover(cover):
    """Remove isolated land-cover pixels without inventing broad new regions."""
    stable = cover.copy()
    tree = cover == 10
    open_land = (cover == 30) | (cover == 40) | (cover == 50)
    tree_neighbors = neighborhood_count(tree)
    open_neighbors = neighborhood_count(open_land)

    # A lone sampled tree pixel at this scale should not create a full forest
    # biome with trees and terrain decoration. Real cropland and built-up
    # pixels remain open even when surrounded by forest.
    isolated_tree = tree & (tree_neighbors <= 3) & (open_neighbors >= 4)
    stable[isolated_tree] = 30
    return stable


def get_worldcover_tile(z, x, y):
    path = WORLDCOVER_CACHE / str(z) / str(x) / f"{y}.png"
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


def sample_worldcover():
    cache_path = REAL_CACHE / f"china_worldcover_2021_z{WORLDCOVER_ZOOM}_equirect_{SIZE_X}x{SIZE_Y}.npy"
    if cache_path.exists():
        cached = np.load(cache_path)
        if cached.shape == (SIZE_Y, SIZE_X):
            return cached

    west_x, north_y = base.lonlat_to_tile_float(base.BBOX["west"], base.BBOX["north"], WORLDCOVER_ZOOM)
    east_x, south_y = base.lonlat_to_tile_float(base.BBOX["east"], base.BBOX["south"], WORLDCOVER_ZOOM)
    min_tx, max_tx = math.floor(west_x), math.floor(east_x)
    min_ty, max_ty = math.floor(north_y), math.floor(south_y)
    tiles = [(tx, ty) for ty in range(min_ty, max_ty + 1) for tx in range(min_tx, max_tx + 1)]

    print(f"Downloading/loading {len(tiles)} ESA WorldCover tiles...")
    loaded = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(get_worldcover_tile, WORLDCOVER_ZOOM, tx, ty): (tx, ty) for tx, ty in tiles}
        for index, future in enumerate(as_completed(futures), start=1):
            loaded[futures[future]] = future.result()
            if index % 50 == 0 or index == len(tiles):
                print(f"WorldCover tiles: {index}/{len(tiles)}")

    mosaic = Image.new("RGB", ((max_tx - min_tx + 1) * 256, (max_ty - min_ty + 1) * 256))
    for (tx, ty), tile in loaded.items():
        mosaic.paste(tile, ((tx - min_tx) * 256, (ty - min_ty) * 256))

    mosaic_rgb = np.asarray(mosaic, dtype=np.uint8)
    lon_values = np.linspace(base.BBOX["west"], base.BBOX["east"], SIZE_X, dtype=np.float64)
    lat_values = np.linspace(base.BBOX["north"], base.BBOX["south"], SIZE_Y, dtype=np.float64)
    tile_x = (lon_values + 180.0) / 360.0 * (2 ** WORLDCOVER_ZOOM)
    lat_radians = np.radians(lat_values)
    tile_y = (
        1.0 - np.arcsinh(np.tan(lat_radians)) / np.pi
    ) / 2.0 * (2 ** WORLDCOVER_ZOOM)
    xs = np.clip(np.round((tile_x - min_tx) * 256).astype(np.int32), 0, mosaic_rgb.shape[1] - 1)
    ys = np.clip(np.round((tile_y - min_ty) * 256).astype(np.int32), 0, mosaic_rgb.shape[0] - 1)
    rgb = mosaic_rgb[ys[:, None], xs[None, :]]
    classes = np.zeros((SIZE_Y, SIZE_X), dtype=np.uint8)
    for color, class_id in WORLDCOVER_RGB_TO_CLASS.items():
        classes[np.all(rgb == color, axis=2)] = class_id
    np.save(cache_path, classes)
    return classes


def worldclim_source_crop(image):
    width, height = image.size
    left = round((base.BBOX["west"] + 180.0) / 360.0 * width)
    right = round((base.BBOX["east"] + 180.0) / 360.0 * width)
    top = round((90.0 - base.BBOX["north"]) / 180.0 * height)
    bottom = round((90.0 - base.BBOX["south"]) / 180.0 * height)
    return image.crop((left, top, right, bottom)).resize((SIZE_X, SIZE_Y), Image.Resampling.BILINEAR)


def sample_worldclim():
    CLIMATE_CACHE.mkdir(parents=True, exist_ok=True)
    paths = {
        "annual_temp": CLIMATE_CACHE / "annual_temp.npy",
        "coldest_temp": CLIMATE_CACHE / "coldest_temp.npy",
        "warmest_temp": CLIMATE_CACHE / "warmest_temp.npy",
        "temp_range": CLIMATE_CACHE / "temp_range.npy",
        "annual_precip": CLIMATE_CACHE / "annual_precip.npy",
        "driest_precip": CLIMATE_CACHE / "driest_precip.npy",
        "wettest_precip": CLIMATE_CACHE / "wettest_precip.npy",
        "precip_seasonality": CLIMATE_CACHE / "precip_seasonality.npy",
        "warm_season_precip_ratio": CLIMATE_CACHE / "warm_season_precip_ratio.npy",
    }
    if all(path.exists() for path in paths.values()):
        result = {key: np.load(path, mmap_mode="r") for key, path in paths.items()}
        if all(value.shape == (SIZE_Y, SIZE_X) for value in result.values()):
            return result

    # WorldClim's native grid is far coarser than either Minecraft output.
    # Upscale the already derived V19 climate layers one at a time, avoiding
    # nine full-resolution float arrays in memory simultaneously.
    source_cache = REAL_CACHE / "china_worldclim_2.5m"
    if all((source_cache / path.name).exists() for path in paths.values()):
        for key, path in paths.items():
            source = np.load(source_cache / path.name, mmap_mode="r")
            image = Image.fromarray(source, mode="F").resize(
                (SIZE_X, SIZE_Y), Image.Resampling.BILINEAR
            )
            np.save(path, np.asarray(image, dtype=np.float32))
            del source, image
        return {key: np.load(path, mmap_mode="r") for key, path in paths.items()}

    if not TAVG_ZIP.exists() or not PREC_ZIP.exists():
        raise FileNotFoundError("Missing WorldClim tavg/prec ZIP files in real_data_cache")

    annual_temp = np.zeros((SIZE_Y, SIZE_X), dtype=np.float32)
    coldest_temp = np.full((SIZE_Y, SIZE_X), 100.0, dtype=np.float32)
    warmest_temp = np.full((SIZE_Y, SIZE_X), -100.0, dtype=np.float32)
    annual_precip = np.zeros((SIZE_Y, SIZE_X), dtype=np.float32)
    driest_precip = np.full((SIZE_Y, SIZE_X), 100000.0, dtype=np.float32)
    wettest_precip = np.zeros((SIZE_Y, SIZE_X), dtype=np.float32)
    precip_square_sum = np.zeros((SIZE_Y, SIZE_X), dtype=np.float32)
    warm_season_precip = np.zeros((SIZE_Y, SIZE_X), dtype=np.float32)

    with zipfile.ZipFile(TAVG_ZIP) as archive:
        names = sorted(name for name in archive.namelist() if name.lower().endswith(".tif"))
        for index, name in enumerate(names, start=1):
            with archive.open(name) as source:
                image = Image.open(io.BytesIO(source.read()))
                values = np.array(worldclim_source_crop(image), dtype=np.float32, copy=True)
            values[values < -1000] = np.nan
            annual_temp += np.nan_to_num(values, nan=0.0)
            coldest_temp = np.fmin(coldest_temp, values)
            warmest_temp = np.fmax(warmest_temp, values)
            print(f"WorldClim temperature: {index}/{len(names)}")
    annual_temp /= len(names)

    with zipfile.ZipFile(PREC_ZIP) as archive:
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
            print(f"WorldClim precipitation: {index}/{len(names)}")

    monthly_precip_mean = annual_precip / 12.0
    monthly_precip_variance = np.maximum(0.0, precip_square_sum / 12.0 - monthly_precip_mean ** 2)
    result = {
        "annual_temp": annual_temp,
        "coldest_temp": coldest_temp,
        "warmest_temp": warmest_temp,
        "temp_range": warmest_temp - coldest_temp,
        "annual_precip": annual_precip,
        "driest_precip": driest_precip,
        "wettest_precip": wettest_precip,
        "precip_seasonality": np.sqrt(monthly_precip_variance) / np.maximum(monthly_precip_mean, 1.0),
        "warm_season_precip_ratio": warm_season_precip / np.maximum(annual_precip, 1.0),
    }
    for key, path in paths.items():
        np.save(path, result[key])
    return result


def sample_elevation_equirectangular():
    tile_count = 2 ** base.ZOOM
    sample_north = min(base.BBOX["north"], WEB_MERCATOR_MAX_LAT)
    sample_south = max(base.BBOX["south"], -WEB_MERCATOR_MAX_LAT)
    if sample_south >= sample_north:
        return np.zeros((SIZE_Y, SIZE_X), dtype=np.float32)

    west_x, north_y = base.lonlat_to_tile_float(base.BBOX["west"], sample_north, base.ZOOM)
    east_x, south_y = base.lonlat_to_tile_float(base.BBOX["east"], sample_south, base.ZOOM)
    min_tx = max(0, min(tile_count - 1, math.floor(west_x)))
    max_tx = max(0, min(tile_count - 1, math.ceil(east_x) - 1))
    min_ty = max(0, min(tile_count - 1, math.floor(north_y)))
    max_ty = max(0, min(tile_count - 1, math.ceil(south_y) - 1))
    mosaic = np.zeros(((max_ty - min_ty + 1) * 256, (max_tx - min_tx + 1) * 256, 3), dtype=np.uint8)
    for ty in range(min_ty, max_ty + 1):
        for tx in range(min_tx, max_tx + 1):
            tile = np.asarray(base.get_tile(base.ZOOM, tx, ty), dtype=np.uint8)
            oy, ox = (ty - min_ty) * 256, (tx - min_tx) * 256
            mosaic[oy:oy + 256, ox:ox + 256] = tile

    lon_values = np.linspace(base.BBOX["west"], base.BBOX["east"], SIZE_X, dtype=np.float64)
    lat_values = np.linspace(base.BBOX["north"], base.BBOX["south"], SIZE_Y, dtype=np.float64)
    lat_values = np.clip(lat_values, -WEB_MERCATOR_MAX_LAT, WEB_MERCATOR_MAX_LAT)
    tile_x = (lon_values + 180.0) / 360.0 * (2 ** base.ZOOM)
    tile_x = np.clip(tile_x, 0.0, np.nextafter(float(tile_count), 0.0))
    lat_radians = np.radians(lat_values)
    tile_y = (1.0 - np.arcsinh(np.tan(lat_radians)) / np.pi) / 2.0 * (2 ** base.ZOOM)
    xs = np.clip(np.round((tile_x - min_tx) * 256).astype(np.int32), 0, mosaic.shape[1] - 1)
    ys = np.clip(np.round((tile_y - min_ty) * 256).astype(np.int32), 0, mosaic.shape[0] - 1)
    elev = base.decode_terrarium(mosaic[ys[:, None], xs[None, :]])
    elev[elev > 9000] = 0
    return elev


def minecraft_height_with_bathymetry(elev, cover):
    height, terrain_land = base.minecraft_height(elev)
    cover_land = (cover != 0) & (cover != 80)

    # Preserve the validated V18 additive land recovery exactly. WorldCover can
    # fill zero-value elevation gaps but never removes elevation-defined land,
    # so this cannot create new inland or coastal holes.
    land = terrain_land | cover_land
    recovered_coastal_land = cover_land & ~terrain_land
    height[recovered_coastal_land] = np.maximum(height[recovered_coastal_land], SEA_LEVEL + 2)
    true_ocean = connected_ocean_mask(~land)
    height = apply_ocean_depth_guard(height, elev, land, true_ocean)
    return height, land


def connected_ocean_mask(water):
    """Only water connected to the map edge is allowed to become ocean."""
    if not np.any(water):
        return water.copy()

    labels, _ = ndimage.label(water, structure=np.ones((3, 3), dtype=np.uint8))
    edge_labels = np.unique(np.concatenate([
        labels[0, :],
        labels[-1, :],
        labels[:, 0],
        labels[:, -1],
    ]))
    edge_labels = edge_labels[edge_labels != 0]
    if not len(edge_labels):
        return np.zeros_like(water, dtype=bool)
    return np.isin(labels, edge_labels)


def apply_ocean_depth_guard(height, elev, land, true_ocean):
    """Make real oceans deepen quickly while leaving inland water untouched."""
    guarded = height.copy()
    if not np.any(true_ocean):
        return guarded

    depth_proxy = np.maximum(0.0, -elev)
    offshore_px = ndimage.distance_transform_edt(true_ocean).astype(np.float32)
    visual_depth = np.clip(2.0 + offshore_px * 3.8, 4.0, 34.0)
    bathy_depth = np.zeros_like(visual_depth, dtype=np.float32)
    shelf = true_ocean & (depth_proxy < 200)
    deep = true_ocean & (depth_proxy >= 200) & (depth_proxy < 4000)
    abyss = true_ocean & (depth_proxy >= 4000)
    bathy_depth[shelf] = 4.0 + np.power(depth_proxy[shelf] / 200.0, 0.68) * 14.0
    bathy_depth[deep] = 18.0 + np.power((depth_proxy[deep] - 200.0) / 3800.0, 0.58) * 22.0
    bathy_depth[abyss] = 40.0 + np.power(
        np.clip(depth_proxy[abyss] - 4000.0, 0, 7000.0) / 7000.0,
        0.72,
    ) * 9.0
    target_depth = np.maximum(visual_depth, bathy_depth)
    ocean_height = SEA_LEVEL - target_depth
    guarded[true_ocean] = np.clip(np.round(ocean_height[true_ocean]), 17, SEA_LEVEL - 1).astype(np.uint8)

    inland_water = (~land) & ~true_ocean
    guarded[inland_water] = np.clip(guarded[inland_water], SEA_LEVEL - 10, SEA_LEVEL - 1)
    return guarded


def classify_water_layers(land, cover, lake_mask, water_lakes=None, water_rivers=None):
    true_ocean = connected_ocean_mask(~land)
    water_lakes = np.zeros_like(land, dtype=bool) if water_lakes is None else water_lakes
    water_rivers = np.zeros_like(land, dtype=bool) if water_rivers is None else water_rivers

    permanent_inland_water = (cover == 80) & ~true_ocean
    inland_lake_water = ((lake_mask & (~land | water_lakes)) | water_lakes | permanent_inland_water) & ~true_ocean
    river_water = water_rivers & ~true_ocean
    inland_water = (inland_lake_water | river_water | ((~land) & ~true_ocean)) & ~true_ocean
    coast_band = base.dilate(true_ocean, rounds=3) & land
    return {
        "land": land,
        "true_ocean_water": true_ocean,
        "inland_lake_water": inland_lake_water,
        "river_water": river_water,
        "inland_water": inland_water,
        "coast_band": coast_band,
    }


def conservative_river_pass(height, rivers, land):
    coast_near = base.dilate(~land, rounds=7) & land
    estuary = base.dilate(rivers & coast_near, rounds=1) & land
    return base.carve_rivers(height, rivers | estuary)


def surface_biomes(height, elev, land, cover, climate, rivers, lakes):
    lat = base.lat_grid()
    lon = base.lon_grid()
    sl = base.slope(height)
    coast = base.coast_mask(land)
    texture = base.climate_texture(lon, lat)
    forest_variant = (
        0.52 * np.sin(lon * 3.7 + lat * 2.1)
        + 0.31 * np.sin(lon * 7.3 - lat * 4.9)
        + 0.17 * np.sin((lon + lat) * 11.7)
    )
    temp = climate["annual_temp"] + texture * 0.18
    coldest = climate["coldest_temp"]
    precip = climate["annual_precip"]

    keys = EncodedBiomeMap(height.shape, "ocean")
    water = ~land
    sea_temp = base.ocean_temperature(lat, lon, height)
    deep_water = water & (height < 34)
    shallow_water = water & ~deep_water
    keys[shallow_water & (sea_temp >= 27.0)] = "warm_ocean"
    keys[shallow_water & (sea_temp >= 22.0) & (sea_temp < 27.0)] = "lukewarm_ocean"
    keys[shallow_water & (sea_temp >= 11.0) & (sea_temp < 22.0)] = "ocean"
    keys[shallow_water & (sea_temp >= 1.5) & (sea_temp < 11.0)] = "cold_ocean"
    keys[shallow_water & (sea_temp < 1.5)] = "frozen_ocean"
    keys[deep_water & (sea_temp >= 20.0)] = "deep_lukewarm_ocean"
    keys[deep_water & (sea_temp >= 9.0) & (sea_temp < 20.0)] = "deep_ocean"
    keys[deep_water & (sea_temp >= 0.5) & (sea_temp < 9.0)] = "deep_cold_ocean"
    keys[deep_water & (sea_temp < 0.5)] = "deep_frozen_ocean"
    keys[land] = "plains"

    tree = land & (cover == 10)
    shrub = land & (cover == 20)
    grass = land & (cover == 30)
    open_land = land & ((cover == 40) | (cover == 50))
    bare = land & (cover == 60)
    snow_ice = land & (cover == 70)
    wet_cover = land & ((cover == 90) | (cover == 95))
    moss = land & (cover == 100)

    arid = precip < 420
    very_arid = precip < 220
    humid = precip >= 850
    very_humid = precip >= 1450
    tropical = (temp >= 21.5) & (coldest >= 12.0)
    cold = (temp < 4.5) | (coldest < -12.0)
    severe_cold = (temp < -2.0) | (coldest < -24.0)
    flat = sl < 3.8
    rugged = sl >= 5.0
    hill = (height >= 99) | (sl >= 3.0)

    keys[grass & tropical & arid] = "savanna"
    keys[grass & tropical & ~arid] = "savanna_plateau"
    keys[grass & cold] = "snowy_plains"
    keys[grass & ~cold & (height >= 105)] = "meadow"
    keys[grass & ~cold & (height < 105)] = "plains"
    keys[open_land & (temp < -1.0)] = "snowy_plains"
    keys[open_land & (temp >= -1.0)] = "plains"
    keys[open_land & very_humid & (temp > 13)] = "sunflower_plains"

    keys[tree & tropical & very_humid] = "jungle"
    keys[tree & tropical & humid & ~very_humid] = "sparse_jungle"
    keys[tree & cold & ~severe_cold] = "taiga"
    keys[tree & severe_cold] = "snowy_taiga"
    temperate_tree = tree & ~cold & ~tropical
    keys[temperate_tree] = "forest"
    keys[temperate_tree & (precip < 650) & (temp < 15)] = "birch_forest"
    keys[
        temperate_tree
        & (precip >= 1250)
        & (temp >= 8)
        & (temp < 18)
        & (height < 130)
        & (forest_variant > 0.78)
    ] = "dark_forest"
    keys[tree & hill & (lat > 42) & (precip > 650)] = "old_growth_spruce_taiga"
    keys[tree & hill & (lat > 37) & (lat <= 45) & (precip > 600)] = "old_growth_pine_taiga"
    keys[tree & hill & (lat > 43) & (lon > 120) & (temp > 2)] = "old_growth_birch_forest"
    flower_patch = tree & hill & (temp > 8) & (precip > 1000) & (precip < 1550) & (texture > 0.52)
    keys[flower_patch] = "flower_forest"

    keys[shrub & tropical] = "savanna"
    keys[shrub & cold] = "taiga"
    keys[shrub & ~tropical & ~cold & arid] = "savanna"
    keys[shrub & ~tropical & ~cold & ~arid] = "meadow"
    keys[wet_cover & tropical & very_humid] = "sparse_jungle"
    keys[wet_cover & ~tropical] = "plains"
    keys[moss & severe_cold] = "snowy_plains"
    keys[moss & ~severe_cold] = "taiga"

    keys[bare & very_arid & flat] = "desert"
    keys[bare & very_arid & rugged] = "eroded_badlands"
    keys[bare & arid & ~very_arid & rugged] = "badlands"
    keys[bare & arid & ~very_arid & flat] = "savanna"
    keys[bare & ~arid & rugged] = "windswept_gravelly_hills"
    keys[snow_ice] = "snowy_slopes"

    # Protect important buildable plains even where modern tree-cover pixels or
    # coarse climate cells would otherwise make them too densely wooded.
    north_china_w = base.oval(lon, lat, 116.5, 36.8, 5.0, 4.0)
    northeast_w = np.maximum(
        base.oval(lon, lat, 124.5, 45.5, 5.0, 3.4),
        base.oval(lon, lat, 128.5, 47.0, 3.7, 2.4),
    )
    yangtze_w = np.maximum(
        base.oval(lon, lat, 120.4, 31.0, 3.2, 1.8),
        base.oval(lon, lat, 112.6, 30.0, 4.2, 2.0),
    )
    pearl_w = base.oval(lon, lat, 113.4, 22.8, 2.0, 1.1)
    sichuan_w = base.oval(lon, lat, 106.0, 30.5, 3.0, 1.8)
    plain_weight = np.maximum.reduce([north_china_w, northeast_w, yangtze_w, pearl_w, sichuan_w])
    plain_open = open_land | grass
    protected_plains = (
        land
        & (height < 108)
        & flat
        & ((plain_weight + texture * 0.035) > 0.14)
        & plain_open
    )
    northeast_plain = protected_plains & ((northeast_w + texture * 0.025) > 0.20)
    keys[protected_plains] = "plains"
    keys[protected_plains & (precip > 1050) & (temp > 11)] = "sunflower_plains"
    keys[northeast_plain & (temp < 0)] = "snowy_plains"

    hainan = land & base.in_box(lon, lat, 108.0, 18.0, 112.0, 21.0)
    south_yunnan = land & base.in_box(lon, lat, 97.0, 21.0, 102.5, 24.5)
    keys[(hainan | south_yunnan) & tree & very_humid & (height < 125)] = "jungle"
    keys[(hainan | south_yunnan) & ~tree & very_humid & (height < 105)] = "sparse_jungle"
    keys[(hainan | south_yunnan) & tree & very_humid & (height >= 105) & (height < 140)] = "bamboo_jungle"

    # Terrain remains the final authority in mountains. Thresholds are gradual
    # and climate-aware to avoid straight biome boundaries.
    mountain = land & (height >= 122) & ~protected_plains
    keys[mountain & ~cold & ~arid & (height < 150) & ~rugged] = "meadow"
    keys[mountain & ~cold & arid & (height < 150) & ~rugged] = "windswept_savanna"
    keys[mountain & ~cold & (height < 160) & rugged] = "windswept_hills"
    keys[mountain & cold & (height < 158) & ~rugged] = "grove"
    keys[mountain & cold & (height < 166) & rugged] = "windswept_forest"
    keys[land & (height >= 158) & cold] = "snowy_slopes"
    keys[land & (height >= 177) & rugged & cold] = "frozen_peaks"
    keys[land & (height >= 184) & rugged & ~severe_cold] = "stony_peaks"
    keys[land & (height >= 204)] = "jagged_peaks"

    # Rare but geographically plausible vanilla surface variants. All masks
    # use terrain, land cover, and soft regional weights to avoid box edges.
    northwest_badlands_w = np.maximum(
        base.oval(lon, lat, 89.0, 36.5, 5.2, 2.8),
        base.oval(lon, lat, 104.5, 36.8, 4.0, 2.8),
    )
    badlands_candidate = land & very_arid & (height < 150) & bare & rugged
    keys[badlands_candidate & (northwest_badlands_w > 0.28) & (texture > 0.42)] = "badlands"
    keys[badlands_candidate & (northwest_badlands_w > 0.42) & (texture > 0.62)] = "eroded_badlands"
    keys[
        land & arid & hill & tree
        & ((base.oval(lon, lat, 106.5, 36.8, 4.0, 3.0) + texture * 0.04) > 0.42)
    ] = "wooded_badlands"

    yunnan_plateau_w = base.oval(lon, lat, 102.5, 25.5, 4.0, 2.8)
    keys[
        land & (grass | shrub) & (temp > 14) & (precip < 1350)
        & (height >= 96) & (height < 140) & ((yunnan_plateau_w + texture * 0.04) > 0.36)
    ] = "savanna_plateau"

    ice_spike_w = np.maximum(
        base.oval(lon, lat, 92.5, 33.5, 1.2, 0.8),
        base.oval(lon, lat, 97.0, 35.2, 1.0, 0.7),
    )
    keys[
        land & severe_cold & flat & (height >= 154) & (snow_ice | bare)
        & ((ice_spike_w + texture * 0.16) > 0.68)
    ] = "ice_spikes"

    sichuan_flower_w = base.oval(lon, lat, 103.0, 30.0, 2.0, 1.6)
    keys[
        tree & (precip > 1050) & (height > 105)
        & ((sichuan_flower_w + texture * 0.04) > 0.48)
    ] = "flower_forest"

    keys[land & coast & (height <= SEA_LEVEL + 4)] = "beach"
    keys[land & coast & (height <= SEA_LEVEL + 4) & (coldest < -10)] = "snowy_beach"
    keys[land & coast & rugged] = "stony_shore"

    keys[lakes] = "river"
    keys[lakes & (coldest < -12)] = "frozen_river"
    keys[rivers] = "river"
    keys[rivers & (coldest < -12)] = "frozen_river"
    return keys


def geographic_surface_biomes(height, elev, land, cover, climate, rivers, lakes, water_layers=None):
    lat = base.lat_grid()
    lon = base.lon_grid()
    sl = base.slope(height)
    coast = base.coast_mask(land)
    texture = base.climate_texture(lon, lat)
    patch = (
        0.50 * np.sin(lon * 3.7 + lat * 2.1)
        + 0.31 * np.sin(lon * 7.3 - lat * 4.9)
        + 0.19 * np.sin((lon + lat) * 11.7)
    )

    temp = climate["annual_temp"]
    coldest = climate["coldest_temp"]
    warmest = climate["warmest_temp"]
    temp_range = climate["temp_range"]
    precip = climate["annual_precip"]
    driest = climate["driest_precip"]
    seasonality = climate["precip_seasonality"]
    warm_rain_ratio = climate["warm_season_precip_ratio"]

    keys = EncodedBiomeMap(height.shape, "ocean")
    if water_layers is None:
        true_ocean = ~land
        inland_water = np.zeros_like(land, dtype=bool)
    else:
        true_ocean = water_layers["true_ocean_water"]
        inland_water = water_layers["inland_water"]
    sea_temp = base.ocean_temperature(lat, lon, height)
    deep_water = true_ocean & (height < 34)
    shallow_water = true_ocean & ~deep_water
    keys[shallow_water & (sea_temp >= 27.0)] = "warm_ocean"
    keys[shallow_water & (sea_temp >= 22.0) & (sea_temp < 27.0)] = "lukewarm_ocean"
    keys[shallow_water & (sea_temp >= 11.0) & (sea_temp < 22.0)] = "ocean"
    keys[shallow_water & (sea_temp >= 1.5) & (sea_temp < 11.0)] = "cold_ocean"
    keys[shallow_water & (sea_temp < 1.5)] = "frozen_ocean"
    keys[deep_water & (sea_temp >= 20.0)] = "deep_lukewarm_ocean"
    keys[deep_water & (sea_temp >= 9.0) & (sea_temp < 20.0)] = "deep_ocean"
    keys[deep_water & (sea_temp >= 0.5) & (sea_temp < 9.0)] = "deep_cold_ocean"
    keys[deep_water & (sea_temp < 0.5)] = "deep_frozen_ocean"
    keys[inland_water] = "river"
    keys[inland_water & (coldest < -12)] = "frozen_river"
    keys[land] = "plains"

    tree = land & (cover == 10)
    shrub = land & (cover == 20)
    grass = land & (cover == 30)
    cropland = land & (cover == 40)
    built = land & (cover == 50)
    bare = land & (cover == 60)
    snow_ice = land & (cover == 70)
    wet_cover = land & ((cover == 90) | (cover == 95))
    moss = land & (cover == 100)
    open_land = cropland | built | grass

    lowland = land & (height < 96) & (sl < 3.2)
    # Flat basins and steppe remain plains even when their real elevation maps
    # above the old absolute Minecraft-height threshold. Very high plateaus
    # retain their own geomorphology below.
    broad_plain = land & (elev < 2400) & (sl < 4.0)
    rolling = land & (elev < 2400) & (sl >= 2.2) & (sl < 5.2)
    mountain = land & ((height >= 125) | (sl >= 5.2))
    high_mountain = land & (height >= 158)
    plateau = land & (elev >= 2400) & (sl < 4.8)
    exposed = bare | snow_ice | moss | (mountain & ~tree)
    river_corridor = base.dilate(rivers, rounds=4) & land
    sheltered = land & (sl < 4.0) & ~coast & ~plateau

    tropical = (temp >= 20.0) & (coldest >= 10.0)
    subtropical = (temp >= 12.0) & (coldest > -3.0) & ~tropical
    temperate = (temp >= 4.0) & ~subtropical & ~tropical
    boreal = (temp < 4.0) | (coldest <= -15.0)
    severe_cold = (temp < -2.0) | (coldest <= -24.0)
    continental = temp_range >= 28.0

    east_china_warm_lowland = (
        land & (lon >= 109.0) & (lat <= 34.5) & (elev < 900)
        & (height < 112)
    )
    tibetan_high_plateau = land & (elev >= 3000) & (lat >= 27.0) & (lat <= 38.5) & (lon >= 76.0) & (lon <= 104.0)
    qaidam_tibet_margin = (
        land & (lat >= 31.5) & (lat <= 39.5)
        & (lon >= 83.0) & (lon <= 104.0)
    )
    northwest_badlands_domain = (
        land & (elev < 2600) & (lat >= 34.0) & (lon >= 84.0) & (lon <= 111.0)
        & (height < 150)
    )

    climate_demand = np.maximum(240.0, 32.0 * np.maximum(temp + 10.0, 2.0))
    aridity_index = precip / climate_demand
    hyper_arid = aridity_index < 0.24
    arid = aridity_index < 0.50
    semi_arid = aridity_index < 0.78
    humid = (aridity_index >= 0.95) & (precip >= 700)
    year_round_humid = humid & (driest >= 35) & (seasonality < 0.85)
    monsoonal = (warm_rain_ratio >= 0.52) & (seasonality >= 0.55)
    strongly_seasonal = seasonality >= 0.85
    cold_arid_highland = (
        land & (elev >= 1800)
        & ((temp < 7.0) | (coldest < -10.0))
        & (aridity_index < 0.85)
    )

    # Open real-world land controls settlement space before forest variety.
    keys[cropland | built] = "plains"
    keys[(cropland | built) & tropical & humid] = "sunflower_plains"
    keys[grass & tropical & ~arid] = "savanna"
    keys[grass & tropical & arid] = "savanna_plateau"
    keys[grass & subtropical & semi_arid] = "savanna"
    keys[grass & ~tropical & ~boreal & broad_plain] = "plains"
    keys[grass & ~tropical & ~boreal & ~broad_plain] = "meadow"
    keys[grass & boreal] = "snowy_plains"
    keys[open_land & severe_cold] = "snowy_plains"

    # Real forests are divided by climate regime and landform. Humid does not
    # imply dark forest: ordinary broadleaf forest is the default.
    tropical_rainforest = tree & tropical & (precip >= 1400) & (driest >= 15)
    keys[tropical_rainforest] = "jungle"
    keys[tree & tropical & humid & ~tropical_rainforest] = "sparse_jungle"
    keys[tree & tropical & ~humid] = "savanna"
    keys[tree & subtropical] = "forest"
    keys[tree & subtropical & semi_arid & continental & (temp < 15)] = "birch_forest"
    keys[tree & temperate] = "forest"
    keys[tree & temperate & semi_arid] = "birch_forest"
    keys[tree & boreal & ~severe_cold] = "taiga"
    keys[tree & severe_cold] = "snowy_taiga"

    # Special forests are rare ecological variants, not climate defaults.
    keys[
        tree & subtropical & year_round_humid & rolling
        & (warmest > 19) & (patch > 0.88)
    ] = "dark_forest"
    keys[
        tree & temperate & humid & rolling & (temp_range < 28)
        & (patch > 0.91)
    ] = "flower_forest"
    keys[
        tree & temperate & humid & rolling & continental
        & (patch > 0.90)
    ] = "old_growth_birch_forest"
    keys[
        tree & boreal & mountain & ~severe_cold & (patch > 0.65)
    ] = "old_growth_spruce_taiga"
    keys[
        tree & temperate & mountain & semi_arid & (patch > 0.68)
    ] = "old_growth_pine_taiga"
    keys[
        tree & subtropical & humid & mountain & monsoonal
        & (patch > 0.83)
    ] = "bamboo_jungle"

    # Sparse vegetation follows actual dryness and terrain form.
    keys[shrub & tropical & ~arid] = "savanna"
    keys[shrub & subtropical & ~arid] = "savanna"
    keys[shrub & temperate & semi_arid] = "meadow"
    keys[shrub & temperate & arid] = "savanna"
    keys[shrub & boreal] = "taiga"
    keys[bare & hyper_arid & broad_plain] = "desert"
    keys[bare & arid & ~hyper_arid & broad_plain] = "savanna"
    keys[bare & ~arid & rolling] = "windswept_gravelly_hills"
    keys[moss & boreal] = "snowy_plains"
    keys[wet_cover & tropical & humid] = "sparse_jungle"
    keys[wet_cover & ~tropical] = "plains"

    # Geomorphology has final authority in mountains and plateaus.
    keys[plateau & ~severe_cold & (grass | shrub)] = "meadow"
    keys[plateau & severe_cold & (grass | shrub | moss)] = "snowy_plains"
    keys[plateau & bare & hyper_arid] = "windswept_gravelly_hills"
    keys[mountain & tree & ~boreal & (sl >= 5.2)] = "windswept_forest"
    keys[mountain & exposed & ~boreal & ~arid & (height < 164)] = "windswept_hills"
    keys[mountain & exposed & arid & (height < 164)] = "windswept_savanna"
    keys[high_mountain & boreal] = "snowy_slopes"
    keys[high_mountain & exposed & ~boreal] = "stony_peaks"
    keys[land & (height >= 177) & severe_cold & (sl >= 4.2)] = "frozen_peaks"
    keys[land & (height >= 205)] = "jagged_peaks"
    keys[snow_ice & ~high_mountain] = "snowy_plains"

    # Rare terrain-specific variants use real cover and landform, then a stable
    # texture only to keep them fragmented and scarce.
    keys[northwest_badlands_domain & bare & hyper_arid & rolling & (patch > 0.78)] = "badlands"
    keys[northwest_badlands_domain & bare & hyper_arid & mountain & (patch > 0.86)] = "eroded_badlands"
    keys[northwest_badlands_domain & tree & semi_arid & rolling & (patch > 0.92)] = "wooded_badlands"
    keys[grass & subtropical & semi_arid & rolling & (patch > 0.72)] = "savanna_plateau"
    keys[snow_ice & plateau & severe_cold & (patch > 0.90)] = "ice_spikes"

    keys[land & coast & (height <= SEA_LEVEL + 4)] = "beach"
    keys[land & coast & (height <= SEA_LEVEL + 4) & (coldest < -10)] = "snowy_beach"
    keys[land & coast & (sl >= 5.0)] = "stony_shore"

    # Guard rails for places where real-world landform should dominate rare
    # Minecraft variants. These prevent high Tibetan plateaus from receiving
    # orange badlands patches and keep warm, low-elevation Jiangnan/coastal
    # plains from producing snow or frozen coast artifacts.
    tibetan_forbidden = np.isin(keys.data, [
        BIOME_CODES["badlands"],
        BIOME_CODES["eroded_badlands"],
        BIOME_CODES["wooded_badlands"],
        BIOME_CODES["windswept_hills"],
        BIOME_CODES["windswept_savanna"],
    ])
    keys[tibetan_high_plateau & tibetan_forbidden] = "stony_peaks"
    keys[tibetan_high_plateau & ~severe_cold & (height < 145) & ~bare] = "meadow"
    keys[tibetan_high_plateau & severe_cold & (height < 145)] = "snowy_plains"
    keys[tibetan_high_plateau & ((bare | moss) & hyper_arid)] = "stony_peaks"
    keys[tibetan_high_plateau & severe_cold & (height >= 145)] = "snowy_slopes"
    keys[tibetan_high_plateau & (height >= 174)] = "frozen_peaks"
    keys[tibetan_high_plateau & bare & hyper_arid & (patch > 0.88)] = "windswept_gravelly_hills"

    # Global highland guard: cold or dry elevated terrain should not inherit
    # warm savanna-style mountain variants. This is intentionally broader than
    # Tibet so the same rule protects future Andes, Rockies, and Central Asian
    # highland maps.
    highland_guard = (cold_arid_highland | qaidam_tibet_margin) & np.isin(keys.data, [
        BIOME_CODES["windswept_hills"],
        BIOME_CODES["windswept_savanna"],
        BIOME_CODES["badlands"],
        BIOME_CODES["eroded_badlands"],
        BIOME_CODES["wooded_badlands"],
    ])
    keys[highland_guard & severe_cold & (height >= 145)] = "snowy_slopes"
    keys[highland_guard & severe_cold & (height < 145)] = "snowy_plains"
    keys[highland_guard & ~severe_cold & (height >= 158)] = "stony_peaks"
    keys[highland_guard & ~severe_cold & (height < 158) & (bare | moss | hyper_arid)] = "windswept_gravelly_hills"
    keys[highland_guard & ~severe_cold & (height < 158) & ~(bare | moss | hyper_arid)] = "meadow"

    keys[east_china_warm_lowland & np.isin(keys.data, [
        BIOME_CODES["snowy_plains"],
        BIOME_CODES["snowy_taiga"],
        BIOME_CODES["snowy_slopes"],
        BIOME_CODES["frozen_peaks"],
        BIOME_CODES["ice_spikes"],
        BIOME_CODES["snowy_beach"],
    ])] = "plains"
    keys[east_china_warm_lowland & coast & (height <= SEA_LEVEL + 4)] = "beach"

    northern_birch_w = np.maximum.reduce([
        base.oval(lon, lat, 123.5, 50.0, 4.8, 4.0),  # Da Hinggan
        base.oval(lon, lat, 128.0, 48.0, 3.6, 2.6),  # Xiao Hinggan
        base.oval(lon, lat, 127.5, 42.5, 3.0, 2.0),  # Changbai
        base.oval(lon, lat, 118.0, 40.5, 3.2, 1.8),  # Yanshan
        base.oval(lon, lat, 113.5, 38.0, 2.6, 1.6),  # North Taihang
        base.oval(lon, lat, 108.0, 33.8, 3.4, 1.4),  # Qinling
        base.oval(lon, lat, 127.6, 40.0, 2.6, 2.8),  # Korea north/central
    ])
    northern_birch_candidate = (
        tree & ~tropical & (elev < 2400) & (height >= 88)
        & (sl >= 1.4) & ((northern_birch_w + patch * 0.04) > 0.26)
    )
    keys[northern_birch_candidate] = "birch_forest"
    keys[
        northern_birch_candidate & (sl >= 2.4)
        & ((northern_birch_w + patch * 0.06) > 0.48)
    ] = "old_growth_birch_forest"

    keys[lakes] = "river"
    keys[lakes & (coldest < -12)] = "frozen_river"
    keys[rivers] = "river"
    keys[rivers & (coldest < -12)] = "frozen_river"
    return keys


def count_biomes(surface, names, mask):
    codes = [BIOME_CODES[name] for name in names]
    return int((np.isin(surface.data, codes) & mask).sum())


def validate_surface_biome_consistency(surface, land, water_layers, height, elev, climate):
    land_surface = land & ~water_layers["inland_lake_water"] & ~water_layers["river_water"]
    true_ocean = water_layers["true_ocean_water"]
    inland_water = water_layers["inland_water"]
    ocean_codes = [BIOME_CODES[name] for name in OCEAN_BIOMES]
    land_codes = [BIOME_CODES[name] for name in LAND_BIOMES]

    inland_ocean_hits = count_biomes(surface, OCEAN_BIOMES, inland_water)
    land_ocean_hits = count_biomes(surface, OCEAN_BIOMES, land_surface)
    ocean_land_hits = int((np.isin(surface.data, land_codes) & true_ocean).sum())
    ocean_pixels = int(true_ocean.sum())
    inland_pixels = int(inland_water.sum())

    offshore_px = ndimage.distance_transform_edt(true_ocean).astype(np.float32)
    offshore_ocean = true_ocean & (offshore_px >= 3.0)
    shallow_offshore = int((offshore_ocean & (height > SEA_LEVEL - 8)).sum())

    lat = base.lat_grid()
    lon = base.lon_grid()
    temp = climate["annual_temp"]
    coldest = climate["coldest_temp"]
    precip = climate["annual_precip"]
    climate_demand = np.maximum(240.0, 32.0 * np.maximum(temp + 10.0, 2.0))
    aridity_index = precip / climate_demand
    tibetan_high_plateau = (
        land & (elev >= 3000)
        & (lat >= 27.0) & (lat <= 38.5)
        & (lon >= 76.0) & (lon <= 104.0)
    )
    tibetan_forbidden_hits = count_biomes(
        surface,
        ["badlands", "eroded_badlands", "wooded_badlands", "windswept_hills", "windswept_savanna"],
        tibetan_high_plateau,
    )
    cold_arid_highland = (
        land & (elev >= 1800)
        & ((temp < 7.0) | (coldest < -10.0))
        & (aridity_index < 0.85)
    )
    qaidam_tibet_margin = (
        land & (lat >= 31.5) & (lat <= 39.5)
        & (lon >= 83.0) & (lon <= 104.0)
    )
    highland_guard_domain = cold_arid_highland | qaidam_tibet_margin
    highland_forbidden_hits = count_biomes(
        surface,
        ["badlands", "eroded_badlands", "wooded_badlands", "windswept_hills", "windswept_savanna"],
        highland_guard_domain,
    )

    northern_birch_domain = land & (
        (base.oval(lon, lat, 123.5, 50.0, 4.8, 4.0) > 0.22)
        | (base.oval(lon, lat, 128.0, 48.0, 3.6, 2.6) > 0.22)
        | (base.oval(lon, lat, 127.5, 42.5, 3.0, 2.0) > 0.22)
        | (base.oval(lon, lat, 108.0, 33.8, 3.4, 1.4) > 0.28)
    )
    birch_hits = count_biomes(surface, ["birch_forest", "old_growth_birch_forest"], northern_birch_domain)

    audit = {
        "ocean_vs_inland_water_counts": {
            "true_ocean_water_pixels": ocean_pixels,
            "inland_water_pixels": inland_pixels,
        },
        "inland_lake_biome_audit": {
            "inland_water_pixels_with_ocean_biome": inland_ocean_hits,
        },
        "land_ocean_biome_audit": {
            "land_pixels_with_ocean_biome": land_ocean_hits,
            "true_ocean_pixels_with_land_biome": ocean_land_hits,
        },
        "coastal_shallow_shelf_audit": {
            "true_ocean_pixels_at_least_3px_offshore": int(offshore_ocean.sum()),
            "offshore_pixels_shallower_than_8_blocks": shallow_offshore,
        },
        "plateau_surface_biome_audit": {
            "tibetan_high_plateau_pixels": int(tibetan_high_plateau.sum()),
            "forbidden_plateau_biome_hits": tibetan_forbidden_hits,
            "cold_arid_highland_guard_pixels": int(highland_guard_domain.sum()),
            "forbidden_highland_biome_hits": highland_forbidden_hits,
        },
        "northern_birch_presence_audit": {
            "target_domain_pixels": int(northern_birch_domain.sum()),
            "birch_pixels": birch_hits,
        },
    }

    failures = {
        key: value
        for key, value in {
            "inland_water_ocean_biomes": inland_ocean_hits,
            "land_ocean_biomes": land_ocean_hits,
            "true_ocean_land_biomes": ocean_land_hits,
            "tibetan_forbidden_biomes": tibetan_forbidden_hits,
            "cold_arid_highland_forbidden_biomes": highland_forbidden_hits,
        }.items()
        if value
    }
    if failures:
        raise RuntimeError(f"Surface biome consistency failed: {failures}")
    return audit


def write_previews(height, surface, cover, climate):
    preview = np.zeros((SIZE_Y, SIZE_X, 3), dtype=np.uint8)
    for key, color in SURFACE_COLORS.items():
        rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        preview[surface == key] = rgb
    shade = np.clip((height.astype(np.float32) - 43) / 172.0, 0.38, 1.12)[..., None]
    preview = np.clip(preview.astype(np.float32) * shade, 0, 255).astype(np.uint8)
    Image.fromarray(preview, "RGB").resize(
        (1600, int(1600 * SIZE_Y / SIZE_X)), Image.Resampling.LANCZOS
    ).save(OUT_ROOT / "china_v23_4x_area_global_rules_preview.png")

    cover_colors = {
        0: (80, 80, 80), 10: (0, 100, 0), 20: (255, 187, 34), 30: (255, 255, 76),
        40: (240, 150, 255), 50: (250, 0, 0), 60: (180, 180, 180), 70: (240, 240, 240),
        80: (0, 100, 200), 90: (0, 150, 160), 95: (0, 207, 117), 100: (250, 230, 160),
    }
    cover_rgb = np.zeros((SIZE_Y, SIZE_X, 3), dtype=np.uint8)
    for class_id, color in cover_colors.items():
        cover_rgb[cover == class_id] = color
    Image.fromarray(cover_rgb, "RGB").resize(
        (1600, int(1600 * SIZE_Y / SIZE_X)), Image.Resampling.NEAREST
    ).save(OUT_ROOT / "china_v23_4x_area_worldcover_preview.png")

    temp = climate["annual_temp"]
    precip = climate["annual_precip"]
    climate_rgb = np.zeros((SIZE_Y, SIZE_X, 3), dtype=np.uint8)
    climate_rgb[..., 0] = np.clip((temp + 15) / 45 * 255, 0, 255).astype(np.uint8)
    climate_rgb[..., 1] = np.clip(precip / 2200 * 255, 0, 255).astype(np.uint8)
    climate_rgb[..., 2] = np.clip((30 - temp) / 45 * 255, 0, 255).astype(np.uint8)
    Image.fromarray(climate_rgb, "RGB").resize(
        (1600, int(1600 * SIZE_Y / SIZE_X)), Image.Resampling.LANCZOS
    ).save(OUT_ROOT / "china_v23_4x_area_worldclim_preview.png")


def sanitize_ore_cave_biomes():
    biome_dir = PACK / "data/china/worldgen/biome"
    sanitized = 0
    hazardous_underground_features = {
        "minecraft:amethyst_geode",
        "minecraft:underwater_magma",
        "minecraft:disk_sand",
        "minecraft:disk_clay",
        "minecraft:disk_gravel",
    }
    for path in biome_dir.glob("ore_combo_*.json"):
        biome = json.loads(path.read_text(encoding="utf-8"))
        old_features = biome.get("features", [])
        safe_ore_features = []
        if len(old_features) > 6:
            safe_ore_features = [
                feature
                for feature in old_features[6]
                if isinstance(feature, str)
                and feature not in hazardous_underground_features
            ]

        # Keep ordinary ores and safe underground decoration because this biome
        # replaces the surface biome below its mapped Y range. Remove only
        # terrain-cutting or fluid-producing features that can tear open
        # lowlands or expose lava on high plateaus.
        features = [[] for _ in range(11)]
        if len(old_features) > 2:
            features[2] = [
                feature
                for feature in old_features[2]
                if feature not in hazardous_underground_features
            ]
        if len(old_features) > 3:
            features[3] = old_features[3]
        features[6] = safe_ore_features
        if len(old_features) > 9:
            features[9] = old_features[9]
        biome["carvers"] = {}
        biome["features"] = features
        write_json(path, biome)
        sanitized += 1
    return sanitized


def merge_v17_ore_system(map_info):
    if not ORE_SOURCE.exists():
        raise FileNotFoundError(f"Missing V17 ore source pack: {ORE_SOURCE}")
    shutil.copytree(ORE_SOURCE / "data/china/worldgen", PACK / "data/china/worldgen", dirs_exist_ok=True)
    shutil.copytree(
        ORE_SOURCE / "data/minecraft/tags/worldgen/biome",
        PACK / "data/minecraft/tags/worldgen/biome",
        dirs_exist_ok=True,
    )
    ore_zones = Image.open(
        ORE_SOURCE / "data/china/novoatlas/biome_map/ore_zones.png"
    ).convert("RGB")
    ore_zones.resize((SIZE_X, SIZE_Y), Image.Resampling.NEAREST).save(
        PACK / "data/china/novoatlas/biome_map/ore_zones.png"
    )
    ore_map_info = json.loads(
        (ORE_SOURCE / "data/china/novoatlas/map_info/china.json").read_text(encoding="utf-8")
    )
    map_info["cave_biomes"] = ore_map_info["cave_biomes"]
    for layer in map_info["cave_biomes"].get("layers", []):
        y_range = layer.setdefault("y_range", {})
        y_range["max"] = min(int(y_range.get("max", SEA_LEVEL - 15)), SEA_LEVEL - 15)
    return sanitize_ore_cave_biomes()


def audit_ore_cave_biomes():
    forbidden = [
        "lake_lava",
        "spring_lava",
        "underwater_magma",
        "spring_water",
        "amethyst_geode",
        "minecraft:cave",
        "minecraft:canyon",
        "minecraft:disk_",
    ]
    violations = []
    biome_dir = PACK / "data/china/worldgen/biome"
    for path in biome_dir.glob("ore_combo_*.json"):
        text = path.read_text(encoding="utf-8")
        found = [token for token in forbidden if token in text]
        if found:
            violations.append({"file": path.name, "forbidden": found})
    if violations:
        raise RuntimeError(f"Hazardous ore cave biome features remain: {violations[:5]}")
    return len(list(biome_dir.glob("ore_combo_*.json")))


def audit_cave_biome_y_range(map_info):
    unsafe = []
    for index, layer in enumerate(map_info.get("cave_biomes", {}).get("layers", [])):
        max_y = layer.get("y_range", {}).get("max")
        if max_y is None or max_y > SEA_LEVEL - 15:
            unsafe.append({"layer": index, "max": max_y})
    if unsafe:
        raise RuntimeError(f"Unsafe cave biome Y ranges remain: {unsafe}")
    return {
        "max_allowed_y": SEA_LEVEL - 15,
        "layers": [
            layer.get("y_range", {})
            for layer in map_info.get("cave_biomes", {}).get("layers", [])
        ],
    }


def write_vanilla_surface_safety_overrides():
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
            {
                "feature": feature,
                "placement": [never_place],
            },
        )


def build():
    if PACK.exists():
        shutil.rmtree(PACK)
    for relative in [
        "data/china/novoatlas/heightmap",
        "data/china/novoatlas/biome_map",
        "data/china/novoatlas/map_info",
        "data/minecraft/dimension",
        "data/minecraft/worldgen/placed_feature",
    ]:
        (PACK / relative).mkdir(parents=True, exist_ok=True)

    climate = sample_worldclim()
    raw_cover = sample_worldcover()
    cover = stabilize_landcover(raw_cover)
    elev = sample_elevation_equirectangular()
    height, land = minecraft_height_with_bathymetry(elev, raw_cover)
    lakes = base.lake_mask()
    height, water_lakes, _ = base.carve_lakes(height, lakes)
    rivers = base.river_mask(land & ~water_lakes)
    height, water_rivers = conservative_river_pass(height, rivers, land)
    water_layers = classify_water_layers(land, raw_cover, lakes, water_lakes, water_rivers)
    surface_land = land & ~water_layers["inland_lake_water"]
    surface = geographic_surface_biomes(
        height,
        elev,
        surface_land,
        cover,
        climate,
        water_layers["river_water"],
        water_layers["inland_lake_water"],
        water_layers,
    )
    consistency_audit = validate_surface_biome_consistency(surface, land, water_layers, height, elev, climate)

    Image.fromarray(height, "L").save(PACK / "data/china/novoatlas/heightmap/china.png")
    base.color_image(surface, SURFACE_COLORS).save(PACK / "data/china/novoatlas/biome_map/china.png")

    map_info = {
        "starting_y": 0,
        "horizontal_scale": 1,
        "vertical_scale": 1,
        "height_map": "china:china",
        "surface_biomes": {
            "map": "china:china",
            "biomes": [
                {"biome": SURFACE_BIOMES[key], "color": SURFACE_COLORS[key]}
                for key in SURFACE_COLORS
            ],
        },
    }
    sanitized_ore_biomes = merge_v17_ore_system(map_info)
    write_json(PACK / "data/china/novoatlas/map_info/china.json", map_info)
    write_json(
        PACK / "data/minecraft/dimension/overworld.json",
        {
            "type": "minecraft:overworld",
            "generator": {
                "type": "novoatlas:image_map",
                "map_info": "china:china",
                "settings": "minecraft:overworld",
                "underground_density_function": "novoatlas:caves",
                "biome_source": {
                    "type": "novoatlas:color_map",
                    "map_info": "china:china",
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
                "description": "NovoAtlas China V23 4x area: global hydrology rules, guarded oceans/plateaus, safe balanced composite ores",
            }
        },
    )

    write_vanilla_surface_safety_overrides()
    write_previews(height, surface, cover, climate)
    stats = surface.counts()
    write_json(
        OUT_ROOT / "china_v23_4x_area_generation_report.json",
        {
            "pack": str(PACK),
            "size_blocks": {"x": SIZE_X, "z": SIZE_Y},
            "surface_biome_counts": stats,
            **consistency_audit,
            "excluded_surface_biomes": ["minecraft:mushroom_fields", "minecraft:cherry_grove", "minecraft:swamp", "minecraft:mangrove_swamp"],
            "real_data": [
                "AWS Terrarium global elevation and bathymetry",
                "WorldClim 2.1 2.5-minute monthly mean temperature and precipitation",
                "ESA WorldCover 2021 real land cover sampled from official WMTS",
                "HydroRIVERS real river vectors",
                "Natural Earth real lake polygons",
            ],
            "biome_logic": "V23 classifies inland water, rivers, true ocean, and coast bands before biome mapping; ocean biomes only apply to sea-connected water, high plateaus use whitelisted cold/stony/meadow biomes, and northern mixed-forest domains receive stable birch patches.",
            "ore_system": "V17 balanced five-level, spatially decaying, multi-mineral enrichment retained; cave biomes keep safe vanilla underground ores, add rich veins without fluid or terrain-cutting features, and are capped below the surface-risk Y range.",
            "sanitized_ore_cave_biomes": sanitized_ore_biomes,
            "audited_safe_ore_cave_biomes": audit_ore_cave_biomes(),
            "cave_biome_surface_leak_audit": audit_cave_biome_y_range(map_info),
        },
    )
    print(f"Built {PACK}")


if __name__ == "__main__":
    build()
