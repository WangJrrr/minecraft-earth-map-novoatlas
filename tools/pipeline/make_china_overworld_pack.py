import json
import math
import os
import shutil
import struct
import time
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "tile_cache"
VECTOR_CACHE = ROOT / "vector_cache"
PROJECT_ROOT = ROOT.parents[1]
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
PACK = OUT_ROOT / "NovoAtlas_China_Overworld_Scale_Japan2048_v12"

BBOX = {"west": 73.0, "south": 18.0, "east": 135.0, "north": 54.0}
JAPAN_REFERENCE = {"west": 128.0, "south": 30.0, "east": 146.0, "north": 46.0, "size": 2048}
SIZE_X = int(round((BBOX["east"] - BBOX["west"]) / ((JAPAN_REFERENCE["east"] - JAPAN_REFERENCE["west"]) / JAPAN_REFERENCE["size"])))
SIZE_Y = int(round((BBOX["north"] - BBOX["south"]) / ((JAPAN_REFERENCE["north"] - JAPAN_REFERENCE["south"]) / JAPAN_REFERENCE["size"])))
ZOOM = 7
SEA_LEVEL = 63

SURFACE_COLORS = {
    "deep_ocean": "#10175E",
    "deep_cold_ocean": "#13205F",
    "deep_frozen_ocean": "#738B9E",
    "deep_lukewarm_ocean": "#1E4687",
    "ocean": "#313A8B",
    "cold_ocean": "#19248A",
    "frozen_ocean": "#A8D2E6",
    "lukewarm_ocean": "#2D6FA3",
    "warm_ocean": "#2FAFB0",
    "river": "#254E9C",
    "frozen_river": "#9FC8DF",
    "beach": "#C4B058",
    "plains": "#6D923D",
    "sunflower_plains": "#A0B94C",
    "meadow": "#7FC458",
    "forest": "#4A8A38",
    "birch_forest": "#5F9B43",
    "dark_forest": "#274E24",
    "jungle": "#338C2A",
    "sparse_jungle": "#4B9C31",
    "bamboo_jungle": "#2F7E2B",
    "taiga": "#338553",
    "old_growth_spruce_taiga": "#224D20",
    "snowy_plains": "#D8E1E3",
    "snowy_taiga": "#AFC8C5",
    "grove": "#8AAD88",
    "windswept_forest": "#6A7251",
    "stony_shore": "#525252",
    "stony_peaks": "#939393",
    "snowy_slopes": "#DDE5E7",
    "jagged_peaks": "#FFFFFF",
    "desert": "#D6C26D",
    "savanna": "#BDB35D",
    "badlands": "#C06C3A",
    "wooded_badlands": "#9B6B3E",
    "eroded_badlands": "#D07A45",
}

SURFACE_BIOMES = {
    key: f"minecraft:{key}" for key in SURFACE_COLORS
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lonlat_to_tile_float(lon, lat, zoom):
    lat_rad = math.radians(lat)
    n = 2 ** zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def get_tile(z, x, y):
    path = CACHE / str(z) / str(x) / f"{y}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            return Image.open(path).convert("RGB")
        except Exception:
            path.unlink()
    urls = [
        f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
        f"https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png",
        f"http://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
    ]
    last_error = None
    for attempt in range(5):
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "minecraft-earth-map-novoatlas"})
                with urllib.request.urlopen(req, timeout=45) as resp:
                    path.write_bytes(resp.read())
                return Image.open(path).convert("RGB")
            except Exception as exc:
                last_error = exc
        time.sleep(1.5 + attempt)
    raise last_error


def decode_terrarium(rgb):
    arr = rgb.astype(np.float32)
    return arr[..., 0] * 256.0 + arr[..., 1] + arr[..., 2] / 256.0 - 32768.0


def sample_elevation():
    west_x, north_y = lonlat_to_tile_float(BBOX["west"], BBOX["north"], ZOOM)
    east_x, south_y = lonlat_to_tile_float(BBOX["east"], BBOX["south"], ZOOM)
    min_tx, max_tx = math.floor(west_x), math.floor(east_x)
    min_ty, max_ty = math.floor(north_y), math.floor(south_y)
    mosaic = np.zeros(((max_ty - min_ty + 1) * 256, (max_tx - min_tx + 1) * 256, 3), dtype=np.uint8)
    for ty in range(min_ty, max_ty + 1):
        for tx in range(min_tx, max_tx + 1):
            tile = np.asarray(get_tile(ZOOM, tx, ty), dtype=np.uint8)
            oy, ox = (ty - min_ty) * 256, (tx - min_tx) * 256
            mosaic[oy:oy + 256, ox:ox + 256] = tile
    px_w = (west_x - min_tx) * 256
    px_e = (east_x - min_tx) * 256
    py_n = (north_y - min_ty) * 256
    py_s = (south_y - min_ty) * 256
    xs = np.linspace(px_w, px_e, SIZE_X, dtype=np.float32).astype(np.int32)
    ys = np.linspace(py_n, py_s, SIZE_Y, dtype=np.float32).astype(np.int32)
    sampled = mosaic[ys[:, None], xs[None, :]]
    elev = decode_terrarium(sampled)
    elev[elev > 9000] = 0
    return elev


