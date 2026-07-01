# Minecraft Earth Map for NovoAtlas

**TerraScale：1:200 与 1:400 Minecraft 真实数据地球地图**

[English](README.md) | [简体中文](README.zh-CN.md)

这是一个面向 Minecraft 1.21.1 / NeoForge 的真实数据地球世界：高程、海岸线、土地覆盖、气候、河流、海洋与矿区共同决定地形，而不是简单放大一张世界地图。TerraScale 使用太平洋中心全球坐标、高精度地理分区处理和 NovoAtlas 瓦片图层，让超大比例地球地图能够实际加载、局部重建并继续开发。

项目提供可直接使用的 **1:200** 与 **1:400** 两种比例，以及两套可选富矿规则。

## Download

### [前往 Releases 下载最新版本](../../releases/latest)

下载时需要 **一个 NovoAtlas JAR + 一个地图数据包 ZIP**。

### 1. 下载必需 JAR

```text
novoatlas-neoforge-1.21.1-earth-tiled-r4.jar
```

### 2. 四选一下载地图

| 用途 | 比例 | 矿产规则 | 下载文件 |
|---|---:|---|---|
| 最高地理细节 | 1:200 | Original Rich Ore | `1-200-original-rich-ore-antarctica-fixed-requires-create.zip` |
| 最高地理细节 + 真实矿区 | 1:200 | Top100 Rich Ore | `1-200-top100-rich-ore-antarctica-fixed-requires-create.zip` |
| 较小世界、较低生成成本 | 1:400 | Original Rich Ore | `1-400-fixed-original-rich-ore-requires-create.zip` |
| 较小世界 + 真实矿区 | 1:400 | Top100 Rich Ore | `1-400-fixed-top100-rich-ore-requires-create.zip` |

不要在同一个世界中同时安装多个地图包。

## Requirements

