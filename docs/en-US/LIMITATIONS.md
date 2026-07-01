# Known Limitations and Intended Use

[English](LIMITATIONS.md) | [简体中文](../zh-CN/LIMITATIONS_zh-CN.md)

The project is usable for normal world creation and server play, but it is not a perfectly accurate digital twin of Earth.

## Geography and Biomes

- **Incomplete 1:200 rivers:** the 1:200 release retains an older Asia-focused HydroRIVERS pipeline. Some rivers outside Asia may be missing even when coastlines and lakes are present.
- **Highland classification errors:** the Andes, Rockies, Tibetan margins, and other cold or dry highlands may map to overly orange or arid Minecraft mountain biomes. This usually indicates biome classification, not intentionally generated lava fields.
- **Compressed elevation:** horizontal scale and vertical Minecraft height use different transformations.
- **Small-feature loss:** narrow rivers, tiny islands, urban lakes, and fragmented coastlines may be widened, simplified, or omitted by source resolution and rasterization.
- **Protected polar rules:** the 1:400 Antarctic landmass uses a deliberate snow-biome override after real coastline and elevation sampling.

## Rich Ores and Underground Content

Original and Top100 ore editions use NovoAtlas cave-biome maps. Ore-covered cells become custom `world:ore_combo_*` biomes rather than receiving features on top of the original cave biome.

Possible effects include:

- deep dark replacement and loss of ancient-city eligibility;
- loss of lush cave or dripstone cave identity and decoration;
- missing amethyst geodes or other features not copied into custom ore biomes;
- missing modded structures, mobs, or decoration selected by original biome tags.

The impact is limited to cells covered by the custom Ore layer, but larger and overlapping districts increase the affected area. Use the no-custom-ore tool when vanilla underground content is the priority.

## World Content

- Real cities, buildings, roads, railways, borders, and population are not generated.
- Vanilla and modded structures still follow their own placement logic and may not match real locations.
- Datapack upgrades only affect newly generated chunks.

## Performance and Storage

- Tiled loading avoids single-image memory spikes, but first-time generation remains slower than a normal vanilla world.
- Full Chunky pregeneration can require very large storage and long CPU time.
- BlueMap and similar render caches can exceed the datapack size and are outside this project's storage figures.

## Data Accuracy

- Source datasets have different dates, resolutions, and boundary definitions.
- Rich-ore tiers are gameplay abstractions, not reserve estimates, mining rights, or economic valuations.
- Do not use the project for navigation, engineering, safety, surveying, or investment decisions.