def smooth(arr, rounds=2):
    out = arr.astype(np.float32)
    for _ in range(rounds):
        p = np.pad(out, 1, mode="edge")
        out = (
            p[:-2, :-2] + p[:-2, 1:-1] * 2 + p[:-2, 2:]
            + p[1:-1, :-2] * 2 + p[1:-1, 1:-1] * 4 + p[1:-1, 2:] * 2
            + p[2:, :-2] + p[2:, 1:-1] * 2 + p[2:, 2:]
        ) / 16.0
    return out


def minecraft_height(elev):
    land = elev > 0
    y = np.full(elev.shape, 40.0, dtype=np.float32)
    low = land & (elev < 700)
    mid = land & (elev >= 700) & (elev < 2500)
    high = land & (elev >= 2500)
    y[low] = SEA_LEVEL + np.power(np.clip(elev[low], 0, 700) / 700.0, 0.85) * 34.0
    y[mid] = 97 + np.power((elev[mid] - 700) / 1800.0, 0.95) * 54.0
    y[high] = 151 + np.power(np.clip(elev[high] - 2500, 0, 5500) / 5500.0, 0.72) * 72.0
    y = smooth(y, rounds=2)
    y[~land] = np.clip(SEA_LEVEL + elev[~land] / 180.0, 22, 54)
    return np.clip(np.round(y), 0, 255).astype(np.uint8), land


def lat_grid():
    return np.linspace(BBOX["north"], BBOX["south"], SIZE_Y, dtype=np.float32)[:, None]


def lon_grid():
    return np.linspace(BBOX["west"], BBOX["east"], SIZE_X, dtype=np.float32)[None, :]


def slope(height):
    gy, gx = np.gradient(height.astype(np.float32))
    return np.maximum(np.abs(gx), np.abs(gy))


def coast_mask(land):
    p = np.pad(land, 2, mode="edge")
    ocean_near = np.zeros_like(land, dtype=bool)
    for dy in range(5):
        for dx in range(5):
            ocean_near |= ~p[dy:dy + SIZE_Y, dx:dx + SIZE_X]
    return land & ocean_near


def in_box(lon, lat, west, south, east, north):
    return (lon >= west) & (lon <= east) & (lat >= south) & (lat <= north)


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def oval(lon, lat, cx, cy, sx, sy):
    return np.exp(-0.5 * (((lon - cx) / sx) ** 2 + ((lat - cy) / sy) ** 2))


def climate_texture(lon, lat):
    return (
        0.55 * np.sin(lon * 0.73 + lat * 0.41)
        + 0.35 * np.sin(lon * 1.37 - lat * 0.88)
        + 0.20 * np.sin((lon + lat) * 2.17)
    )


def color_image(keys, colors):
    img = np.zeros((SIZE_Y, SIZE_X, 4), dtype=np.uint8)
    for key, color in colors.items():
        rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        img[keys == key, :3] = rgb
        img[keys == key, 3] = 255
    return Image.fromarray(img, "RGBA")


def to_pixel(lon, lat):
    x = (lon - BBOX["west"]) / (BBOX["east"] - BBOX["west"]) * (SIZE_X - 1)
    y = (BBOX["north"] - lat) / (BBOX["north"] - BBOX["south"]) * (SIZE_Y - 1)
    return x, y


HYDRORIVERS_ZIP = VECTOR_CACHE / "HydroRIVERS_v10_as_shp.zip"
HYDRORIVERS_SHP = "HydroRIVERS_v10_as_shp/HydroRIVERS_v10_as.shp"
HYDRORIVERS_DBF = "HydroRIVERS_v10_as_shp/HydroRIVERS_v10_as.dbf"
RIVER_MASK_CACHE = ROOT / f"hydrorivers_river_mask_v11_{SIZE_X}x{SIZE_Y}.npy"
LAKES_ZIP = VECTOR_CACHE / "ne_10m_lakes.zip"
LAKES_SHP = "ne_10m_lakes.shp"
LAKES_DBF = "ne_10m_lakes.dbf"
LAKE_MASK_CACHE = ROOT / f"ne_lakes_mask_v12_{SIZE_X}x{SIZE_Y}.npy"


