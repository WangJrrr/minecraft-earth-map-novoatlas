# Technical Overview

[English](TECHNICAL_OVERVIEW.md) | [简体中文](../zh-CN/TECHNICAL_OVERVIEW_zh-CN.md)

## Architecture

TerraScale separates world control into three image layers:

1. **Height** controls seabed, sea level, and land elevation.
2. **Surface** maps colors to Minecraft surface biomes.
3. **Ore** selects underground cave biomes containing rich-ore features.

The modified NovoAtlas build reads each layer as 2048 x 2048 tiles instead of one enormous global PNG. This lowers validation and image-decoding memory pressure and allows individual geographic regions to be replaced.

## Scale Profiles

| Parameter | 1:200 | 1:400 |
|---|---:|---:|
| Horizontal meaning | approximately 200 m/block | approximately 400 m/block |
| Global width | 163840 | 81920 |
| Global height | 92160 | 46080 |
| Geographic regions | 432 | 432 |
| Standard region pixels | 6144 x 6144 | 3072 x 3072 |
| NovoAtlas tile size | 2048 | 2048 |

Vertical height is compressed independently to remain playable within Minecraft's world-height limits.

## Geographic Regions

All regions share one global coordinate system. A builder samples data for a longitude/latitude bounding box, creates temporary height and biome images, and patches them into their absolute global tile locations.

Regions are an offline build mechanism. The final server uses one complete datapack, not 432 simultaneously loaded region packs.

## Surface Classification

The biome classifier combines ESA WorldCover, WorldClim temperature and precipitation, elevation, slope, latitude, coast relationships, HydroRIVERS, and Natural Earth water layers.

Ocean cells are classified by temperature and depth. Land is mapped to plains, forests, tropical biomes, savannas, deserts, wetlands, snow biomes, and mountain variants.

The fixed 1:400 pipeline selects HydroRIVERS archives by continent. Antarctic land south of 60°S retains real coast/elevation but receives a final snowy-plains, snowy-slopes, or frozen-peaks override.

## Rich-Ore Layer

Ore pixels select custom cave biomes. Each cave biome contains configured and placed features for one or more minerals and prosperity tiers. Overlapping districts use a compact multi-ore combination code.

This approach provides global coordinate control but replaces original cave-biome identity. See the compatibility and limitations documents before using rich ores on a structure-heavy modpack.

## Build Tools

`tools/1_200` and `tools/1_400` contain production region builders, queues, assembly tools, and finalizers. `tools/pipeline` contains shared real-data classification logic. Public scripts use environment variables for output, cache, pipeline, mineral input, and 1:400 work-root locations.
