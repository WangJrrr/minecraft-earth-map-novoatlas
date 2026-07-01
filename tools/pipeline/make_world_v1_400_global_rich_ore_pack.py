import colorsys
import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT_ROOT = REPO / "outputs" / "world_novoatlas_overworld"
SOURCE_PACK = OUT_ROOT / "NovoAtlas_World_Overworld_1block400m_v1_hscale10"
PACK = OUT_ROOT / "NovoAtlas_World_Overworld_1block400m_v1_hscale10_GlobalRichOre_Stable64"

FULL_SIZE_X = 81920
FULL_SIZE_Y = 46080
PREVIEW_DIVISOR = 10
SIZE_X = FULL_SIZE_X // PREVIEW_DIVISOR
SIZE_Y = FULL_SIZE_Y // PREVIEW_DIVISOR
BBOX = {"west": -180.0, "south": -90.0, "east": 180.0, "north": 90.0}
MAX_DEPOSITS_PER_ORE = 100
TIER_BASE = 6
ORE_LAYER_MAX_Y = 48
STABLE_MAX_COMPOSITE_BIOMES = 64

# Rank bands are intentionally based on extra ore generation, not total world
# ore count. Tier 5 is the current richest setting, while low ranks only add a
# mild bonus over vanilla/Create generation.
TIERS = {
    5: {"label": "world_top", "max_rank": 10, "density": 1.00, "radius": 1.90},
    4: {"label": "major", "max_rank": 25, "density": 0.50, "radius": 1.65},
    3: {"label": "large", "max_rank": 50, "density": 0.33, "radius": 1.45},
    2: {"label": "regional", "max_rank": 75, "density": 0.12, "radius": 1.28},
    1: {"label": "local", "max_rank": 100, "density": 0.05, "radius": 1.14},
}

ORES = {
    "coal": {
        "color": "#202020",
        "ore": "minecraft:coal_ore",
        "deepslate_ore": "minecraft:deepslate_coal_ore",
        "core": "minecraft:coal_block",
        "vein_size": 36,
        "count": 28,
        "min_y": 0,
        "max_y": 128,
        "core_fraction": 0.01,
    },
    "iron": {
        "color": "#B86F45",
        "ore": "minecraft:iron_ore",
        "deepslate_ore": "minecraft:deepslate_iron_ore",
        "core": "minecraft:iron_block",
        "vein_size": 34,
        "count": 24,
        "min_y": -32,
        "max_y": 96,
        "core_fraction": 0.01,
    },
    "copper": {
        "color": "#D47A4A",
        "ore": "minecraft:copper_ore",
        "deepslate_ore": "minecraft:deepslate_copper_ore",
        "core": "minecraft:copper_block",
        # Copper is already common in vanilla, so the richest district is tuned
        # to feel rich without flooding every cave wall.
        "vein_size": 34,
        "count": 16,
        "min_y": -24,
        "max_y": 112,
        "core_fraction": 0.01,
    },
    "gold": {
        "color": "#F0C944",
        "ore": "minecraft:gold_ore",
        "deepslate_ore": "minecraft:deepslate_gold_ore",
        "core": "minecraft:gold_block",
        "vein_size": 26,
        "count": 16,
        "min_y": -56,
        "max_y": 48,
        "core_fraction": 0.01,
    },
    "zinc": {
        "color": "#78AFC8",
        "ore": "create:zinc_ore",
        "deepslate_ore": "create:deepslate_zinc_ore",
        "core": "create:zinc_block",
        # Zinc is also a common Create ore. Keep the top tier at roughly the
        # requested seven-times-feel instead of copying the earlier jackpot.
        "vein_size": 32,
        "count": 18,
        "min_y": -48,
        "max_y": 90,
        "core_fraction": 0.01,
    },
    "diamond": {
        "color": "#44D4D4",
        "ore": "minecraft:diamond_ore",
        "deepslate_ore": "minecraft:deepslate_diamond_ore",
        "core": "minecraft:diamond_block",
        "vein_size": 9,
        "count": 6,
        "min_y": -64,
        "max_y": 16,
        "core_fraction": 0.01,
    },
    "redstone": {
        "color": "#C82828",
        "ore": "minecraft:redstone_ore",
        "deepslate_ore": "minecraft:deepslate_redstone_ore",
        "core": "minecraft:redstone_block",
        "vein_size": 18,
        "count": 10,
        "min_y": -64,
        "max_y": 16,
        "core_fraction": 0.01,
    },
    "lapis": {
        "color": "#315AC8",
        "ore": "minecraft:lapis_ore",
        "deepslate_ore": "minecraft:deepslate_lapis_ore",
        "core": "minecraft:lapis_block",
        "vein_size": 12,
        "count": 7,
        "min_y": -64,
        "max_y": 32,
        "core_fraction": 0.01,
    },
    "emerald": {
        "color": "#30B45C",
        "ore": "minecraft:emerald_ore",
        "deepslate_ore": "minecraft:deepslate_emerald_ore",
        "core": "minecraft:emerald_block",
        "vein_size": 5,
        "count": 4,
        "min_y": -16,
        "max_y": 128,
        "core_fraction": 0.01,
    },
}

