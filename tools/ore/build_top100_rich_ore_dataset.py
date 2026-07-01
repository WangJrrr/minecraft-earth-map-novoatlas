import ast
import csv
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
INPUT_ROOT = Path(os.environ.get("NOVOATLAS_MINERAL_INPUT_ROOT", PROJECT_ROOT / "inputs" / "mineral_data"))
MRDS_CSV = INPUT_ROOT / "mrds_csv" / "mrds.csv"
LEGACY_RICH_ORE_SCRIPT = PROJECT_ROOT / "tools" / "pipeline" / "make_world_v1_400_global_rich_ore_pack.py"

DATA_DIR = OUT_ROOT / "rich_ore_top100"
CSV_OUT = DATA_DIR / "global_top100_rich_ore_candidates.csv"
JSON_OUT = DATA_DIR / "global_top100_rich_ore_candidates.json"
SUMMARY_OUT = DATA_DIR / "global_top100_rich_ore_summary.json"
COVERAGE_PREVIEW = DATA_DIR / "global_top100_rich_ore_coverage_preview.png"
POINT_PREVIEW = DATA_DIR / "global_top100_rich_ore_points_preview.png"

SCALE_DENOMINATOR = float(os.environ.get("NOVOATLAS_SCALE_DENOMINATOR", "200"))
SCALE_FACTOR = 200.0 / SCALE_DENOMINATOR
WIDTH = round(163840 * SCALE_FACTOR)
HEIGHT = round(92160 * SCALE_FACTOR)
PREVIEW_W = 4096
PREVIEW_H = 2304
PACIFIC_WEST = -31.5
MAX_PER_ORE = 100

TIERS = {
    5: {"label": "world_top", "max_rank": 10, "density": 1.00, "radius": 1.90},
    4: {"label": "major", "max_rank": 25, "density": 0.50, "radius": 1.65},
    3: {"label": "large", "max_rank": 50, "density": 0.33, "radius": 1.45},
    2: {"label": "regional", "max_rank": 75, "density": 0.12, "radius": 1.28},
    1: {"label": "local", "max_rank": 100, "density": 0.05, "radius": 1.14},
}

ORE_COLORS = {
    "coal": (30, 30, 30),
    "iron": (184, 111, 69),
    "copper": (212, 122, 74),
    "gold": (240, 201, 68),
    "zinc": (120, 175, 200),
    "diamond": (68, 212, 212),
    "redstone": (200, 40, 40),
    "lapis": (49, 90, 200),
    "emerald": (48, 180, 92),
}

ORE_MATCHES = {
    "coal": {
        "commodities": {"coal", "lignite", "bituminous", "subbituminous", "anthracite"},
        "name_keywords": {"coal", "lignite", "anthracite", "bituminous", "subbituminous"},
    },
    "iron": {"commodities": {"iron"}, "name_keywords": {"iron", "hematite", "magnetite"}},
    "copper": {"commodities": {"copper"}, "name_keywords": {"copper", "porphyry"}},
    "gold": {"commodities": {"gold"}, "name_keywords": {"gold"}},
    "zinc": {"commodities": {"zinc"}, "name_keywords": {"zinc"}},
    "diamond": {"commodities": {"diamond"}, "name_keywords": {"diamond", "kimberlite"}},
    # Redstone is a game mapping. Uranium/vanadium/thorium districts produce a believable
    # "red industrial/radioactive mineral" layer without changing vanilla ore identities.
    "redstone": {
        "commodities": {"uranium", "vanadium", "thorium", "rare earths", "rare earth elements"},
        "name_keywords": {"uranium", "vanadium", "thorium", "monazite"},
    },
    "lapis": {
        "commodities": {"lapis lazuli", "lazurite"},
        "name_keywords": {"lapis", "lazurite", "badakhshan"},
    },
    # Jade is intentionally mapped to Minecraft emerald for playability. Emerald/jade
    # deposits are later given smaller radii and gentler ore counts than metal districts.
    "emerald": {"commodities": {"emerald", "jade", "jadeite", "nephrite"}, "name_keywords": {"emerald", "jade", "jadeite", "nephrite"}},
}