def dbf_fields(dbf):
    fields = {}
    pos = 32
    offset = 1
    while dbf[pos] != 13:
        raw = dbf[pos:pos + 32]
        name = raw[:11].split(b"\0", 1)[0].decode("latin1")
        size = raw[16]
        fields[name] = (offset, size)
        offset += size
        pos += 32
    return fields


def dbf_float(record, fields, name):
    offset, size = fields[name]
    value = record[offset:offset + size].strip()
    return float(value) if value else 0.0


def hydroriver_selected(flow, upland, length):
    return flow >= 300.0 or upland >= 25000.0 or (flow >= 160.0 and length >= 45.0)


def hydroriver_radius(flow, upland):
    if flow >= 12000.0 or upland >= 800000.0:
        return 7
    if flow >= 5000.0 or upland >= 250000.0:
        return 5
    if flow >= 1500.0 or upland >= 80000.0:
        return 4
    if flow >= 450.0 or upland >= 25000.0:
        return 3
    return 2


def read_hydrorivers():
    if not HYDRORIVERS_ZIP.exists():
        raise FileNotFoundError(
            f"Missing {HYDRORIVERS_ZIP}. Download HydroRIVERS_v10_as_shp.zip first."
        )

    with zipfile.ZipFile(HYDRORIVERS_ZIP) as source:
        shp = source.read(HYDRORIVERS_SHP)
        dbf = source.read(HYDRORIVERS_DBF)

    fields = dbf_fields(dbf)
    dbf_header_len = struct.unpack("<H", dbf[8:10])[0]
    dbf_record_len = struct.unpack("<H", dbf[10:12])[0]
    selected = []
    pos = 100
    index = 0
    margin = 0.4

    while pos < len(shp):
        content_len = struct.unpack(">i", shp[pos + 4:pos + 8])[0] * 2
        pos += 8
        end = pos + content_len
        shape_type = struct.unpack("<i", shp[pos:pos + 4])[0]

        if shape_type == 3:
            xmin, ymin, xmax, ymax = struct.unpack("<4d", shp[pos + 4:pos + 36])
            intersects = (
                xmax >= BBOX["west"] - margin
                and xmin <= BBOX["east"] + margin
                and ymax >= BBOX["south"] - margin
                and ymin <= BBOX["north"] + margin
            )
            if intersects:
                record = dbf[
                    dbf_header_len + index * dbf_record_len:
                    dbf_header_len + (index + 1) * dbf_record_len
                ]
                flow = dbf_float(record, fields, "DIS_AV_CMS")
                upland = dbf_float(record, fields, "UPLAND_SKM")
                length = dbf_float(record, fields, "LENGTH_KM")

                if hydroriver_selected(flow, upland, length):
                    num_parts, num_points = struct.unpack("<2i", shp[pos + 36:pos + 44])
                    parts = list(struct.unpack(
                        f"<{num_parts}i",
                        shp[pos + 44:pos + 44 + num_parts * 4],
                    ))
                    parts.append(num_points)
                    point_offset = pos + 44 + num_parts * 4
                    radius = hydroriver_radius(flow, upland)
                    selected.append((point_offset, parts, radius, shp))

        pos = end
        index += 1

    return selected


def dbf_text(record, fields, name):
    offset, size = fields[name]
    return record[offset:offset + size].decode("utf-8", "ignore").replace("\0", "").strip()


def lake_selected(xmin, ymin, xmax, ymax, min_zoom):
    if xmax < BBOX["west"] or xmin > BBOX["east"] or ymax < BBOX["south"] or ymin > BBOX["north"]:
        return False
    lon_span = max(0.0, min(xmax, BBOX["east"]) - max(xmin, BBOX["west"]))
    lat_span = max(0.0, min(ymax, BBOX["north"]) - max(ymin, BBOX["south"]))
    px_w = lon_span / (BBOX["east"] - BBOX["west"]) * SIZE_X
    px_h = lat_span / (BBOX["north"] - BBOX["south"]) * SIZE_Y
    return min_zoom <= 7.6 or px_w * px_h >= 8.0 or max(px_w, px_h) >= 6.0


