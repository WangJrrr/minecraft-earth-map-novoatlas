# Minecraft Earth Map for NovoAtlas

**TerraScale: Real-Data Earth Maps at 1:200 and 1:400**

[English](README.md) | [简体中文](README.zh-CN.md)

A data-driven Earth world for Minecraft 1.21.1 / NeoForge, built from real elevation, coastlines, land cover, climate, rivers, oceans, and mineral districts. Unlike a single enlarged map image, TerraScale uses a Pacific-centered global coordinate system, high-detail geographic region processing, and tiled NovoAtlas layers that remain practical to load and regenerate.

Ready-to-use **1:200** and **1:400** editions are provided with two optional rich-ore models.

## Download

### [Download the latest release](../../releases/latest)

You need **one NovoAtlas JAR and exactly one map ZIP**.

### 1. Required JAR

```text
novoatlas-neoforge-1.21.1-earth-tiled-r4.jar
```

### 2. Choose one map

| Use case | Scale | Ore model | Release asset |
|---|---:|---|---|
| Highest geographic detail | 1:200 | Original Rich Ore | `1-200-original-rich-ore-antarctica-fixed-requires-create.zip` |
| Highest detail + real mining districts | 1:200 | Top100 Rich Ore | `1-200-top100-rich-ore-antarctica-fixed-requires-create.zip` |
| Smaller world and lower generation cost | 1:400 | Original Rich Ore | `1-400-fixed-original-rich-ore-requires-create.zip` |
| Smaller world + real mining districts | 1:400 | Top100 Rich Ore | `1-400-fixed-top100-rich-ore-requires-create.zip` |

Do not install more than one Earth-map datapack in the same world.

## Requirements

- Minecraft 1.21.1
- NeoForge
- [Create](https://github.com/Creators-of-Create/Create) for Minecraft 1.21.1
- The modified NovoAtlas JAR published with this project

> All four current map packages reference Create zinc blocks and ores. Without Create, datapack validation may fail before world creation.

> **Underground compatibility warning:** rich-ore regions use custom cave biomes. They can replace deep dark, lush caves, and other underground biome identities, suppressing amethyst geodes, ancient cities, cave vegetation, or modded structures that depend on original biome tags. Servers prioritizing vanilla underground content should use the no-custom-ore conversion tool.

Users who only need the Earth terrain can run `tools/ore/make_no_custom_ore_variant.py`. It removes the custom ore layer and this project's Create dependency without rebuilding height or surface data.

## Quick Installation

1. Install NeoForge, Create, and its required dependencies on both client and server.
2. Put the modified NovoAtlas JAR in both `mods` folders.
3. Download and extract one map ZIP from the table above.
4. Before creating the world, place the extracted datapack folder in the world's `datapacks` directory.
5. Create a new world and confirm datapack validation succeeds.

Existing chunks are not rewritten when the datapack changes. The map can generate during exploration; full Chunky pregeneration is optional.

## Editions

### 1:200

- Global size: `163840 x 92160` blocks.
- Better coastline, lake, island, and regional detail.
- Higher datapack, storage, and pregeneration cost.
- Some rivers outside Asia may be missing in the current release.

### 1:400

- Global size: `81920 x 46080` blocks.
- More practical for typical servers and smaller storage budgets.
- Uses continental HydroRIVERS sources worldwide.
- Fixes non-snow Antarctic land biomes.

### Original Rich Ore

Preserves the project's earlier curated rich-ore distribution.

### Top100 Rich Ore

Builds five prosperity tiers from major real-world mining districts for each mineral. Higher tiers receive denser veins; tier 4 and tier 5 regions include a small amount of mineral-block cores.

## Main Features

- Pacific-centered global layout with one absolute coordinate system.
- Terrain biomes derived from elevation, land cover, climate, and hydrology.
- Warm, lukewarm, cold, frozen, and deep-ocean variants.
- 2048 x 2048 tiled image maps instead of single enormous PNG files.
- Geographic region queues, resumable builds, and global tile assembly.
- Tools for removing rich ores, removing Create zinc, or adding modded ores.
- Rebuild guidance for custom scales such as 1:100, 1:300, and 1:800.

## About the Project

This project converts real geographic datasets into tiled NovoAtlas height, surface-biome, and underground-ore maps. The 432 geographic regions are an offline construction method; the final server loads one assembled datapack and generates chunks during exploration.

The Pacific-centered coordinate system places its seam at 31.5°W. Longitude/latitude can be converted directly to Minecraft X/Z using the documented formula or `tools/scale/convert_coordinates.py`.

[Read the full project introduction](docs/en-US/PROJECT_INTRODUCTION.md) · [Coordinate system and formulas](docs/en-US/COORDINATE_SYSTEM.md)

## Known Limitations

- The 1:200 edition uses an older Asia-focused river pipeline; rivers may be missing in some non-Asian regions.
- The Andes, Rockies, and some plateaus may map to overly dry Minecraft mountain biomes.
- Rich-ore cave biomes can suppress amethyst geodes, ancient cities, lush caves, deep dark content, and modded underground structures.
- Cities, roads, railways, and administrative boundaries are not generated.
- Horizontal map scale and Minecraft vertical height compression are different.
- This is a game-world generator, not a surveying or mineral-resource assessment product.

[Read the complete limitations](docs/en-US/LIMITATIONS.md).

## Documentation

### Players and Server Administrators

- [Installation and server deployment](docs/en-US/INSTALLATION.md)
- [Compatibility and zinc](docs/en-US/COMPATIBILITY.md)
- [Known limitations](docs/en-US/LIMITATIONS.md)
- [Release assets and checksums](release/ASSETS.md)

### Technical Design

- [Project introduction](docs/en-US/PROJECT_INTRODUCTION.md)
- [Coordinate system and conversion formulas](docs/en-US/COORDINATE_SYSTEM.md)
- [Technical overview](docs/en-US/TECHNICAL_OVERVIEW.md)
- [Data sources and attribution](docs/en-US/DATA_SOURCES.md)
- [Mineral data and current rules](docs/en-US/MINERAL_DATA_AND_RULES.md)

### Rebuilding and Custom Development

- [Rebuilding 1:200 and 1:400](docs/en-US/REBUILD_GUIDE.md)
- [Ore profiles, no-Create builds, and modded ores](docs/en-US/ORE_CUSTOMIZATION.md)
- [Writing custom mineral rules](docs/en-US/WRITING_CUSTOM_MINERAL_RULES.md)
- [Custom scales: 1:100, 1:300, 1:800, and others](docs/en-US/SCALE_CUSTOMIZATION.md)
- [Build tools](tools/README.md)

## Source and License

The modified NovoAtlas source is in `novoatlas-mod`. Upstream: [TheDeathlyCow/novoatlas](https://github.com/TheDeathlyCow/novoatlas). The source retains the LGPL-3.0 license. Geographic datasets remain subject to their providers' licenses.

This independent community project is not affiliated with or endorsed by Mojang, Microsoft, Create, NovoAtlas, or the data providers.