# Representative global mineral districts. Each ore is independently capped at
# MAX_DEPOSITS_PER_ORE; order is used as the rank for tier decay. The list favors
# recognizable server-play regions and permits overlap, so South Africa,
# Australia, Canada, China, and the Andes can hold several rich minerals.
ZONES = {
    "coal": [
        ("Powder River Basin", -106.0, 44.5, 260),
        ("Appalachian Basin", -81.5, 38.5, 230),
        ("Illinois Basin", -88.5, 38.0, 180),
        ("Bowen Basin", 148.0, -22.5, 230),
        ("Hunter Valley", 151.0, -32.5, 130),
        ("Kuznetsk Basin", 86.0, 54.0, 240),
        ("Tunguska Basin", 100.0, 64.0, 420),
        ("Pechora Basin", 58.0, 66.0, 260),
        ("Donets Basin", 38.5, 48.0, 180),
        ("Upper Silesia", 19.0, 50.0, 120),
        ("Ruhr", 7.0, 51.4, 100),
        ("Ordos Basin", 109.5, 39.3, 260),
        ("Datong Shanxi", 113.3, 40.1, 160),
        ("Junggar Basin", 86.0, 44.5, 230),
        ("Tarim Basin", 82.5, 40.5, 240),
        ("Tavan Tolgoi", 105.5, 43.6, 140),
        ("Jharia", 86.4, 23.8, 120),
        ("Singrauli", 82.7, 24.1, 130),
        ("Korba", 82.7, 22.4, 130),
        ("Kalimantan", 115.0, -1.5, 260),
        ("South Sumatra", 103.5, -3.5, 170),
        ("Mpumalanga Witbank", 29.2, -26.0, 170),
        ("Waterberg", 27.8, -23.8, 150),
        ("Cerrejon", -72.6, 11.0, 120),
        ("Tete", 33.5, -16.0, 150),
        ("Karaganda", 73.0, 49.8, 180),
        ("Ekibastuz", 75.5, 51.7, 140),
    ],
    "iron": [
        ("Pilbara Hamersley", 118.0, -22.0, 300),
        ("Carajas", -50.2, -6.0, 170),
        ("Quadrilatero Ferrifero", -43.7, -20.2, 150),
        ("Labrador Trough", -67.0, 53.0, 260),
        ("Mesabi Range", -92.5, 47.5, 130),
        ("Kursk Magnetic Anomaly", 37.5, 51.0, 210),
        ("Kryvyi Rih", 33.4, 47.9, 140),
        ("Kiruna", 20.3, 67.9, 120),
        ("Anshan Benxi", 123.2, 41.2, 140),
        ("Bayan Obo", 109.9, 41.8, 110),
        ("Panzhihua", 101.7, 26.6, 110),
        ("Odisha Keonjhar", 85.5, 21.8, 160),
        ("Bailadila", 81.2, 18.7, 120),
        ("Singhbhum", 85.5, 22.3, 140),
        ("Sishen", 22.9, -27.8, 140),
        ("Simandou", -8.8, 8.6, 150),
        ("Nimba", -8.6, 7.6, 120),
        ("Mauritania Zouerat", -12.5, 22.7, 180),
        ("Marampa", -12.2, 8.7, 100),
        ("El Mutun", -59.2, -19.2, 160),
        ("Yilgarn Iron Province", 119.5, -28.5, 220),
        ("Magnetite Range", 116.2, -28.0, 150),
    ],
    "copper": [
        ("Escondida", -69.1, -24.3, 120),
        ("Chuquicamata", -68.9, -22.3, 120),
        ("Collahuasi", -68.7, -20.9, 120),
        ("El Teniente", -70.4, -34.1, 110),
        ("Cerro Verde", -71.6, -16.5, 120),
        ("Las Bambas", -72.3, -14.1, 110),
        ("Antamina", -77.1, -9.5, 120),
        ("Morenci", -109.3, 33.1, 120),
        ("Bingham Canyon", -112.1, 40.5, 90),
        ("Resolution Arizona", -111.1, 33.3, 90),
        ("Grasberg", 137.1, -4.1, 120),
        ("Olympic Dam", 136.9, -30.4, 170),
        ("Mount Isa", 139.5, -20.7, 150),
        ("Kamoa Kakula", 25.2, -10.8, 150),
        ("Tenke Fungurume", 26.2, -10.6, 140),
        ("Katanga Copperbelt", 27.5, -11.5, 220),
        ("Kansanshi", 26.4, -12.1, 130),
        ("Sentinel Zambia", 25.7, -12.3, 120),
        ("Oyu Tolgoi", 106.9, 43.0, 130),
        ("Erdenet", 104.0, 49.0, 120),
        ("Dexing", 117.6, 29.0, 110),
        ("Yulong Tibet", 97.7, 31.5, 120),
        ("Tongling Daye Belt", 116.5, 30.4, 150),
        ("Udokan", 116.6, 56.3, 130),
        ("Norilsk", 88.2, 69.3, 150),
        ("Lubin KGHM", 16.1, 51.4, 110),
        ("Bor Timok", 22.1, 44.1, 100),
        ("Aitik", 20.9, 67.1, 90),
    ],
    "gold": [
        ("Witwatersrand", 27.8, -26.2, 210),
        ("Carlin Trend", -116.0, 40.8, 140),
        ("Cortez Trend", -116.7, 40.2, 110),
        ("Nevada Gold Mines", -116.3, 40.5, 170),
        ("Kalgoorlie", 121.5, -30.7, 150),
        ("Yilgarn Goldfields", 121.0, -29.0, 230),
        ("Muruntau", 64.6, 41.5, 130),
        ("Olimpiada", 94.7, 59.7, 130),
        ("Natalka", 148.3, 61.6, 120),
        ("Sukhoi Log", 116.5, 58.5, 130),
        ("Grasberg", 137.1, -4.1, 110),
        ("Lihir", 152.6, -3.1, 100),
        ("Porgera", 143.1, -5.5, 100),
        ("Cadia", 148.9, -33.5, 100),
        ("Boddington", 116.5, -32.8, 110),
        ("Jiaodong", 120.4, 37.3, 150),
        ("Zijinshan", 116.4, 25.2, 100),
        ("Tianshan Gold Belt", 84.5, 43.0, 170),
        ("Yanacocha", -78.5, -6.9, 120),
        ("Pueblo Viejo", -70.2, 19.0, 100),
        ("Fruta del Norte", -78.5, -3.8, 90),
        ("Tarkwa", -2.0, 5.3, 130),
        ("Obuasi Ashanti", -1.7, 6.2, 130),
        ("Kibali", 29.6, 3.1, 120),
        ("Lake Victoria Goldfields", 32.5, -3.0, 180),
        ("Red Lake", -93.8, 51.0, 120),
        ("Abitibi", -79.0, 48.3, 180),
        ("Val d'Or", -77.8, 48.1, 110),
    ],
    "zinc": [
        ("Red Dog", -162.9, 68.1, 130),
        ("Mount Isa", 139.5, -20.7, 150),
        ("McArthur River", 136.1, -16.4, 140),
        ("Century", 138.6, -18.7, 120),
        ("Broken Hill", 141.5, -31.9, 120),
        ("Rampura Agucha", 74.7, 25.8, 110),
        ("Sindesar Khurd", 74.2, 24.9, 90),
        ("Dugald River", 140.1, -20.2, 100),
        ("Antamina", -77.1, -9.5, 120),
        ("San Cristobal Bolivia", -66.1, -21.1, 120),
        ("Penasquito", -101.7, 24.6, 130),
        ("Fresnillo", -102.9, 23.2, 100),
        ("Tara Navan", -6.7, 53.6, 80),
        ("Gamsberg", 18.9, -29.2, 100),
        ("Kipushi", 27.3, -11.8, 100),
        ("Rosh Pinah", 16.8, -27.9, 100),
        ("Norilsk", 88.2, 69.3, 120),
        ("Fankou", 113.7, 25.1, 110),
        ("Huize", 103.3, 26.4, 120),
        ("Lanping", 99.4, 26.5, 120),
        ("Shuikoushan", 112.6, 26.7, 100),
        ("Xitieshan", 95.6, 37.0, 120),
        ("Zawar", 73.7, 24.3, 90),
    ],
    "diamond": [
        ("Jwaneng", 24.7, -24.6, 100),
        ("Orapa", 25.4, -21.3, 110),
        ("Karowe", 25.4, -21.5, 90),
        ("Venetia", 29.3, -22.4, 100),
        ("Cullinan", 28.5, -25.7, 80),
        ("Kimberley", 24.8, -28.7, 90),
        ("Letseng", 28.9, -29.0, 80),
        ("Catoca", 20.3, -9.4, 110),
        ("Luele", 20.4, -9.8, 100),
        ("Mbuji Mayi", 23.6, -6.1, 130),
        ("Kasai", 21.5, -5.5, 170),
        ("Marange", 32.4, -20.4, 110),
        ("Argyle", 128.4, -16.7, 90),
        ("Diavik", -110.3, 64.5, 90),
        ("Ekati", -110.6, 64.7, 90),
        ("Gahcho Kue", -109.2, 63.5, 90),
        ("Mirny", 113.9, 62.5, 110),
        ("Udachny", 112.4, 66.4, 100),
        ("Aikhal", 111.5, 65.9, 90),
        ("Lomonosov", 41.0, 64.7, 90),
        ("Grib Arkhangelsk", 41.5, 65.0, 90),
    ],
    "redstone": [
        ("Athabasca Basin", -105.0, 58.0, 250),
        ("Kazakhstan Uranium Belt", 67.5, 44.0, 300),
        ("Olympic Dam", 136.9, -30.4, 170),
        ("Bayan Obo REE", 109.9, 41.8, 120),
        ("Mountain Pass", -115.5, 35.5, 90),
        ("Mount Weld", 122.0, -28.9, 100),
        ("Kvanefjeld", -45.9, 60.9, 90),
        ("Cigar Lake", -104.5, 58.1, 90),
        ("McArthur River Canada", -105.0, 57.8, 90),
        ("Ranger Jabiru", 132.9, -12.7, 100),
        ("Rossing", 15.0, -22.5, 110),
        ("Husab", 15.1, -22.6, 110),
        ("Arlit Niger", 7.4, 18.7, 120),
        ("Tummalapalle", 78.3, 14.3, 90),
        ("Korea Rare Metals", 128.0, 37.0, 80),
    ],
    "lapis": [
        ("Badakhshan Sar-e-Sang", 70.8, 36.2, 110),
        ("Andean Lazurite Chile", -69.6, -30.2, 100),
        ("Lake Baikal Lazurite", 108.0, 52.0, 100),
        ("Pamirs Blue Minerals", 72.0, 38.5, 100),
        ("Hindu Kush", 70.0, 35.5, 120),
        ("Ovalle Chile", -71.2, -30.6, 90),
        ("Colorado Blue Minerals", -106.0, 39.0, 80),
        ("Myanmar Mogok", 96.5, 22.9, 80),
        ("Pakistan Himalaya", 74.5, 35.5, 90),
        ("Tajikistan Pamir", 72.5, 38.0, 90),
    ],
    "emerald": [
        ("Muzo Colombia", -74.1, 5.5, 90),
        ("Chivor Colombia", -73.4, 4.9, 90),
        ("Coscuez Colombia", -74.0, 5.6, 80),
        ("Kagem Zambia", 28.0, -13.0, 100),
        ("Itabira Nova Era", -43.0, -19.7, 100),
        ("Bahia Emerald Belt", -41.0, -12.5, 110),
        ("Santa Terezinha", -49.6, -14.4, 90),
        ("Swat Pakistan", 72.3, 35.2, 90),
        ("Panjshir Afghanistan", 69.8, 35.4, 90),
        ("Ural Emerald Mines", 61.5, 57.0, 90),
        ("Shakiso Ethiopia", 38.9, 5.8, 90),
        ("Mananjary Madagascar", 47.9, -21.2, 90),
        ("Sandawana Zimbabwe", 29.9, -20.9, 90),
        ("Habachtal Austria", 12.3, 47.2, 70),
    ],
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lonlat_to_pixel(lon, lat):
    x = (lon - BBOX["west"]) / (BBOX["east"] - BBOX["west"]) * (SIZE_X - 1)
    y = (BBOX["north"] - lat) / (BBOX["north"] - BBOX["south"]) * (SIZE_Y - 1)
    return x, y


def lonlat_to_world(lon, lat):
    x, z = lonlat_to_pixel(lon, lat)
    full_x = (x - SIZE_X / 2) * PREVIEW_DIVISOR
    full_z = (z - SIZE_Y / 2) * PREVIEW_DIVISOR
    return int(round(full_x)), int(round(full_z))


def radius_km_to_pixels(radius_km, lat):
    km_per_lon_degree = 111.32 * max(0.25, math.cos(math.radians(lat)))
    px_per_lon_degree = SIZE_X / (BBOX["east"] - BBOX["west"])
    px_per_lat_degree = SIZE_Y / (BBOX["north"] - BBOX["south"])
    rx = radius_km / km_per_lon_degree * px_per_lon_degree
    ry = radius_km / 110.57 * px_per_lat_degree
    return max(4, rx), max(4, ry)


def draw_irregular_zone(draw, lon, lat, radius_km, color, seed):
    x, y = lonlat_to_pixel(lon, lat)
    rx, ry = radius_km_to_pixels(radius_km, lat)
    lobes = [
        (0.0, 0.0, 1.0, 0.70),
        (-0.38, 0.12, 0.66, 0.46),
        (0.34, -0.18, 0.72, 0.42),
        (0.08, 0.36, 0.48, 0.36),
        (-0.05, -0.38, 0.44, 0.30),
    ]
    wobble = ((seed * 37) % 17 - 8) / 40.0
    for ox, oy, sx, sy in lobes:
        cx = x + (ox + wobble * oy) * rx
        cy = y + (oy - wobble * ox) * ry
        half_x = rx * sx
        half_y = ry * sy
        draw.ellipse((cx - half_x, cy - half_y, cx + half_x, cy + half_y), fill=color)


def rank_to_tier(rank):
    for tier in sorted(TIERS, reverse=True):
        if rank <= TIERS[tier]["max_rank"]:
            return tier
    return 0


def tier_count(config, tier):
    return max(1, round(config["count"] * TIERS[tier]["density"]))


def decode_combo(code):
    result = []
    remaining = int(code)
    for ore in ORES:
        tier = remaining % TIER_BASE
        remaining //= TIER_BASE
        if tier:
            result.append((ore, tier))
    return result


def single_code_for_combo(code):
    combo = decode_combo(code)
    if not combo:
        return 0
    order = {ore: index for index, ore in enumerate(ORES)}
    ore, tier = max(combo, key=lambda item: (item[1], -order[item[0]]))
    return tier * (TIER_BASE ** order[ore])


def collapse_to_stable_combo_palette(combo_codes):
    codes, counts = np.unique(combo_codes, return_counts=True)
    raw_codes = [int(code) for code in codes if int(code)]
    count_by_code = {int(code): int(count) for code, count in zip(codes, counts)}
    single_codes = {single_code_for_combo(code) for code in raw_codes}
    single_codes.discard(0)
    multi_codes = [code for code in raw_codes if len(decode_combo(code)) > 1]

    def multi_score(code):
        combo = decode_combo(code)
        tiers = [tier for _, tier in combo]
        return (
            max(tiers),
            sum(tiers),
            len(combo),
            count_by_code[code],
        )

    keep_slots = max(0, STABLE_MAX_COMPOSITE_BIOMES - len(single_codes))
    kept_multi = sorted(multi_codes, key=multi_score, reverse=True)[:keep_slots]
    allowed = set(single_codes) | set(kept_multi)

    stable_codes = np.zeros_like(combo_codes, dtype=np.uint32)
    collapsed = []
    for code in raw_codes:
        target = code if code in allowed else single_code_for_combo(code)
        stable_codes[combo_codes == code] = target
        if target != code:
            collapsed.append(
                {
                    "from_code": code,
                    "to_code": int(target),
                    "pixels": count_by_code[code],
                    "from_minerals": [
                        {"ore": ore, "tier": tier, "tier_label": TIERS[tier]["label"]}
                        for ore, tier in decode_combo(code)
                    ],
                    "to_minerals": [
                        {"ore": ore, "tier": tier, "tier_label": TIERS[tier]["label"]}
                        for ore, tier in decode_combo(target)
                    ],
                }
            )
    return stable_codes, sorted(int(code) for code in np.unique(stable_codes) if int(code)), collapsed


def combo_color(index):
    hue = (index * 0.618033988749895 + 0.08) % 1.0
    saturation = 0.58 + 0.14 * ((index % 3) / 2)
    value = 0.70 + 0.22 * (((index * 7) % 5) / 4)
    rgb = colorsys.hsv_to_rgb(hue, saturation, value)
    return tuple(round(channel * 255) for channel in rgb)


def rgb_hex(rgb):
    return "#" + "".join(f"{channel:02X}" for channel in rgb)


def ore_targets(stone_state, deepslate_state):
    return [
        {
            "target": {
                "predicate_type": "minecraft:tag_match",
                "tag": "minecraft:stone_ore_replaceables",
            },
            "state": {"Name": stone_state},
        },
        {
            "target": {
                "predicate_type": "minecraft:tag_match",
                "tag": "minecraft:deepslate_ore_replaceables",
            },
            "state": {"Name": deepslate_state},
        },
    ]


def configured_ore(size, stone_state, deepslate_state):
    return {
        "type": "minecraft:ore",
        "config": {
            "discard_chance_on_air_exposure": 0.0,
            "size": size,
            "targets": ore_targets(stone_state, deepslate_state),
        },
    }


def height_range(min_y, max_y):
    return {
        "type": "minecraft:height_range",
        "height": {
            "type": "minecraft:uniform",
            "min_inclusive": {"absolute": min_y},
            "max_inclusive": {"absolute": max_y},
        },
    }


def placed_vein(ore, config, tier):
    return {
        "feature": f"world:{ore}_rich_vein",
        "placement": [
            {"type": "minecraft:count", "count": tier_count(config, tier)},
            {"type": "minecraft:in_square"},
            height_range(config["min_y"], config["max_y"]),
            {"type": "minecraft:biome"},
        ],
    }


def placed_core(ore, config, tier):
    core_count = max(
        1,
        round(tier_count(config, tier) * config["vein_size"] * config["core_fraction"]),
    )
    return {
        "feature": f"world:{ore}_rich_core",
        "placement": [
            {"type": "minecraft:count", "count": core_count},
            {"type": "minecraft:in_square"},
            height_range(config["min_y"], config["max_y"]),
            {"type": "minecraft:biome"},
        ],
    }


def cave_biome(combo):
    features = [[] for _ in range(11)]
    features[3] = ["minecraft:monster_room", "minecraft:monster_room_deep"]
    features[6] = [
        "minecraft:ore_dirt",
        "minecraft:ore_gravel",
        "minecraft:ore_granite_upper",
        "minecraft:ore_granite_lower",
        "minecraft:ore_diorite_upper",
        "minecraft:ore_diorite_lower",
        "minecraft:ore_andesite_upper",
        "minecraft:ore_andesite_lower",
        "minecraft:ore_tuff",
        "minecraft:ore_coal_upper",
        "minecraft:ore_coal_lower",
        "minecraft:ore_iron_upper",
        "minecraft:ore_iron_middle",
        "minecraft:ore_iron_small",
        "minecraft:ore_gold",
        "minecraft:ore_gold_lower",
        "minecraft:ore_redstone",
        "minecraft:ore_redstone_lower",
        "minecraft:ore_diamond",
        "minecraft:ore_diamond_medium",
        "minecraft:ore_diamond_large",
        "minecraft:ore_diamond_buried",
        "minecraft:ore_lapis",
        "minecraft:ore_lapis_buried",
        "minecraft:ore_copper",
    ]
    for ore, tier in combo:
        features[6].extend(
            [
                f"world:{ore}_t{tier}_rich_vein",
                f"world:{ore}_t{tier}_rich_core",
            ]
        )
    features[9] = ["minecraft:glow_lichen"]
    return {
        "temperature": 0.8,
        "downfall": 0.4,
        "has_precipitation": True,
        "effects": {
            "sky_color": 7907327,
            "fog_color": 12638463,
            "water_color": 4159204,
            "water_fog_color": 329011,
        },
        "spawners": {
            "ambient": [{"type": "minecraft:bat", "maxCount": 8, "minCount": 8, "weight": 10}],
            "axolotls": [],
            "creature": [],
            "misc": [],
            "monster": [
                {"type": "minecraft:spider", "maxCount": 4, "minCount": 4, "weight": 100},
                {"type": "minecraft:zombie", "maxCount": 4, "minCount": 4, "weight": 95},
                {"type": "minecraft:skeleton", "maxCount": 4, "minCount": 4, "weight": 100},
                {"type": "minecraft:creeper", "maxCount": 4, "minCount": 4, "weight": 100},
                {"type": "minecraft:enderman", "maxCount": 1, "minCount": 1, "weight": 10},
                {"type": "minecraft:witch", "maxCount": 1, "minCount": 1, "weight": 5},
            ],
            "underground_water_creature": [
                {"type": "minecraft:glow_squid", "maxCount": 6, "minCount": 4, "weight": 10}
            ],
            "water_ambient": [],
            "water_creature": [],
        },
        "spawn_costs": {},
        "carvers": {},
        "features": features,
    }


def build():
    if not SOURCE_PACK.exists():
        raise FileNotFoundError(f"Missing source pack: {SOURCE_PACK}")
    if PACK.exists():
        shutil.rmtree(PACK)
    shutil.copytree(SOURCE_PACK, PACK)

    ore_masks = {}
    test_coords = []

    for ore_index, (ore, zones) in enumerate(ZONES.items()):
        mask = Image.new("L", (SIZE_X, SIZE_Y), 0)
        draw = ImageDraw.Draw(mask)
        zone_layers = []
        ranked_zones = list(enumerate(zones[:MAX_DEPOSITS_PER_ORE], start=1))
        for rank, (name, lon, lat, radius_km) in ranked_zones:
            core_tier = rank_to_tier(rank)
            if not core_tier:
                continue
            outer_radius = radius_km * TIERS[core_tier]["radius"]
            middle_radius = radius_km * (1.0 + (TIERS[core_tier]["radius"] - 1.0) * 0.55)
            seed = ore_index * 1000 + rank
            zone_layers.extend(
                [
                    (max(1, core_tier - 2), outer_radius, lon, lat, seed),
                    (max(1, core_tier - 1), middle_radius, lon, lat, seed),
                    (core_tier, radius_km, lon, lat, seed),
                ]
            )
            x, z = lonlat_to_world(lon, lat)
            test_coords.append(
                {
                    "ore": ore,
                    "district": name,
                    "rank": rank,
                    "tier": core_tier,
                    "tier_label": TIERS[core_tier]["label"],
                    "core_radius_km": radius_km,
                    "outer_enrichment_radius_km": round(outer_radius, 1),
                    "core_vein_count_per_chunk": tier_count(ORES[ore], core_tier),
                    "longitude": lon,
                    "latitude": lat,
                    "world_x": x,
                    "world_z": z,
                    "spectator_command": f"/tp @s {x} 20 {z}",
                }
            )
        for paint_tier, paint_radius, lon, lat, seed in sorted(zone_layers):
            draw_irregular_zone(draw, lon, lat, paint_radius, paint_tier, seed)
        ore_masks[ore] = np.asarray(mask, dtype=np.uint32)

    combo_codes = np.zeros((SIZE_Y, SIZE_X), dtype=np.uint32)
    for ore_index, ore in enumerate(ORES):
        combo_codes += ore_masks[ore] * (TIER_BASE ** ore_index)

    raw_unique_codes = sorted(int(code) for code in np.unique(combo_codes) if code)
    combo_codes, unique_codes, collapsed_codes = collapse_to_stable_combo_palette(combo_codes)
    combo_colors = {code: combo_color(index) for index, code in enumerate(unique_codes, start=1)}
    cave_rgb = np.full((SIZE_Y, SIZE_X, 3), 255, dtype=np.uint8)
    for code, color in combo_colors.items():
        cave_rgb[combo_codes == code] = color
    cave_map = Image.fromarray(cave_rgb, mode="RGB")

    for point in test_coords:
        px, py = lonlat_to_pixel(point["longitude"], point["latitude"])
        code = int(combo_codes[round(py), round(px)])
        point["combo_code"] = code
        point["minerals_at_center"] = [
            {
                "ore": ore,
                "tier": tier,
                "tier_label": TIERS[tier]["label"],
                "vein_count_per_chunk": tier_count(ORES[ore], tier),
            }
            for ore, tier in decode_combo(code)
        ]

    cave_path = PACK / "data/world/novoatlas/biome_map/ore_zones.png"
    cave_path.parent.mkdir(parents=True, exist_ok=True)
    cave_map.save(cave_path)
    cave_map.resize((2400, int(2400 * SIZE_Y / SIZE_X)), Image.Resampling.NEAREST).save(
        OUT_ROOT / "world_v1_400_global_rich_ore_stable64_zones_preview_2400.png"
    )

    map_info_path = PACK / "data/world/novoatlas/map_info/world.json"
    map_info = json.loads(map_info_path.read_text(encoding="utf-8"))
    map_info["cave_biomes"] = {
        "layers": [
            {
                "y_range": {"max": ORE_LAYER_MAX_Y},
                "biomes": {
                    "map": "world:ore_zones",
                    "biomes": [
                        {"biome": "novoatlas:surface_biome", "color": "#FFFFFF"},
                        *[
                            {
                                "biome": f"world:ore_combo_{code}",
                                "color": rgb_hex(combo_colors[code]),
                            }
                            for code in unique_codes
                        ],
                    ],
                },
            }
        ]
    }
    write_json(map_info_path, map_info)

    for ore, config in ORES.items():
        write_json(
            PACK / f"data/world/worldgen/configured_feature/{ore}_rich_vein.json",
            configured_ore(config["vein_size"], config["ore"], config["deepslate_ore"]),
        )
        write_json(
            PACK / f"data/world/worldgen/configured_feature/{ore}_rich_core.json",
            configured_ore(1, config["core"], config["core"]),
        )
        for tier in TIERS:
            write_json(
                PACK / f"data/world/worldgen/placed_feature/{ore}_t{tier}_rich_vein.json",
                placed_vein(ore, config, tier),
            )
            write_json(
                PACK / f"data/world/worldgen/placed_feature/{ore}_t{tier}_rich_core.json",
                placed_core(ore, config, tier),
            )

    for code in unique_codes:
        write_json(
            PACK / f"data/world/worldgen/biome/ore_combo_{code}.json",
            cave_biome(decode_combo(code)),
        )

    write_json(
        PACK / "data/minecraft/tags/worldgen/biome/is_overworld.json",
        {
            "replace": False,
            "values": [f"world:ore_combo_{code}" for code in unique_codes],
        },
    )

    pack_meta_path = PACK / "pack.mcmeta"
    pack_meta = json.loads(pack_meta_path.read_text(encoding="utf-8"))
    pack_meta["pack"]["description"] = (
        "NovoAtlas World V1 1 block ~= 400m, global surface rules + "
        "tiered top-100 rich ore districts"
    )
    write_json(pack_meta_path, pack_meta)

    deposit_counts = {ore: min(len(ZONES[ore]), MAX_DEPOSITS_PER_ORE) for ore in ORES}
    write_json(OUT_ROOT / "world_v1_400_global_rich_ore_stable64_test_coordinates.json", test_coords)
    write_json(
        OUT_ROOT / "world_v1_400_global_rich_ore_stable64_summary.json",
        {
            "pack": str(PACK),
            "source_pack": str(SOURCE_PACK),
            "max_deposits_per_ore": MAX_DEPOSITS_PER_ORE,
            "deposit_counts": deposit_counts,
            "tier_settings": TIERS,
            "ore_layer_y_range": {"max": ORE_LAYER_MAX_Y},
            "stable_max_composite_biomes": STABLE_MAX_COMPOSITE_BIOMES,
            "raw_unique_composite_biomes_before_stability_collapse": len(raw_unique_codes),
            "unique_composite_biomes": len(unique_codes),
            "collapsed_combo_count": len(collapsed_codes),
            "notes": [
                "Each ore list is capped at the global top 100. Current embedded lists are representative and leave room for replacing with an authoritative top-100 CSV later.",
                "Ore districts can overlap; combo codes preserve every mineral and tier present at the same map pixel.",
                "For packet stability in large modpacks, rare composite ore combinations are collapsed to the strongest mineral unless they are among the most important kept composites.",
                "The ore cave biome layer is capped below y=48 and defines no carvers, lava springs, lava lakes, geodes, or sand/gravel/clay disks.",
            ],
            "collapsed_combinations_sample": collapsed_codes[:200],
            "combinations": [
                {
                    "code": code,
                    "color": rgb_hex(combo_colors[code]),
                    "biome": f"world:ore_combo_{code}",
                    "minerals": [
                        {
                            "ore": ore,
                            "tier": tier,
                            "tier_label": TIERS[tier]["label"],
                            "vein_count_per_chunk": tier_count(ORES[ore], tier),
                        }
                        for ore, tier in decode_combo(code)
                    ],
                }
                for code in unique_codes
            ],
        },
    )
    print(f"Built global rich ore pack: {PACK}")
    print(f"Unique composite ore biomes: {len(unique_codes)}")
    print(f"Deposit counts: {deposit_counts}")


if __name__ == "__main__":
    build()
