# Writing Custom Mineral Rules

[English](WRITING_CUSTOM_MINERAL_RULES.md) | [简体中文](../zh-CN/WRITING_CUSTOM_MINERAL_RULES_zh-CN.md)

## Two Configuration Layers

Custom minerals require both:

1. **Deposit data:** location, commodity key, tier, and radius.
2. **Generation settings:** block registry IDs, vein size, attempts, and height range.

The `ore` value in deposit JSON must exactly match a key in the generator's `ORES` dictionary.

## Deposit JSON

```json
{
  "ore": "tin",
  "name": "Example Tin District",
  "longitude": 100.0,
  "latitude": 20.0,
  "tier": 3,
  "core_radius_km": 40.0,
  "outer_radius_km": 100.0,
  "country": "Example Country",
  "region": "Western Region",
  "source": "custom",
  "source_url": "https://example.com/source"
}
```

See `examples/custom_mineral_deposits.json`.

- `ore`: lowercase ASCII key matching `ORES`.
- `longitude`: -180 to 180.
- `latitude`: -90 to 90.
- `tier`: 1 to 5.
- `core_radius_km`: highest-tier inner radius.
- `outer_radius_km`: outer influence radius, not smaller than core radius.
- `source` / `source_url`: recommended for traceability.

Manually tiered JSON can be passed directly to the Ore generator without running MRDS ranking.

## Adding an MRDS-Matched Commodity

In `build_top100_rich_ore_dataset.py`:

```python
ORE_MATCHES["tin"] = {
    "commodities": {"tin"},
    "name_keywords": {"tin", "cassiterite"},
}
ORE_COLORS["tin"] = (170, 180, 190)
```

For non-MRDS data, convert records to the same candidate fields before ranking. Public datasets should retain source attribution.

## Defining Blocks and Placement

In `make_global_top100_rich_ore_layer_tiles.py`:

```python
"tin": {
    "ore": "examplemod:tin_ore",
    "deepslate_ore": "examplemod:deepslate_tin_ore",
    "core": "examplemod:tin_block",
    "vein_size": 24,
    "count": 12,
    "min_y": -48,
    "max_y": 72,
},
```

- Smaller `vein_size` is appropriate for rare minerals.
- `count` is the base value before tier multipliers.
- `min_y` and `max_y` define uniform placement bounds.
- `core` is used only for high-tier mineral-block cores.

If no deepslate variant exists, the normal ore ID can be reused. If no storage block exists, disable cores for that mineral or use the ore itself; do not borrow an unrelated block.

## Custom Tier Rules

Both the ranking script and Ore generator define `TIERS`. Keep them synchronized. Changing ore order also changes base-6 combination encoding, so the entire Ore layer and cave-biome palette must be rebuilt.

## Rebuild

```powershell
python tools\ore\build_top100_rich_ore_dataset.py
$env:NOVOATLAS_SCALE_DENOMINATOR = "200"
python tools\ore\make_global_top100_rich_ore_layer_tiles.py
```

Merge generated Ore PNGs, the map-info cave-biome patch, biome JSON, configured features, placed features, and biome tags into the terrain datapack.

## Validation

1. Verify every `namespace:block_id` exists in the target mod version.
2. Install the same content mods on client and server.
3. Search the final pack for stale mineral references.
4. Ensure every Ore PNG color exists in the map-info palette.
5. Ensure every cave biome references existing placed features.
6. Test a small new world before publishing a global package.