def lake_mask():
    if LAKE_MASK_CACHE.exists():
        cached = np.load(LAKE_MASK_CACHE)
        if cached.shape == (SIZE_Y, SIZE_X):
            return cached

    if not LAKES_ZIP.exists():
        raise FileNotFoundError(f"Missing {LAKES_ZIP}. Download ne_10m_lakes.zip first.")

    start = time.time()
    with zipfile.ZipFile(LAKES_ZIP) as source:
        shp = source.read(LAKES_SHP)
        dbf = source.read(LAKES_DBF)

    fields = dbf_fields(dbf)
    dbf_header_len = struct.unpack("<H", dbf[8:10])[0]
    dbf_record_len = struct.unpack("<H", dbf[10:12])[0]
    image = Image.new("1", (SIZE_X, SIZE_Y), 0)
    draw = ImageDraw.Draw(image)
    pos = 100
    index = 0
    drawn = 0

    while pos < len(shp):
        content_len = struct.unpack(">i", shp[pos + 4:pos + 8])[0] * 2
        pos += 8
        end = pos + content_len
        shape_type = struct.unpack("<i", shp[pos:pos + 4])[0]

        if shape_type == 5:
            xmin, ymin, xmax, ymax = struct.unpack("<4d", shp[pos + 4:pos + 36])
            record = dbf[
                dbf_header_len + index * dbf_record_len:
                dbf_header_len + (index + 1) * dbf_record_len
            ]
            min_zoom = dbf_float(record, fields, "min_zoom") if "min_zoom" in fields else 9.0
            if lake_selected(xmin, ymin, xmax, ymax, min_zoom):
                num_parts, num_points = struct.unpack("<2i", shp[pos + 36:pos + 44])
                parts = list(struct.unpack(
                    f"<{num_parts}i",
                    shp[pos + 44:pos + 44 + num_parts * 4],
                ))
                parts.append(num_points)
                point_offset = pos + 44 + num_parts * 4
                for part_start, part_end in zip(parts, parts[1:]):
                    ring = []
                    for point_index in range(part_start, part_end):
                        offset = point_offset + point_index * 16
                        lon, lat = struct.unpack("<2d", shp[offset:offset + 16])
                        if (
                            BBOX["west"] - 0.3 <= lon <= BBOX["east"] + 0.3
                            and BBOX["south"] - 0.3 <= lat <= BBOX["north"] + 0.3
                        ):
                            x, y = to_pixel(lon, lat)
                            ring.append((int(round(x)), int(round(y))))
                    if len(ring) >= 3:
                        draw.polygon(ring, fill=1)
                        drawn += 1

        pos = end
        index += 1

    mask = np.array(image, dtype=bool)
    np.save(LAKE_MASK_CACHE, mask)
    print(f"Natural Earth lake mask built in {time.time() - start:.1f}s from {drawn} rings")
    return mask


def draw_segment(mask, x0, y0, x1, y1, radius):
    min_x = max(0, int(math.floor(min(x0, x1) - radius - 2)))
    max_x = min(SIZE_X - 1, int(math.ceil(max(x0, x1) + radius + 2)))
    min_y = max(0, int(math.floor(min(y0, y1) - radius - 2)))
    max_y = min(SIZE_Y - 1, int(math.ceil(max(y0, y1) + radius + 2)))
    if min_x > max_x or min_y > max_y:
        return
    yy, xx = np.ogrid[min_y:max_y + 1, min_x:max_x + 1]
    vx = x1 - x0
    vy = y1 - y0
    denom = vx * vx + vy * vy
    if denom <= 0:
        dist = np.sqrt((xx - x0) ** 2 + (yy - y0) ** 2)
    else:
        t = np.clip(((xx - x0) * vx + (yy - y0) * vy) / denom, 0, 1)
        px = x0 + t * vx
        py = y0 + t * vy
        dist = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)
    mask[min_y:max_y + 1, min_x:max_x + 1] |= dist <= radius


def smooth_points(points, rounds=2):
    smoothed = list(points)
    for _ in range(rounds):
        next_points = [smoothed[0]]
        for p0, p1 in zip(smoothed, smoothed[1:]):
            q = (p0[0] * 0.75 + p1[0] * 0.25, p0[1] * 0.75 + p1[1] * 0.25)
            r = (p0[0] * 0.25 + p1[0] * 0.75, p0[1] * 0.25 + p1[1] * 0.75)
            next_points.extend([q, r])
        next_points.append(smoothed[-1])
        smoothed = next_points
    return smoothed


