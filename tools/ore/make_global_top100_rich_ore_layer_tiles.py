import colorsys
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
SCALE_DENOMINATOR = float(os.environ.get("NOVOATLAS_SCALE_DENOMINATOR", "200"))
SCALE_LABEL = f"{SCALE_DENOMINATOR:g}".replace(".", "p")
DATA_ID = f"global_1_{SCALE_LABEL}_pacific_tiled_v1"
DATA_DIR = OUT_ROOT / "rich_ore_top100"
DEPOSITS_JSON = DATA_DIR / "global_top100_rich_ore_candidates.json"
LAYER_ROOT = DATA_DIR / f"generated_layer_1_{SCALE_LABEL}"
ORE_TILE_ROOT = LAYER_ROOT / "data/world/novoatlas" / DATA_ID / "ore"
WORLDGEN_ROOT = LAYER_ROOT / "data/world/worldgen"
SUMMARY = DATA_DIR / f"global_top100_rich_ore_layer_1_{SCALE_LABEL}_summary.json"
PREVIEW = DATA_DIR / f"global_top100_rich_ore_layer_1_{SCALE_LABEL}_preview.png"

SCALE_FACTOR = 200.0 / SCALE_DENOMINATOR
WIDTH = round(163840 * SCALE_FACTOR)
HEIGHT = round(92160 * SCALE_FACTOR)
TILE = 2048
TILES_X = math.ceil(WIDTH / TILE)
TILES_Z = math.ceil(HEIGHT / TILE)
PACIFIC_WEST = -31.5
TIER_BASE = 6
STABLE_MAX_COMPOSITE_BIOMES = 64
ORE_LAYER_MAX_Y = 48
RICH_ORE_RADIUS_MULTIPLIER = 1.33

TIERS = {
    5: {"label": "world_top", "max_rank": 10, "density": 2.00, "radius": 1.90, "core_fraction": 0.02},
    4: {"label": "major", "max_rank": 25, "density": 1.00, "radius": 1.65, "core_fraction": 0.01},
    3: {"label": "large", "max_rank": 50, "density": 0.66, "radius": 1.45, "core_fraction": 0.00},
    2: {"label": "regional", "max_rank": 75, "density": 0.24, "radius": 1.28, "core_fraction": 0.00},
    1: {"label": "local", "max_rank": 100, "density": 0.10, "radius": 1.14, "core_fraction": 0.00},
}

