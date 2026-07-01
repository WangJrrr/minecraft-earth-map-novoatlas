# 兼容性与锌矿

## 必需模组

当前 Release 数据包直接引用：

```text
create:zinc_ore
create:deepslate_zinc_ore
create:zinc_block
```

因此 Create 是必需依赖。没有 Create 时，这些注册项不存在，Minecraft 可能在创建世界之前报告数据包验证失败。

## 为什么不把锌替换成铜或铁

锌矿区来自锌矿产数据。将它替换为铜或铁虽然能消除模组依赖，却会改变地图表达的矿种含义，因此当前正式版选择保留 Create 锌矿并明确声明依赖。

## 无 Create 版本

纯原版兼容版不能通过删除几个 zinc JSON 文件获得。地下群系使用多矿种组合编码，正确处理方式是重新生成 Ore 瓦片、颜色映射和 cave biome，并从所有组合中移除锌。锌矿区在无 Create 版本中应不提供额外富矿，而不是伪装为其他矿物。

当前仓库暂不发布预打包的无 Create 数据包，但提供 `tools/ore/make_no_custom_ore_variant.py`。它可以从任一解压后的 Release 包移除完整自定义富矿层，同时保留地球高度和地表。

## 原版地下结构兼容性

富矿层使用 `world:ore_combo_*` cave biome 覆盖原地下群系。因此矿区内可能无法保留深暗之域、繁茂洞穴等群系身份，也可能缺失紫水晶晶洞、古城和依赖原 biome tag 的模组结构。

无自定义富矿转换工具会移除整个 cave-biome Ore 图层，让地下继续使用正常群系及其他模组自己的矿物/结构规则。这是目前保持地下兼容性最可靠的选项。