def river_mask(land):
    if RIVER_MASK_CACHE.exists():
        cached = np.load(RIVER_MASK_CACHE)
        if cached.shape == land.shape:
            return cached & land

    start = time.time()
    mask = np.zeros((SIZE_Y, SIZE_X), dtype=bool)
    for point_offset, parts, radius, shp in read_hydrorivers():
        for part_start, part_end in zip(parts, parts[1:]):
            previous = None
            for point_index in range(part_start, part_end):
                offset = point_offset + point_index * 16
                lon, lat = struct.unpack("<2d", shp[offset:offset + 16])
                if previous is not None:
                    x0, y0 = to_pixel(previous[0], previous[1])
                    x1, y1 = to_pixel(lon, lat)
                    draw_segment(mask, x0, y0, x1, y1, radius)
                previous = (lon, lat)
    for _ in range(1):
        p = np.pad(mask, 1, mode="edge")
        mask = (
            p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:] | p[1:-1, 1:-1]
        )
    mask &= land
    np.save(RIVER_MASK_CACHE, mask)
    print(f"HydroRIVERS mask built in {time.time() - start:.1f}s")
    return mask


def dilate(mask, rounds=1):
    out = mask.copy()
    for _ in range(rounds):
        p = np.pad(out, 1, mode="edge")
        out = (
            p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
            | p[:-2, :-2] | p[:-2, 2:] | p[2:, :-2] | p[2:, 2:] | p[1:-1, 1:-1]
        )
    return out


def carve_rivers(height, rivers):
    carved = height.copy()
    lowland = rivers & (height <= SEA_LEVEL + 14)
    foothill = rivers & (height > SEA_LEVEL + 14) & (height <= SEA_LEVEL + 34)

    outer_banks = dilate(lowland, rounds=5) & ~dilate(lowland, rounds=3)
    mid_banks = dilate(lowland, rounds=3) & ~dilate(lowland, rounds=1)
    inner_banks = dilate(lowland, rounds=1) & ~lowland

    carved[outer_banks] = np.minimum(carved[outer_banks], SEA_LEVEL + 5)
    carved[mid_banks] = np.minimum(carved[mid_banks], SEA_LEVEL + 3)
    carved[inner_banks] = np.minimum(carved[inner_banks], SEA_LEVEL + 1)
    carved[lowland] = np.minimum(carved[lowland], SEA_LEVEL - 5)

    # Higher terrain cannot use sea-level water without creating artificial
    # chasms. Keep these as shallow valleys for now; real elevated rivers need
    # a later block-placement pass instead of heightmap-only carving.
    carved[foothill] = np.maximum(SEA_LEVEL + 6, carved[foothill] - 2)
    return carved, lowland


def carve_lakes(height, lakes):
    carved = height.copy()
    lowland = lakes & (height <= SEA_LEVEL + 24)
    highland = lakes & ~lowland

    outer_banks = dilate(lowland, rounds=5) & ~dilate(lowland, rounds=2)
    inner_banks = dilate(lowland, rounds=2) & ~lowland
    carved[outer_banks] = np.minimum(carved[outer_banks], SEA_LEVEL + 4)
    carved[inner_banks] = np.minimum(carved[inner_banks], SEA_LEVEL + 1)
    carved[lowland] = np.minimum(carved[lowland], SEA_LEVEL - 4)

    # High-elevation lakes need a chunk post-process for true local water
    # levels. Keep only a shallow local depression in the heightmap pass.
    carved[highland] = np.maximum(carved[highland] - 2, SEA_LEVEL + 6)
    return carved, lowland, highland


def ocean_temperature(lat, lon, height):
    depth = np.maximum(0, SEA_LEVEL - height)
    base = 30.0 - 0.58 * (lat - 18.0)
    south_china_sea = 2.0 * sigmoid((25.0 - lat) / 2.7) * sigmoid((lon - 106.0) / 3.0)
    kuroshio = 2.2 * sigmoid((lon - 120.0) / 1.8) * sigmoid((34.0 - lat) / 4.0)
    east_china_shelf = 0.9 * sigmoid((lon - 118.0) / 2.0) * sigmoid((lat - 24.0) / 2.5) * sigmoid((35.0 - lat) / 2.5)
    yellow_bohai_cold = -3.2 * sigmoid((lat - 35.0) / 1.8) * sigmoid((123.5 - lon) / 2.0)
    japan_sea_cold = -2.0 * sigmoid((lat - 39.0) / 2.0) * sigmoid((lon - 126.0) / 2.5)
    deep_moderation = -0.8 * sigmoid((depth - 28.0) / 9.0)
    texture = 0.8 * np.sin((lon - 102.0) * 0.65 + lat * 0.28) + 0.4 * np.sin((lon + lat) * 1.7)
    return base + south_china_sea + kuroshio + east_china_shelf + yellow_bohai_cold + japan_sea_cold + deep_moderation + texture