ORES = {
    "coal": {
        "ore": "minecraft:coal_ore",
        "deepslate_ore": "minecraft:deepslate_coal_ore",
        "core": "minecraft:coal_block",
        "vein_size": 36,
        "count": 28,
        "min_y": 0,
        "max_y": 128,
    },
    "iron": {
        "ore": "minecraft:iron_ore",
        "deepslate_ore": "minecraft:deepslate_iron_ore",
        "core": "minecraft:iron_block",
        "vein_size": 34,
        "count": 24,
        "min_y": -32,
        "max_y": 96,
    },
    "copper": {
        "ore": "minecraft:copper_ore",
        "deepslate_ore": "minecraft:deepslate_copper_ore",
        "core": "minecraft:copper_block",
        "vein_size": 34,
        "count": 16,
        "min_y": -24,
        "max_y": 112,
    },
    "gold": {
        "ore": "minecraft:gold_ore",
        "deepslate_ore": "minecraft:deepslate_gold_ore",
        "core": "minecraft:gold_block",
        "vein_size": 26,
        "count": 16,
        "min_y": -56,
        "max_y": 48,
    },
    "zinc": {
        "ore": "create:zinc_ore",
        "deepslate_ore": "create:deepslate_zinc_ore",
        "core": "create:zinc_block",
        "vein_size": 32,
        "count": 18,
        "min_y": -48,
        "max_y": 90,
    },
    "diamond": {
        "ore": "minecraft:diamond_ore",
        "deepslate_ore": "minecraft:deepslate_diamond_ore",
        "core": "minecraft:diamond_block",
        "vein_size": 12,
        "count": 10,
        "min_y": -64,
        "max_y": 16,
    },
    "redstone": {
        "ore": "minecraft:redstone_ore",
        "deepslate_ore": "minecraft:deepslate_redstone_ore",
        "core": "minecraft:redstone_block",
        "vein_size": 18,
        "count": 10,
        "min_y": -64,
        "max_y": 16,
    },
    "lapis": {
        "ore": "minecraft:lapis_ore",
        "deepslate_ore": "minecraft:deepslate_lapis_ore",
        "core": "minecraft:lapis_block",
        "vein_size": 12,
        "count": 7,
        "min_y": -64,
        "max_y": 32,
    },
    "emerald": {
        "ore": "minecraft:emerald_ore",
        "deepslate_ore": "minecraft:deepslate_emerald_ore",
        "core": "minecraft:emerald_block",
        "vein_size": 4,
        "count": 3,
        "min_y": -16,
        "max_y": 96,
    },
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lonlat_to_pixel(lon, lat, width=WIDTH, height=HEIGHT):
    x = ((lon - PACIFIC_WEST) % 360.0) / 360.0 * width
    y = (90.0 - lat) / 180.0 * height
    return x, y


def radius_km_to_pixels(radius_km, lat, width=WIDTH, height=HEIGHT):
    km_per_lon_degree = 111.32 * max(0.25, math.cos(math.radians(lat)))
    px_per_lon_degree = width / 360.0
    px_per_lat_degree = height / 180.0
    return (
        max(4, radius_km / km_per_lon_degree * px_per_lon_degree),
        max(4, radius_km / 110.57 * px_per_lat_degree),
    )


def combo_color(index):
    hue = (index * 0.618033988749895 + 0.08) % 1.0
    saturation = 0.58 + 0.14 * ((index % 3) / 2)
    value = 0.70 + 0.22 * (((index * 7) % 5) / 4)
    rgb = colorsys.hsv_to_rgb(hue, saturation, value)
    return tuple(round(channel * 255) for channel in rgb)


def rgb_hex(rgb):
    return "#" + "".join(f"{channel:02X}" for channel in rgb)


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


def choose_allowed_combos(sample_codes):
    codes, counts = np.unique(sample_codes, return_counts=True)
    raw = [int(code) for code in codes if int(code)]
    count_by_code = {int(code): int(count) for code, count in zip(codes, counts)}
    single = {single_code_for_combo(code) for code in raw}
    single.discard(0)
    multi = [code for code in raw if len(decode_combo(code)) > 1]

    def score(code):
        combo = decode_combo(code)
        tiers = [tier for _, tier in combo]
        return (max(tiers), sum(tiers), len(combo), count_by_code.get(code, 0))

    keep_multi = sorted(multi, key=score, reverse=True)[: max(0, STABLE_MAX_COMPOSITE_BIOMES - len(single))]
    return set(single) | set(keep_multi)


def collapse_code(code, allowed):
    code = int(code)
    if code == 0 or code in allowed:
        return code
    return single_code_for_combo(code)


def tier_count(ore_config, tier):
    base = ore_config["count"]
    if ore_config is ORES["emerald"]:
        base = min(base, 3)
    return max(1, round(base * TIERS[tier]["density"]))


def ore_targets(stone_state, deepslate_state):
    return [
        {
            "target": {"predicate_type": "minecraft:tag_match", "tag": "minecraft:stone_ore_replaceables"},
            "state": {"Name": stone_state},
        },
        {
            "target": {"predicate_type": "minecraft:tag_match", "tag": "minecraft:deepslate_ore_replaceables"},
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
    fraction = TIERS[tier]["core_fraction"]
    count = round(tier_count(config, tier) * config["vein_size"] * fraction)
    return {
        "feature": f"world:{ore}_rich_core",
        "placement": [
            {"type": "minecraft:count", "count": max(0, count)},
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
        features[6].append(f"world:{ore}_t{tier}_rich_vein")
        if tier >= 4:
            features[6].append(f"world:{ore}_t{tier}_rich_core")
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


def deposits_to_shapes(deposits, width=WIDTH, height=HEIGHT):
    shapes = []
    for dep in deposits:
        ore_index = list(ORES).index(dep["ore"])
        tier = int(dep["tier"])
        lon = float(dep["longitude"])
        lat = float(dep["latitude"])
        core_radius = float(dep["core_radius_km"]) * RICH_ORE_RADIUS_MULTIPLIER
        outer_radius = float(dep["outer_radius_km"]) * RICH_ORE_RADIUS_MULTIPLIER
        if dep["ore"] == "emerald":
            core_radius *= 0.72
            outer_radius *= 0.72
        x, y = lonlat_to_pixel(lon, lat, width, height)
        middle_radius = core_radius + (outer_radius - core_radius) * 0.55
        zone_specs = [
            (max(1, tier - 2), outer_radius),
            (max(1, tier - 1), middle_radius),
            (tier, core_radius),
        ]
        for paint_tier, radius in zone_specs:
            rx, ry = radius_km_to_pixels(radius, lat, width, height)
            shapes.append(
                {
                    **dep,
                    "tier": paint_tier,
                    "source_tier": tier,
                    "code": paint_tier * (TIER_BASE ** ore_index),
                    "x": x,
                    "y": y,
                    "rx": rx,
                    "ry": ry,
                }
            )
    return shapes


def draw_shapes_to_code_array(width, height, shapes, scale_x=1.0, scale_y=1.0, offset_x=0.0, offset_y=0.0):
    code_arr = np.zeros((height, width), dtype=np.uint32)
    for shape in sorted(shapes, key=lambda s: int(s["tier"])):
        mask = Image.new("1", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        x = (shape["x"] - offset_x) * scale_x
        y = (shape["y"] - offset_y) * scale_y
        rx = shape["rx"] * scale_x
        ry = shape["ry"] * scale_y
        draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=1)
        mask_arr = np.asarray(mask, dtype=bool)
        old_tier = (code_arr // (TIER_BASE ** list(ORES).index(shape["ore"]))) % TIER_BASE
        code_arr[mask_arr & (old_tier < int(shape["tier"]))] += (
            (int(shape["tier"]) - old_tier[mask_arr & (old_tier < int(shape["tier"]))])
            * (TIER_BASE ** list(ORES).index(shape["ore"]))
        )
    return code_arr


def build_allowed_palette(shapes):
    sample_w, sample_h = 4096, 2304
    sample_codes = draw_shapes_to_code_array(
        sample_w,
        sample_h,
        shapes,
        scale_x=sample_w / WIDTH,
        scale_y=sample_h / HEIGHT,
    )
    return choose_allowed_combos(sample_codes)


def write_worldgen(unique_codes, colors):
    for ore, config in ORES.items():
        write_json(
            WORLDGEN_ROOT / f"configured_feature/{ore}_rich_vein.json",
            configured_ore(config["vein_size"], config["ore"], config["deepslate_ore"]),
        )
        write_json(
            WORLDGEN_ROOT / f"configured_feature/{ore}_rich_core.json",
            configured_ore(1, config["core"], config["core"]),
        )
        for tier in TIERS:
            write_json(WORLDGEN_ROOT / f"placed_feature/{ore}_t{tier}_rich_vein.json", placed_vein(ore, config, tier))
            write_json(WORLDGEN_ROOT / f"placed_feature/{ore}_t{tier}_rich_core.json", placed_core(ore, config, tier))
    for code in unique_codes:
        write_json(WORLDGEN_ROOT / f"biome/ore_combo_{code}.json", cave_biome(decode_combo(code)))
    write_json(
        LAYER_ROOT / "data/minecraft/tags/worldgen/biome/is_overworld.json",
        {"replace": False, "values": [f"world:ore_combo_{code}" for code in unique_codes]},
    )

    map_info_patch = {
        "cave_biomes": {
            "layers": [
                {
                    "y_range": {"max": ORE_LAYER_MAX_Y},
                    "biomes": {
                        "map": {
                            "tile_size": TILE,
                            "tiles": f"world:novoatlas/{DATA_ID}/ore/{{tx}}_{{tz}}.png",
                            "width": WIDTH,
                            "height": HEIGHT,
                        },
                        "biomes": [
                            {"biome": "novoatlas:surface_biome", "color": "#FFFFFF"},
                            *[
                                {"biome": f"world:ore_combo_{code}", "color": rgb_hex(colors[code])}
                                for code in unique_codes
                            ],
                        ],
                    },
                }
            ]
        }
    }
    write_json(DATA_DIR / "global_top100_rich_ore_map_info_patch.json", map_info_patch)


def main():
    deposits = json.loads(DEPOSITS_JSON.read_text(encoding="utf-8"))
    shapes = deposits_to_shapes(deposits)
    allowed = build_allowed_palette(shapes)
    colors = {code: combo_color(i) for i, code in enumerate(sorted(allowed), start=1)}

    if ORE_TILE_ROOT.exists():
        for old in ORE_TILE_ROOT.glob("*.png"):
            old.unlink()
    ORE_TILE_ROOT.mkdir(parents=True, exist_ok=True)

    unique_codes = set()
    coverage_pixels_by_tier = {str(tier): 0 for tier in TIERS}
    preview = Image.new("RGB", (4096, 2304), (255, 255, 255))
    preview_scale_x = 4096 / WIDTH
    preview_scale_y = 2304 / HEIGHT

    for tz in range(TILES_Z):
        for tx in range(TILES_X):
            left = tx * TILE
            top = tz * TILE
            relevant = [
                s
                for s in shapes
                if s["x"] + s["rx"] >= left
                and s["x"] - s["rx"] < left + TILE
                and s["y"] + s["ry"] >= top
                and s["y"] - s["ry"] < top + TILE
            ]
            if relevant:
                codes = draw_shapes_to_code_array(TILE, TILE, relevant, offset_x=left, offset_y=top)
                vectorized = np.vectorize(lambda c: collapse_code(c, allowed), otypes=[np.uint32])
                codes = vectorized(codes)
            else:
                codes = np.zeros((TILE, TILE), dtype=np.uint32)

            tile_rgb = np.full((TILE, TILE, 3), 255, dtype=np.uint8)
            for code in sorted(int(c) for c in np.unique(codes) if int(c)):
                unique_codes.add(code)
                if code not in colors:
                    colors[code] = combo_color(len(colors) + 1)
                tile_rgb[codes == code] = colors[code]
            for tier in TIERS:
                max_tier = np.zeros_like(codes, dtype=np.uint8)
                remaining = codes.copy()
                for _ore in ORES:
                    max_tier = np.maximum(max_tier, (remaining % TIER_BASE).astype(np.uint8))
                    remaining //= TIER_BASE
                coverage_pixels_by_tier[str(tier)] += int((max_tier == tier).sum())

            Image.fromarray(tile_rgb, "RGB").save(ORE_TILE_ROOT / f"{tx}_{tz}.png", optimize=True)
            small = Image.fromarray(tile_rgb, "RGB").resize(
                (round(TILE * preview_scale_x), round(TILE * preview_scale_y)),
                Image.Resampling.NEAREST,
            )
            preview.paste(small, (round(left * preview_scale_x), round(top * preview_scale_y)))

        print(f"row {tz + 1}/{TILES_Z} complete")

    # Last partial row
    last_tz = TILES_Z
    real_h = HEIGHT - last_tz * TILE
    if real_h > 0:
        for tx in range(TILES_X):
            left = tx * TILE
            top = last_tz * TILE
            relevant = [
                s for s in shapes
                if s["x"] + s["rx"] >= left and s["x"] - s["rx"] < left + TILE
                and s["y"] + s["ry"] >= top and s["y"] - s["ry"] < top + real_h
            ]
            if relevant:
                codes = draw_shapes_to_code_array(TILE, real_h, relevant, offset_x=left, offset_y=top)
                vectorized = np.vectorize(lambda c: collapse_code(c, allowed), otypes=[np.uint32])
                codes = vectorized(codes)
            else:
                codes = np.zeros((real_h, TILE), dtype=np.uint32)
            tile_rgb = np.full((real_h, TILE, 3), 255, dtype=np.uint8)
            for code in sorted(int(c) for c in np.unique(codes) if int(c)):
                unique_codes.add(code)
                if code not in colors:
                    colors[code] = combo_color(len(colors) + 1)
                tile_rgb[codes == code] = colors[code]
            padded = np.full((TILE, TILE, 3), 255, dtype=np.uint8)
            padded[:real_h, :, :] = tile_rgb
            Image.fromarray(padded, "RGB").save(ORE_TILE_ROOT / f"{tx}_{last_tz}.png", optimize=True)
            small = Image.fromarray(padded, "RGB").resize(
                (round(TILE * preview_scale_x), round(TILE * preview_scale_y)),
                Image.Resampling.NEAREST,
            )
            preview.paste(small, (round(left * preview_scale_x), round(top * preview_scale_y)))
        print(f"row {last_tz + 1}/{last_tz + 1} complete (partial)")

    unique_codes = sorted(unique_codes)
    write_worldgen(unique_codes, colors)
    preview.save(PREVIEW, optimize=True)

    total = WIDTH * HEIGHT
    coverage = {
        tier: {
            "label": TIERS[int(tier)]["label"],
            "pixels": pixels,
            "percent_of_map": round(pixels * 100.0 / total, 4),
        }
        for tier, pixels in coverage_pixels_by_tier.items()
        if pixels
    }
    summary = {
        "layer_root": str(LAYER_ROOT),
        "ore_tile_root": str(ORE_TILE_ROOT),
        "preview": str(PREVIEW),
        "deposits_json": str(DEPOSITS_JSON),
        "tile_size": TILE,
        "scale_denominator": SCALE_DENOMINATOR,
        "dataset_id": DATA_ID,
        "tiles_x": TILES_X,
        "tiles_z": TILES_Z,
        "tile_count": TILES_X * TILES_Z,
        "unique_composite_biomes": len(unique_codes),
        "ore_layer_y_range": {"max": ORE_LAYER_MAX_Y},
        "rich_ore_radius_multiplier": RICH_ORE_RADIUS_MULTIPLIER,
        "tier_core_block_fraction": {
            "5": "2%",
            "4": "1%",
            "1-3": "0%",
        },
        "coverage_percent_of_minecraft_map": coverage,
        "notes": [
            "This is an independent ore-layer payload. It does not modify the current terrain assembly pack.",
            "Emerald includes jade/jadeite/nephrite mapping and is intentionally tuned weaker than metal-rich districts.",
            "Only tier 5 and tier 4 rich ore biomes include mineral block core features.",
        ],
    }
    write_json(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
