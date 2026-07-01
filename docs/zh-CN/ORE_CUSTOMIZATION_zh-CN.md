# 富矿、无 Create 与其他模组矿石定制

地表、高程和地下矿产是独立图层。多数矿产改动不需要重新生成全球地表。

## 1. 完全不需要自定义富矿

使用仓库提供的转换工具：

```powershell
python tools\ore\make_no_custom_ore_variant.py `
  "D:\packs\Top100RichOre_1_400_HQ_Pacific_FullRoute" `
  "D:\packs\EarthMap_1_400_NoCustomOre"
```

该工具会复制原包并：

- 从 `map_info` 移除 cave-biome 富矿层；
- 删除 ore PNG 瓦片；
- 删除 `ore_combo_*` 地下群系；
- 删除所有自定义 rich configured/placed features；
- 清理 biome tag 中的富矿引用；
- 检查是否仍残留 `create:` 或自定义富矿引用。

转换后仍保留完整地球高度和地表群系，地下回到这些 Minecraft 群系自身的普通矿物生成。该版本不再因本项目锌矿而依赖 Create。

这也是希望保留古城、深暗之域、繁茂洞穴、紫水晶晶洞和其他模组地下结构时的推荐方案，因为这些内容可能被富矿 cave biome 覆盖。

## 2. 保留富矿，但不使用 Create 锌矿

不能只删除 `zinc_rich_*.json`。矿区 PNG 的颜色对应多矿种组合，删除文件会让部分 cave biome 引用不存在的 feature。

正确流程：

1. 在 `tools/ore/build_top100_rich_ore_dataset.py` 的矿种规则中移除 zinc；
2. 在 `tools/ore/make_global_top100_rich_ore_layer_tiles.py` 的 `ORES` 字典中移除 zinc；
3. 过滤矿床 JSON 中 `"ore": "zinc"` 的记录；
4. 重新运行矿区数据整理与 Ore 图层生成；
5. 用新的 ore PNG、map-info patch、biome 和 feature 覆盖模板包；
6. 搜索最终包，确认不存在 `create:`。

由于 `ORES` 的顺序参与组合编码，修改矿种列表后必须整体重建 Ore 图层，不能复用旧颜色表。

## 3. 添加其他模组矿石

假设目标模组提供：

```text
examplemod:tin_ore
examplemod:deepslate_tin_ore
examplemod:tin_block
```

在 `make_global_top100_rich_ore_layer_tiles.py` 的 `ORES` 中新增：

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

随后在矿床候选数据中加入：

```json
{
  "ore": "tin",
  "name": "Example Tin District",
  "longitude": 100.0,
  "latitude": 20.0,
  "tier": 3,
  "core_radius_km": 40,
  "outer_radius_km": 100
}
```

重新生成 Ore 图层后，脚本会创建对应 configured feature、placed feature 和组合 cave biome。

注意事项：

- 方块 ID 必须真实存在；先用目标模组版本确认注册名。
- 客户端和服务端都必须安装该模组。
- 如果模组没有深板岩矿石，可将 `deepslate_ore` 设为普通矿石 ID，但视觉效果会不同。
- 如果没有储存块，不应随便指定其他矿物块。可以把 `core` 设为矿石本身，或修改脚本使该矿种不生成四级/五级核心。
- 新矿种会增加组合数量；过多组合可能造成数据包体积和注册数量显著增长。

## 4. 调整富庶程度

`TIERS` 控制五级矿区的排名范围、密度、半径和核心比例；每个矿种的 `vein_size`、`count`、`min_y`、`max_y` 控制矿脉形态。

修改这些参数后只需重建 Ore 图层，不需要重跑 height 和 surface。建议先生成小范围测试世界，确认矿物没有过密、过稀或超出目标高度，再制作全球包。

## 5. 只使用地球地表，不控制地下

这是兼容性最好的公开变体。使用 `make_no_custom_ore_variant.py` 后，其他模组可以按自身 biome modifier 或 placed feature 规则生成矿物，本项目只负责全球高度和地表群系。
