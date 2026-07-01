# Project Introduction

[English](PROJECT_INTRODUCTION.md) | [简体中文](../zh-CN/PROJECT_INTRODUCTION_zh-CN.md)

## What This Project Is

**Minecraft Earth Map for NovoAtlas**, branded **TerraScale**, is a real-data global world-generation project for Minecraft 1.21.1 / NeoForge. Its goal is not merely to reproduce the outline of Earth, but to make geography recognizable through terrain: mountain systems rise from elevation data, climates and land cover shape surface biomes, river and ocean datasets define water environments, and optional mineral layers place richer underground regions near real mining districts.

The project converts those sources into tiled height, surface-biome, and underground-ore maps consumed by a modified NovoAtlas build. A Pacific-centered coordinate system keeps major continents intact in commonly explored areas, while a resumable 432-region offline pipeline provides substantially more local detail than generating every layer from one low-resolution global image.

TerraScale therefore combines three goals that are often in conflict: a recognizable whole Earth, enough regional detail for exploration, and a package that a Minecraft server can actually load and generate incrementally.

Two ready-to-use horizontal scales are published:

- **1:200:** one horizontal block represents approximately 200 meters and preserves more coastline and regional detail.
- **1:400:** one horizontal block represents approximately 400 meters, reducing world span and server-generation cost.

The map uses a Pacific-centered layout. Its west seam is at `31.5°W`, placing the visual center near `148.5°E`. This keeps Asia, Oceania, the Pacific, and the Americas in the familiar Pacific-centered world-map arrangement.

## Why NovoAtlas Was Modified

A global 1:200 or 1:400 layer stored as one enormous PNG can cause datapack validation failures, large decode-time memory spikes, startup stalls, and difficult partial updates.

The modified NovoAtlas build supports tiled image maps:

```text
height/{tx}_{tz}.png
surface/{tx}_{tz}.png
ore/{tx}_{tz}.png
```

Tiles are 2048 x 2048 pixels. Runtime loading and offline patching can operate on the required tiles instead of decoding or rewriting one global image.

## How the Final Datapack Works

The server loads one normal datapack. The 432 geographic regions exist only during offline construction:

1. A script builds one longitude/latitude bounding box.
2. Every region samples data in the same absolute global coordinate system.
3. Height and biome output is patched into the corresponding global tiles.
4. After all regions are assembled, the server uses the completed package.

This is not 432 datapacks controlling separate pieces of a world, and it is not a fully pregenerated Minecraft save. NovoAtlas generates new chunks from the datapack as players explore.

## Ore Editions

Each scale has two underground profiles:

- **Original Rich Ore:** the project's earlier curated distribution.
- **Top100 Rich Ore:** five prosperity tiers derived from major real-world districts for each mineral.

Rich ores currently use custom cave biomes. This enables global coordinate control but may replace vanilla cave-biome identity and affect ancient cities, lush caves, and amethyst geodes. Users who only need Earth terrain can remove the custom Ore layer.

## Intended Users

- Earth-scale survival, geopolitical, transport, or aviation server operators;
- modpack authors who need recognizable continents, climate, and mineral geography;
- developers studying NovoAtlas, raster geographic data, and Minecraft world generation;
- contributors creating new scales such as 1:100, 1:300, or 1:800.

## What Is Not Included

- real city buildings, roads, railways, or political borders;
- a save with every chunk already generated;
- surveying-grade geographic accuracy or current mining statistics;
- guaranteed compatibility between custom cave biomes and every modded structure.

The engineering goal is a reproducible balance between geographic recognizability, Minecraft playability, datapack size, and server performance.