def surface_biomes(height, elev, land, rivers=None, lakes=None, highland_lakes=None):
    lat = lat_grid()
    lon = lon_grid()
    sl = slope(height)
    coast = coast_mask(land)
    texture = climate_texture(lon, lat)
    keys = np.full(height.shape, "ocean", dtype=object)

    # Coarse bioclimatic model for China. It is intentionally continuous first,
    # then corrected with a few well-known geomorphic regions.
    temp = (
        31.0
        - (lat - 18.0) * 0.72
        - np.clip(elev, 0, 6500) * 0.0048
        - sigmoid((lat - 44.0) / 1.8) * 3.0
        + texture * 0.45
    )
    monsoon = sigmoid((lon - 101.5) / 5.0) * sigmoid((33.5 - lat) / 4.8)
    pacific = sigmoid((lon - 112.0) / 4.2)
    south_sea = sigmoid((27.5 - lat) / 2.8)
    continental_dry = sigmoid((104.0 - lon) / 4.8) * sigmoid((lat - 31.0) / 3.2)
    plateau_dry = sigmoid((elev - 2600.0) / 700.0) * sigmoid((105.0 - lon) / 5.0)
    moisture = (
        0.35
        + 1.10 * monsoon
        + 0.55 * pacific
        + 0.55 * south_sea
        - 0.95 * continental_dry
        - 0.60 * plateau_dry
        - 0.20 * sigmoid((elev - 4200.0) / 600.0)
        + texture * 0.08
    )

    arid = (
        1.25 * sigmoid((105.0 - lon) / 4.8)
        + 0.75 * sigmoid((lat - 34.0) / 3.5)
        + 0.35 * sigmoid((elev - 900.0) / 900.0)
        - 0.85 * sigmoid((lon - 112.0) / 4.0)
        - 0.55 * sigmoid((28.0 - lat) / 2.4)
    )
    cold = (
        0.95 * sigmoid((lat - 40.0) / 2.4)
        + 0.65 * sigmoid((elev - 1600.0) / 850.0)
        + 0.55 * sigmoid((height - 145.0) / 16.0)
    )
    humid_warm = (
        1.05 * sigmoid((112.0 - np.abs(lon - 112.0)) / 5.0)
        + 0.95 * sigmoid((30.0 - lat) / 3.0)
        + 0.40 * sigmoid((lon - 104.0) / 4.0)
        - 0.95 * sigmoid((arid - 1.0) / 0.25)
    )

    water = ~land
    sea_temp = ocean_temperature(lat, lon, height)
    deep_water = water & (height < 34)
    shallow_water = water & (height >= 34) & (height < SEA_LEVEL)
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

    northeast_factor = sigmoid((lat - 43.2) / 1.4) * sigmoid((lon - 116.0) / 2.0)
    northeast = land & (northeast_factor > (0.42 + texture * 0.04))
    north = land & ((lat + texture * 0.7) >= 39)
    northwest_arid = land & (moisture < 0.20) & (lat > 31) & (lon < 112) & (elev < 2800)
    tibet = land & (elev > 2800) & (lon < 104) & (lat > 26) & (lat < 39)
    north_china_w = oval(lon, lat, 116.8, 37.0, 4.6, 4.2)
    northeast_w = np.maximum(
        oval(lon, lat, 124.5, 45.7, 4.8, 3.2),
        oval(lon, lat, 128.0, 47.0, 3.5, 2.2),
    )
    yangtze_w = np.maximum(
        oval(lon, lat, 120.8, 31.2, 2.9, 1.8),
        oval(lon, lat, 112.8, 30.0, 3.6, 2.0),
    )
    sichuan_w = oval(lon, lat, 106.0, 30.5, 2.7, 1.7)
    pearl_w = oval(lon, lat, 113.5, 22.8, 1.7, 1.0)
    plain_weight = np.maximum.reduce([north_china_w, northeast_w, yangtze_w, sichuan_w, pearl_w])
    qinghai_gansu = land & in_box(lon, lat, 90, 35, 106, 40)
    north_china_plain = land & in_box(lon, lat, 110.0, 32.0, 123.0, 40.8) & (height < 106) & (sl < 4.2)
    northeast_plain = land & (height < 108) & (sl < 3.6) & ((northeast_w + texture * 0.025) > 0.14)
    yangtze_plain = land & in_box(lon, lat, 108.0, 28.0, 123.0, 33.6) & (height < 104) & (sl < 3.8)
    yangtze_delta = land & in_box(lon, lat, 116.0, 29.0, 123.0, 33.5) & (height < 98) & (sl < 3.4)
    pearl_delta = land & in_box(lon, lat, 111.0, 21.5, 115.5, 24.2) & (height < 100) & (sl < 3.5)
    sichuan_basin = land & in_box(lon, lat, 102.5, 28.0, 109.0, 32.5) & (height < 108) & (sl < 3.8)
    south_china = land & (moisture > 1.05) & (temp > 11) & (lon > 100)
    southwest_mountains = land & in_box(lon, lat, 97, 22, 110, 32)
    hainan = land & in_box(lon, lat, 108, 18, 112, 21)
    yunnan_tropical = land & in_box(lon, lat, 97, 21, 102.5, 24)
    loess_plateau = land & in_box(lon, lat, 104, 34, 112, 40) & (height >= 90) & (height < 135)

    low_flat = land & (height < 92) & (sl < 3.0)
    broad_plain = land & (height < 102) & (sl < 3.8)
    foothill = land & (height >= 90) & (height < 122) & (sl < 3.6)
    hill = land & ((height >= 96) | (sl >= 3.0))

    keys[low_flat] = "plains"
    named_plain = north_china_plain | northeast_plain | yangtze_plain | sichuan_basin | pearl_delta
    plain_core = broad_plain & (((plain_weight + texture * 0.035) > 0.14) | named_plain)
    keys[north_china_plain & plain_core] = "plains"
    keys[northeast_plain & plain_core] = "plains"
    keys[northeast_plain & plain_core & (temp < 1.0)] = "snowy_plains"
    keys[yangtze_plain & plain_core] = "sunflower_plains"
    keys[yangtze_delta & plain_core] = "plains"
    keys[pearl_delta & plain_core] = "sunflower_plains"
    keys[sichuan_basin] = "sunflower_plains"
    keys[foothill & (moisture >= 0.45) & ~northwest_arid] = "meadow"
    keys[foothill & (moisture < 0.45) & ~tibet] = "savanna"

    keys[north & hill & (height < 115) & (temp < 6) & (plain_weight < 0.18)] = "taiga"
    keys[northeast & hill & (height < 125) & (temp < 3) & (northeast_w < 0.18)] = "snowy_taiga"
    keys[low_flat & ((lat + texture * 0.7) > 43.0) & (temp < 1.0)] = "snowy_plains"
    keys[north & (height >= 115) & (height < 145) & (temp < 4)] = "old_growth_spruce_taiga"

    keys[south_china & broad_plain] = "sunflower_plains"
    keys[south_china & hill & (height < 128) & (sl >= 3.4)] = "forest"
    keys[south_china & hill & (height >= 112) & (height < 145) & (sl >= 4.2)] = "dark_forest"
    keys[southwest_mountains & hill & (height >= 100) & (height < 145)] = "birch_forest"
    keys[(hainan | yunnan_tropical) & (height < 95)] = "sparse_jungle"
    keys[hainan & (height >= 95) & (height < 125)] = "bamboo_jungle"

    keys[northwest_arid & (height < 102) & (moisture < 0.0)] = "desert"
    keys[northwest_arid & (height < 128) & (moisture >= 0.0)] = "savanna"
    keys[loess_plateau & (moisture < 0.55) & (sl < 5.5)] = "savanna"
    keys[loess_plateau & (moisture < 0.35) & (sl >= 5.5)] = "wooded_badlands"

    keys[tibet & (temp > -2) & (height < 145) & (sl < 4.0)] = "meadow"
    keys[tibet & (temp <= -2) & (height < 145) & (sl < 4.0)] = "snowy_plains"
    keys[tibet & (height >= 135) & (height < 165)] = "grove"
    keys[tibet & ((height >= 165) | (temp < -6))] = "snowy_slopes"
    keys[tibet & (sl >= 6.5) & (height >= 145)] = "stony_peaks"
    keys[tibet & (height >= 196)] = "jagged_peaks"

    protected_plains = north_china_plain | northeast_plain | yangtze_plain | sichuan_basin | pearl_delta
    keys[land & (moisture > 0.65) & (height >= 120) & (height < 150) & ~tibet & ~protected_plains] = "windswept_forest"
    keys[land & (moisture <= 0.65) & (height >= 128) & (height < 160) & ~tibet] = "meadow"
    keys[land & (height >= 150) & ~tibet & (temp > 1)] = "grove"
    snowline = 166.0 + texture * 5.0
    northern_snowline = 145.0 + texture * 4.0
    keys[land & (((height >= snowline) & (temp <= 3)) | ((height >= northern_snowline) & (lat > 38)))] = "snowy_slopes"
    keys[land & (height >= 185) & (sl >= 4.2)] = "stony_peaks"
    keys[land & (height >= 206)] = "jagged_peaks"

    keys[land & coast & (height <= SEA_LEVEL + 4)] = "beach"
    keys[land & coast & (sl >= 5)] = "stony_shore"
    keys[north_china_plain & plain_core] = "plains"
    keys[northeast_plain & plain_core] = "plains"
    keys[northeast_plain & plain_core & (temp < 1.0)] = "snowy_plains"
    keys[yangtze_delta & plain_core] = "plains"
    keys[yangtze_plain & plain_core & ~yangtze_delta] = "sunflower_plains"
    keys[pearl_delta & plain_core] = "sunflower_plains"
    if lakes is not None:
        keys[lakes] = "river"
        keys[lakes & (temp < -2.0)] = "frozen_river"
    if rivers is not None:
        keys[rivers] = "river"
        keys[rivers & (temp < -2.0)] = "frozen_river"
    return keys