SUPPLEMENTAL_COAL_MAJOR_MINES = [
    ("North Antelope Rochelle Coal Mine", -105.283333, 43.566667, "United States", 210, "https://www.gem.wiki/Top_ten_largest_coal_mines_in_the_world"),
    ("Gevra Coal Mine", 82.545748, 22.336312, "India", 190, "https://www.gem.wiki/Top_ten_largest_coal_mines_in_the_world"),
    ("KPC Operation Coal Mine", 117.599032, 0.823979, "Indonesia", 190, "https://www.gem.wiki/Top_ten_largest_coal_mines_in_the_world"),
    ("Borneo Indobara Coal Mine", 115.559833, -3.700239, "Indonesia", 180, "https://www.gem.wiki/Top_ten_largest_coal_mines_in_the_world"),
    ("Grootegeluk Coal Mine", 27.566687, -23.657141, "South Africa", 180, "https://www.gem.wiki/Top_ten_largest_coal_mines_in_the_world"),
    ("Bara Tabang Coal Mine", 116.126335, 0.550906, "Indonesia", 170, "https://www.gem.wiki/Top_ten_largest_coal_mines_in_the_world"),
    ("Kusmunda Coal Mine", 82.666666, 22.332635, "India", 170, "https://www.gem.wiki/Top_ten_largest_coal_mines_in_the_world"),
    ("PTBA Coal Mines", 103.768323, -3.739981, "Indonesia", 165, "https://www.gem.wiki/Top_ten_largest_coal_mines_in_the_world"),
    ("Tutupan Coal Mine", 115.527798, -2.204484, "Indonesia", 165, "https://www.gem.wiki/Top_ten_largest_coal_mines_in_the_world"),
    ("Zhundong South Surface Mine", 89.233076, 44.818916, "China", 160, "https://www.gem.wiki/Top_ten_largest_coal_mines_in_the_world"),
    ("Black Thunder Coal Mine", -105.234, 43.705, "United States", 150, "https://www.gem.wiki/Global_Coal_Mine_Tracker"),
    ("Carmichael Coal Mine", 146.43, -22.13, "Australia", 135, "https://www.gem.wiki/Global_Coal_Mine_Tracker"),
    ("Peak Downs Coal Mine", 148.18, -22.24, "Australia", 130, "https://www.gem.wiki/Global_Coal_Mine_Tracker"),
    ("Goonyella Riverside Coal Mine", 148.13, -21.78, "Australia", 130, "https://www.gem.wiki/Global_Coal_Mine_Tracker"),
    ("Hail Creek Coal Mine", 148.36, -21.47, "Australia", 120, "https://www.gem.wiki/Global_Coal_Mine_Tracker"),
    ("Mount Arthur Coal Mine", 150.89, -32.29, "Australia", 120, "https://www.gem.wiki/Global_Coal_Mine_Tracker"),
    ("Cerrejon Coal Mine", -72.62, 11.08, "Colombia", 130, "https://www.gem.wiki/Global_Coal_Mine_Tracker"),
    ("Tavan Tolgoi Coal Mine", 105.52, 43.65, "Mongolia", 125, "https://www.gem.wiki/Global_Coal_Mine_Tracker"),
    ("Ekibastuz Coal Basin", 75.35, 51.62, "Kazakhstan", 125, "https://www.gem.wiki/Global_Coal_Mine_Tracker"),
    ("Kuzbass Kemerovo Coal Field", 86.08, 54.76, "Russia", 130, "https://www.gem.wiki/Global_Coal_Mine_Tracker"),
]

PROD_SCORE = {"L": 600, "M": 450, "S": 300, "Y": 250, "N": 20, "U": 0, "": 0}
DEV_SCORE = {
    "Producer": 300,
    "Past Producer": 220,
    "Prospect": 120,
    "Plant": 80,
    "Occurrence": 10,
    "Unknown": 0,
}
QUALITY_SCORE = {"A": 250, "B": 160, "C": 80, "D": 20, "E": 0, "": 0}


