# Mineral Data Sources and Current Rules

[English](MINERAL_DATA_AND_RULES.md) | [简体中文](../zh-CN/MINERAL_DATA_AND_RULES_zh-CN.md)

## Data Sources

Top100 rich ores are built from three source groups.

### USGS MRDS

Most global candidate coordinates come from the U.S. Geological Survey **Mineral Resources Data System (MRDS)**. The pipeline reads longitude, latitude, commodities, site name, production-size class, development status, and record quality.

- [USGS MRDS publication](https://www.usgs.gov/publications/mineral-resources-data-system-mrds)
- [USGS Data Series 52](https://pubs.usgs.gov/publication/ds52)

MRDS is a historical resource inventory. It does not necessarily represent current production, ownership, reserves, or operating status. This project uses it as a geographic and relative-ranking source for gameplay.

### Curated Major-District Anchors

`tools/pipeline/make_world_v1_400_global_rich_ore_pack.py` contains a curated `ZONES` list from the earlier project. These high-confidence anchors supplement commodities for which MRDS is sparse or geographically uneven.

Anchor score:

```text
5000 - original list rank
```

### Global Energy Monitor Coal Anchors

Major modern coal mines are supplemented from [Global Energy Monitor's Global Coal Mine Tracker](https://www.gem.wiki/Global_Coal_Mine_Tracker).

Supplemental coal score:

```text
6200 - supplemental list rank
```

The embedded list is a small set of anchors, not a redistribution of the full tracker.

## Commodity Mapping

The pipeline matches MRDS commodity fields and textual fields including site name, deposit type, ore, gangue, model, and aliases.

| Minecraft output | Real-data matching |
|---|---|
| Coal | coal, lignite, bituminous, subbituminous, anthracite |
| Iron | iron, hematite, magnetite |
| Copper | copper, porphyry |
| Gold | gold |
| Create Zinc | zinc |
| Diamond | diamond, kimberlite |
| Redstone | uranium, vanadium, thorium, rare earths, monazite |
| Lapis | lapis lazuli, lazurite, Badakhshan |
| Emerald | emerald, jade, jadeite, nephrite |

Redstone is a gameplay proxy for uranium/vanadium/thorium/REE districts. Jade is mapped to emerald but receives a smaller influence radius.

## MRDS Scoring

Production size contributes: `L=600`, `M=450`, `S=300`, `Y=250`, `N=20`, and unknown/empty `=0`.

Development status contributes: Producer `300`, Past Producer `220`, Prospect `120`, Plant `80`, Occurrence `10`, and Unknown `0`.

Record quality contributes: A `250`, B `160`, C `80`, D `20`, and E/empty `0`.

An additional 120 points are added when the target commodity is the primary commodity. Non-U.S. records receive 25 balancing points to reduce, but not eliminate, geographic sampling bias.

## Deduplication and Country Caps

Candidates are processed by descending score:

1. A record within 22 km of an already selected point is treated as a duplicate.
2. Each mineral keeps at most 100 locations.
3. MRDS coal allows up to 45 records per country.
4. Other U.S. MRDS minerals allow up to 28 records per mineral.
5. Other countries allow up to 22 MRDS records per mineral.

Curated anchors are retained as important supplements and are not identical to ordinary MRDS candidates.

## Five Prosperity Tiers

Ranking is independent for each mineral:

| Tier | Rank per mineral | Meaning |
|---|---:|---|
| 5 | 1–10 | world-class core districts |
| 4 | 11–25 | major districts |
| 3 | 26–50 | large districts |
| 2 | 51–75 | regional districts |
| 1 | 76–100 | local districts |

Base core radius is derived from production size: L 150 km, M 115 km, S 80 km, Y 75 km, N 45 km, U 40 km, and empty 38 km. Emerald/jade radii are multiplied by 0.62 with a 28 km minimum.

Outer-radius multipliers are: tier 5 `1.90`, tier 4 `1.65`, tier 3 `1.45`, tier 2 `1.28`, and tier 1 `1.14`. Ore-layer generation then applies a global `1.33` radius multiplier and paints outer, middle, and core ellipses.

Longitude radius is corrected by latitude cosine so a fixed real-world radius does not become too narrow at high latitudes.

## Vein Density

Each mineral defines block IDs, vein size, base count, and vertical range. Tier count multipliers are: tier 5 `2.00`, tier 4 `1.00`, tier 3 `0.66`, tier 2 `0.24`, and tier 1 `0.10`.

Approximate attempts per chunk:

```text
max(1, round(base count × tier density))
```

Tier 4 and tier 5 may add mineral-block cores at approximately 1% and 2% of theoretical vein-block volume. Actual in-game percentages vary because replacement targets, chunk boundaries, and terrain affect successful placement.

## Overlapping Districts

Each mineral stores a value from 0 to 5 in a base-6 combination code. Common combinations become separate `ore_combo_*` cave biomes. To keep registry and datapack size stable, uncommon complex combinations can collapse to their strongest single-mineral influence.

## Coverage Percentage

Coverage uses the rectangular Minecraft map grid as its denominator, not spherical Earth area or mineable real-world land. High latitudes are enlarged by the equirectangular layout, so coverage is only useful for comparing gameplay profiles.

## Cave-Biome Side Effects

Ore combinations replace the original underground biome instead of injecting features into it. Custom ore biomes do not reproduce every cave feature or biome tag. Amethyst geodes, lush-cave decoration, deep-dark identity, ancient-city eligibility, or modded structures may be lost in covered regions.

