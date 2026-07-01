# 编写自己的矿产规则

## 1. 两层配置

自定义矿产分为两层：

1. **矿区数据**：矿在哪里、是什么矿、等级和半径是多少。
2. **矿物生成参数**：使用哪个方块、矿脉大小、尝试次数和高度范围。

只修改其中一层通常不够。新增矿种必须同时让数据记录中的 `ore` 名称与 `ORES` 字典键一致。

## 2. 直接编写矿区 JSON

矿区文件是 JSON 数组，每条记录至少包含：

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

示例文件位于 `examples/custom_mineral_deposits.json`。

字段规则：

- `ore`：必须与 `ORES` 中的键完全一致，只使用小写 ASCII。
- `longitude`：-180 到 180。
- `latitude`：-90 到 90。
- `tier`：1 到 5。
- `core_radius_km`：最高等级核心影响半径。
- `outer_radius_km`：最低等级外圈影响半径，必须不小于核心半径。
- `source` 和 `source_url`：建议保留，便于公开项目追溯数据。

若你已经手动确定等级，可跳过 `build_top100_rich_ore_dataset.py`，直接把自定义 JSON 放到 Ore 生成脚本的 `DEPOSITS_JSON` 路径。

## 3. 在 MRDS 自动筛选中新增矿种

在 `build_top100_rich_ore_dataset.py` 中增加匹配规则：

```python
ORE_MATCHES["tin"] = {
    "commodities": {"tin"},
    "name_keywords": {"tin", "cassiterite"},
}
```

同时为预览增加颜色：

```python
ORE_COLORS["tin"] = (170, 180, 190)
```

如果目标数据不是 MRDS，可先转换为相同候选字段，再调用 `select_top100`；不要把没有来源的随机坐标混入公开数据。

## 4. 定义矿石方块

在 `make_global_top100_rich_ore_layer_tiles.py` 的 `ORES` 中加入：

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

参数建议：

- `vein_size`：一次矿脉最多尝试替换的方块数。稀有矿通常更小。
- `count`：五级密度计算前的基础尝试次数。
- `min_y` / `max_y`：均匀高度分布边界。
- `core`：四级、五级使用的少量核心方块。

如果目标模组没有深板岩矿石，可让 `deepslate_ore` 与普通矿石相同。如果没有储存块，建议修改脚本使该矿种不生成核心，而不是借用不相关的方块。

## 5. 调整等级规则

`TIERS` 同时影响排名边界、矿脉密度、范围和矿物块比例。可以按玩法修改，例如：

```python
TIERS = {
    5: {"max_rank": 5, "density": 1.50, "radius": 1.60, "core_fraction": 0.01},
    4: {"max_rank": 15, "density": 0.90, "radius": 1.45, "core_fraction": 0.005},
    3: {"max_rank": 35, "density": 0.55, "radius": 1.30, "core_fraction": 0.00},
    2: {"max_rank": 65, "density": 0.20, "radius": 1.18, "core_fraction": 0.00},
    1: {"max_rank": 100, "density": 0.08, "radius": 1.08, "core_fraction": 0.00},
}
```

数据筛选脚本和 Ore 生成脚本都包含 `TIERS`。若两处不同，候选文档中的等级范围与游戏内生成密度会不一致，修改时应同步。

## 6. 重新生成

```powershell
python tools\ore\build_top100_rich_ore_dataset.py
$env:NOVOATLAS_SCALE_DENOMINATOR = "200"
python tools\ore\make_global_top100_rich_ore_layer_tiles.py
```

第二个脚本中的 `WIDTH`、`HEIGHT`、dataset ID 与输出路径必须匹配目标比例。生成完成后，将以下内容合并到地表数据包：

- `ore/*.png`
- cave-biome map-info patch
- `data/world/worldgen/biome`
- configured features
- placed features
- biome tags

## 7. 验证清单

1. 所有 `namespace:block_id` 在目标模组版本中存在。
2. 客户端和服务端安装相同模组。
3. 最终包不存在旧矿种的悬空引用。
4. Ore PNG 颜色全部出现在 map-info cave biome 表中。
5. 每个 cave biome 引用的 placed feature 都存在。
6. 先用小地图和新世界验证，再生成或发布全球包。