def clean_commodity(value):
    parts = []
    for item in (value or "").replace(";", ",").split(","):
        item = item.split("-")[0].strip().lower()
        if item:
            parts.append(item)
    return parts


def rank_to_tier(rank):
    for tier in sorted(TIERS, reverse=True):
        if rank <= TIERS[tier]["max_rank"]:
            return tier
    return 0


def lonlat_to_pixel(lon, lat, width=WIDTH, height=HEIGHT):
    x = ((lon - PACIFIC_WEST) % 360.0) / 360.0 * width
    y = (90.0 - lat) / 180.0 * height
    return x, y


def lonlat_to_world(lon, lat):
    x, z = lonlat_to_pixel(lon, lat)
    return int(round(x - WIDTH / 2)), int(round(z - HEIGHT / 2))


def radius_km_to_preview_pixels(radius_km, lat):
    km_per_lon_degree = 111.32 * max(0.25, math.cos(math.radians(lat)))
    px_per_lon_degree = PREVIEW_W / 360.0
    px_per_lat_degree = PREVIEW_H / 180.0
    rx = radius_km / km_per_lon_degree * px_per_lon_degree
    ry = radius_km / 110.57 * px_per_lat_degree
    return max(1.5, rx), max(1.5, ry)


def load_legacy_zones():
    if not LEGACY_RICH_ORE_SCRIPT.exists():
        return {}
    module = ast.parse(LEGACY_RICH_ORE_SCRIPT.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "ZONES" for t in node.targets):
            return ast.literal_eval(node.value)
    return {}


def candidate_from_legacy(ore, rank, zone):
    name, lon, lat, radius_km = zone
    x, z = lonlat_to_world(lon, lat)
    return {
        "ore": ore,
        "name": name,
        "longitude": float(lon),
        "latitude": float(lat),
        "country": "",
        "region": "",
        "rank_hint": rank,
        "score": 5000 - rank,
        "core_radius_km": float(radius_km),
        "source": "legacy_curated_major_district",
        "source_url": "",
        "mrds_dep_id": "",
        "mrds_quality": "",
        "mrds_prod_size": "",
        "mrds_dev_status": "",
        "world_x": x,
        "world_z": z,
    }


def candidate_from_supplemental_coal(rank, zone):
    name, lon, lat, country, radius_km, url = zone
    x, z = lonlat_to_world(lon, lat)
    return {
        "ore": "coal",
        "name": name,
        "longitude": float(lon),
        "latitude": float(lat),
        "country": country,
        "region": "",
        "rank_hint": rank,
        "score": 6200 - rank,
        "core_radius_km": float(radius_km),
        "source": "GEM_major_coal_mine_anchor",
        "source_url": url,
        "mrds_dep_id": "",
        "mrds_quality": "",
        "mrds_prod_size": "",
        "mrds_dev_status": "",
        "world_x": x,
        "world_z": z,
    }


def row_matches_ore(row, ore):
    match = ORE_MATCHES[ore]
    commodities = []
    for field in ("commod1", "commod2", "commod3"):
        commodities.extend(clean_commodity(row.get(field, "")))
    commodity_hit = any(c in match["commodities"] for c in commodities)
    text = " ".join(
        [
            row.get("site_name", ""),
            row.get("dep_type", ""),
            row.get("ore", ""),
            row.get("gangue", ""),
            row.get("model", ""),
            row.get("names", ""),
        ]
    ).lower()
    keyword_hit = any(k in text for k in match["name_keywords"])
    return commodity_hit or keyword_hit