def write_preview(height, surface):
    preview = np.zeros((SIZE_Y, SIZE_X, 3), dtype=np.uint8)
    for key, color in SURFACE_COLORS.items():
        rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        preview[surface == key] = rgb
    shade = np.clip((height.astype(np.float32) - 45) / 170.0, 0.35, 1.15)[..., None]
    preview = np.clip(preview.astype(np.float32) * shade, 0, 255).astype(np.uint8)
    Image.fromarray(preview, "RGB").resize((1200, int(1200 * SIZE_Y / SIZE_X)), Image.Resampling.LANCZOS).save(OUT_ROOT / "china_preview.png")


def build_pack():
    if PACK.exists():
        shutil.rmtree(PACK)
    for rel in [
        "data/china/novoatlas/heightmap",
        "data/china/novoatlas/biome_map",
        "data/minecraft/dimension",
    ]:
        (PACK / rel).mkdir(parents=True, exist_ok=True)

    elev = sample_elevation()
    height, land = minecraft_height(elev)
    lakes = lake_mask() & land
    height, water_lakes, highland_lakes = carve_lakes(height, lakes)
    rivers = river_mask(land & ~water_lakes)
    height, water_rivers = carve_rivers(height, rivers)
    surface_land = land & ~water_lakes
    surface = surface_biomes(height, elev, surface_land, water_rivers, water_lakes, highland_lakes)

    Image.fromarray(height, "L").save(PACK / "data/china/novoatlas/heightmap/china.png")
    color_image(surface, SURFACE_COLORS).save(PACK / "data/china/novoatlas/biome_map/china.png")

    write_json(PACK / "pack.mcmeta", {
        "pack": {"pack_format": 48, "description": "NovoAtlas China Overworld v12: real lakes and ocean climate pass"}
    })
    write_json(PACK / "data/china/novoatlas/map_info/china.json", {
        "starting_y": 0,
        "horizontal_scale": 1,
        "vertical_scale": 1,
        "height_map": "china:china",
        "surface_biomes": {
            "map": "china:china",
            "biomes": [
                {"biome": SURFACE_BIOMES[key], "color": SURFACE_COLORS[key]}
                for key in SURFACE_COLORS
            ]
        }
    })
    write_json(PACK / "data/minecraft/dimension/overworld.json", {
        "type": "minecraft:overworld",
        "generator": {
            "type": "novoatlas:image_map",
            "map_info": "china:china",
            "settings": "minecraft:overworld",
            "underground_density_function": "novoatlas:caves",
            "biome_source": {
                "type": "novoatlas:color_map",
                "map_info": "china:china",
                "default_biome": "minecraft:the_void"
            }
        }
    })
    write_preview(height, surface)
    write_json(OUT_ROOT / "manifest.json", {
        "dimension": "minecraft:overworld",
        "bbox": BBOX,
        "size_blocks": {"x": SIZE_X, "z": SIZE_Y},
        "reference": "Uses the same degrees-per-block scale as Japan 2048 test pack.",
        "notes": [
            "Main overworld replacement pack.",
            "Real elevation from AWS Terrarium tiles.",
            "Surface biomes are rule-based from elevation, latitude, slope, coast proximity, and broad China climate regions.",
            "River corridors are rasterized from HydroRIVERS v1.0 Asia vectors, filtered by flow and upstream drainage area.",
            "Lowland rivers are widened and stepped for navigation; foothill rivers are shallow valleys to avoid sea-level chasms.",
            "Lowland lakes are rasterized from Natural Earth 10m lake polygons; highland lakes need a later local-water post-process.",
            "Ocean biomes use a regional sea-temperature approximation with vanilla warm/lukewarm/ocean/cold/frozen classes plus deep variants.",
            "No custom cave biomes, no extra ore features, and no mineral enrichment in this version."
        ],
        "teleport_examples": [
            "/tp @s 0 160 0",
            "/tp @s 2400 150 1200",
            "/tp @s -2600 170 -1200"
        ]
    })


if __name__ == "__main__":
    build_pack()