- Minecraft 1.21.1
- NeoForge
- [Create](https://github.com/Creators-of-Create/Create) for Minecraft 1.21.1
- 本项目发布的修改版 NovoAtlas JAR

> 当前四个地图包都包含 Create 锌矿，因此需要 Create。没有 Create 时可能在创建世界前出现数据包验证失败。

> **地下内容兼容性警告：** 当前富矿通过自定义 cave biome 实现。在富矿覆盖区域，深暗之域、繁茂洞穴等原地下群系可能被替换，紫水晶晶洞、古城及其他依赖原群系或群系特征的内容可能减少或消失。重视原版地下结构的服务器建议使用无自定义富矿转换工具。

不需要自定义富矿的用户可以使用仓库中的转换工具生成无富矿、无 Create 依赖版本，且不必重新生成地球地表。

## Quick Installation

1. 在客户端和服务端安装 NeoForge、Create 及其依赖。
2. 将修改版 NovoAtlas JAR 放入客户端和服务端的 `mods`。
3. 下载上表中的一个地图 ZIP 并解压。
4. 创建世界前，将解压出的数据包文件夹放入世界的 `datapacks`。
5. 创建新世界并确认数据包验证通过。

已生成区块不会因更换数据包自动更新。地图可以边探索边生成，不要求预先使用 Chunky 加载全球。

## Choose an Edition

### 1:200

- 全球尺寸：`163840 x 92160` blocks。
- 海岸、湖泊、小岛和区域轮廓细节更高。
- 数据包、区块存档和预生成成本更高。
- 当前版亚洲以外部分地区可能缺少河流。

### 1:400

- 全球尺寸：`81920 x 46080` blocks。
- 更适合普通服务器和较低存储预算。
- 使用全球 HydroRIVERS 大陆数据。
- 已修正南极非雪原问题。

### Original Rich Ore

保留项目早期整理的富矿分布规则。

### Top100 Rich Ore

按矿种整理全球主要矿区，并分为五级富庶程度。高等级矿区具有更高矿脉密度，四级和五级包含少量矿物块核心。

## Main Features

- 全球 Pacific-centered 地图布局与统一绝对坐标。
- 真实高程、土地覆盖、气候和水系驱动的地表群系。
- 暖水、温水、冷水、冻结及深海等多种海洋群系。
- 2048 x 2048 tiled image map，避免加载单张全球超大 PNG。
- 分片生成、断点续跑和全球瓦片拼装工具。
- 可移除富矿、移除 Create 锌矿、添加其他模组矿石。
- 可重新生成 1:100、1:300、1:800 等自定义比例。

## 项目介绍

本项目把真实地理数据转换为 NovoAtlas 的瓦片化高度、地表群系和地下矿产图。432 个地理分片只用于离线构建；最终服务器加载一个拼装完成的数据包，并在玩家探索时生成新区块。

Pacific-centered 坐标系统将地图接缝放在 31.5°W。经纬度可以通过公式或 `tools/scale/convert_coordinates.py` 直接换算为 Minecraft X/Z。

[阅读完整项目介绍](docs/zh-CN/PROJECT_INTRODUCTION_zh-CN.md) · [坐标系统与换算公式](docs/zh-CN/COORDINATE_SYSTEM_zh-CN.md)

## Known Limitations

- 1:200 版沿用较早的亚洲水系管线，亚洲以外部分区域可能缺少河流。
- 安第斯、落基山及部分高原可能被映射为偏干旱的 Minecraft 山地群系。
- 富矿 cave biome 可能覆盖原地下群系，使紫水晶晶洞、古城、繁茂洞穴等内容在矿区内减少或消失。
- 城市建筑、道路、铁路和行政边界不由本项目生成。
- 水平比例与 Minecraft 垂直高度不是同一缩放比例。
- 本项目是游戏世界生成方案，不是测绘或矿业评估产品。

[阅读完整不足说明](docs/zh-CN/LIMITATIONS_zh-CN.md)

## Documentation

### 玩家与服务器管理者

- [安装与服务器部署](docs/zh-CN/INSTALLATION_zh-CN.md)
- [兼容性与锌矿](docs/zh-CN/COMPATIBILITY_zh-CN.md)
- [已知不足与适用范围](docs/zh-CN/LIMITATIONS_zh-CN.md)
- [Release 文件与校验值](release/ASSETS.zh-CN.md)

### 技术路线

- [项目介绍](docs/zh-CN/PROJECT_INTRODUCTION_zh-CN.md)
- [坐标系统与换算公式](docs/zh-CN/COORDINATE_SYSTEM_zh-CN.md)
- [技术概览](docs/zh-CN/TECHNICAL_OVERVIEW_zh-CN.md)
- [数据来源与署名](docs/zh-CN/DATA_SOURCES_zh-CN.md)
- [矿产数据来源与现行规则](docs/zh-CN/MINERAL_DATA_AND_RULES_zh-CN.md)

### 重新生成与二次开发

- [1:200 与 1:400 重新生成指南](docs/zh-CN/REBUILD_GUIDE_zh-CN.md)
- [富矿、无 Create 与其他矿石定制](docs/zh-CN/ORE_CUSTOMIZATION_zh-CN.md)
- [编写自己的矿产规则](docs/zh-CN/WRITING_CUSTOM_MINERAL_RULES_zh-CN.md)
- [自定义 1:100、1:300、1:800 等比例](docs/zh-CN/SCALE_CUSTOMIZATION_zh-CN.md)
- [生成工具说明](tools/README.zh-CN.md)

## Source and License

修改版 NovoAtlas 位于 `novoatlas-mod`，上游项目为 [TheDeathlyCow/novoatlas](https://github.com/TheDeathlyCow/novoatlas)。源码保留 LGPL-3.0 许可证。地理数据仍受各数据提供方许可约束。

本项目与 Mojang、Microsoft、Create、NovoAtlas 及数据提供方不存在官方隶属关系。