def candidate_from_mrds(row, ore):
    try:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    score = (
        PROD_SCORE.get(row.get("prod_size", "").strip(), 0)
        + DEV_SCORE.get(row.get("dev_stat", "").strip(), 0)
        + QUALITY_SCORE.get(row.get("score", "").strip(), 0)
    )
    if clean_commodity(row.get("commod1", "")):
        primary = clean_commodity(row.get("commod1", ""))
        if any(c in ORE_MATCHES[ore]["commodities"] for c in primary):
            score += 120
    if row.get("country", "") and row.get("country", "") != "United States":
        score += 25
    prod_size = row.get("prod_size", "").strip()
    radius = {"L": 150, "M": 115, "S": 80, "Y": 75, "N": 45, "U": 40, "": 38}.get(prod_size, 40)
    if ore == "emerald":
        radius = max(28, round(radius * 0.62))
    x, z = lonlat_to_world(lon, lat)
    return {
        "ore": ore,
        "name": row.get("site_name", "").strip() or row.get("dep_id", ""),
        "longitude": lon,
        "latitude": lat,
        "country": row.get("country", "").strip(),
        "region": row.get("region", "").strip(),
        "rank_hint": "",
        "score": score,
        "core_radius_km": radius,
        "source": "USGS_MRDS",
        "source_url": row.get("url", ""),
        "mrds_dep_id": row.get("dep_id", ""),
        "mrds_quality": row.get("score", "").strip(),
        "mrds_prod_size": prod_size,
        "mrds_dev_status": row.get("dev_stat", "").strip(),
        "world_x": x,
        "world_z": z,
    }


def distance_km(a, b):
    lat1 = math.radians(a["latitude"])
    lat2 = math.radians(b["latitude"])
    dlat = lat2 - lat1
    dlon = math.radians(b["longitude"] - a["longitude"])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2.0 * math.asin(min(1.0, math.sqrt(h)))


def select_top100(candidates):
    selected = []
    country_counts = {}
    for cand in sorted(candidates, key=lambda x: x["score"], reverse=True):
        if any(distance_km(cand, old) < 22 for old in selected):
            continue
        country = cand.get("country") or "unknown"
        cap = 45 if cand["ore"] == "coal" else (28 if country == "United States" else 22)
        if cand["source"] == "USGS_MRDS" and country_counts.get(country, 0) >= cap:
            continue
        selected.append(cand)
        country_counts[country] = country_counts.get(country, 0) + 1
        if len(selected) >= MAX_PER_ORE:
            break
    for rank, cand in enumerate(selected, start=1):
        tier = rank_to_tier(rank)
        cand["rank"] = rank
        cand["tier"] = tier
        cand["tier_label"] = TIERS[tier]["label"]
        cand["outer_radius_km"] = round(cand["core_radius_km"] * TIERS[tier]["radius"], 1)
    return selected


def build_candidates():
    legacy = load_legacy_zones()
    by_ore = {ore: [] for ore in ORE_MATCHES}
    for ore, zones in legacy.items():
        if ore in by_ore:
            for rank, zone in enumerate(zones[:MAX_PER_ORE], start=1):
                by_ore[ore].append(candidate_from_legacy(ore, rank, zone))
    for rank, zone in enumerate(SUPPLEMENTAL_COAL_MAJOR_MINES, start=1):
        by_ore["coal"].append(candidate_from_supplemental_coal(rank, zone))

    with MRDS_CSV.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for ore in by_ore:
                if row_matches_ore(row, ore):
                    cand = candidate_from_mrds(row, ore)
                    if cand is not None:
                        by_ore[ore].append(cand)

    return {ore: select_top100(cands) for ore, cands in by_ore.items()}


def draw_ellipse(draw, lon, lat, radius_km, fill):
    x, y = lonlat_to_pixel(lon, lat, PREVIEW_W, PREVIEW_H)
    rx, ry = radius_km_to_preview_pixels(radius_km, lat)
    draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=fill)


def make_previews(selected_by_ore):
    tier_map = Image.new("L", (PREVIEW_W, PREVIEW_H), 0)
    tier_draw = ImageDraw.Draw(tier_map)
    points = Image.new("RGB", (PREVIEW_W, PREVIEW_H), (16, 31, 54))
    point_draw = ImageDraw.Draw(points, "RGBA")

    tier_colors = {
        0: (16, 31, 54),
        1: (57, 116, 76),
        2: (83, 155, 86),
        3: (210, 187, 76),
        4: (229, 126, 57),
        5: (212, 48, 48),
    }
    for tier in range(1, 6):
        layer = Image.new("L", (PREVIEW_W, PREVIEW_H), 0)
        draw = ImageDraw.Draw(layer)
        for deposits in selected_by_ore.values():
            for dep in deposits:
                if dep["tier"] == tier:
                    draw_ellipse(draw, dep["longitude"], dep["latitude"], dep["outer_radius_km"], tier)
        current = np.asarray(tier_map, dtype=np.uint8)
        incoming = np.asarray(layer, dtype=np.uint8)
        tier_map = Image.fromarray(np.maximum(current, incoming).astype(np.uint8), "L")
        tier_draw = ImageDraw.Draw(tier_map)

    tier_arr = np.asarray(tier_map, dtype=np.uint8)
    coverage = {}
    total = tier_arr.size
    rgb = np.zeros((PREVIEW_H, PREVIEW_W, 3), dtype=np.uint8)
    for tier, color in tier_colors.items():
        mask = tier_arr == tier
        rgb[mask] = color
        if tier:
            coverage[str(tier)] = {
                "label": TIERS[tier]["label"],
                "pixels": int(mask.sum()),
                "percent_of_map": round(float(mask.sum() * 100.0 / total), 4),
            }
    Image.fromarray(rgb, "RGB").save(COVERAGE_PREVIEW, optimize=True)

    for ore, deposits in selected_by_ore.items():
        color = (*ORE_COLORS[ore], 220)
        for dep in deposits:
            x, y = lonlat_to_pixel(dep["longitude"], dep["latitude"], PREVIEW_W, PREVIEW_H)
            size = 7 if dep["tier"] >= 4 else 5
            point_draw.polygon([(x, y - size), (x - size, y + size), (x + size, y + size)], fill=color)
    points.save(POINT_PREVIEW, optimize=True)
    return coverage


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    selected_by_ore = build_candidates()
    records = [dep for ore in ORE_MATCHES for dep in selected_by_ore[ore]]
    fieldnames = [
        "ore",
        "rank",
        "tier",
        "tier_label",
        "name",
        "longitude",
        "latitude",
        "world_x",
        "world_z",
        "core_radius_km",
        "outer_radius_km",
        "country",
        "region",
        "source",
        "source_url",
        "score",
        "mrds_dep_id",
        "mrds_quality",
        "mrds_prod_size",
        "mrds_dev_status",
    ]
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    JSON_OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    coverage = make_previews(selected_by_ore)
    counts = {ore: len(deps) for ore, deps in selected_by_ore.items()}
    source_counts = {
        ore: {
            source: sum(1 for dep in deps if dep["source"] == source)
            for source in sorted({dep["source"] for dep in deps})
        }
        for ore, deps in selected_by_ore.items()
    }
    summary = {
        "csv": str(CSV_OUT),
        "json": str(JSON_OUT),
        "coverage_preview": str(COVERAGE_PREVIEW),
        "point_preview": str(POINT_PREVIEW),
        "map_grid": {
            "projection": "Pacific-centered equirectangular for Minecraft grid",
            "west_seam_longitude": PACIFIC_WEST,
            "width_blocks": WIDTH,
            "height_blocks": HEIGHT,
        },
        "counts_by_ore": counts,
        "source_counts_by_ore": source_counts,
        "tier_coverage_percent_of_minecraft_map": coverage,
        "notes": [
            "MRDS is used for real global point coordinates and commodity/status/quality scoring.",
            "Legacy curated major districts are retained as high-confidence anchors and supplements, especially for coal, lapis, emerald, and game-mapped redstone.",
            "Coverage percentages are estimated on the Minecraft rectangular map area, not spherical Earth surface area.",
            "Redstone is a game mapping based mainly on uranium/vanadium/thorium/REE-style mineral districts.",
        ],
    }
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
