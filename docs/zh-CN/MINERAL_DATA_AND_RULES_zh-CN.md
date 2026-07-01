# 矿产数据来源与现行规则

## 1. 数据来源

Top100 富矿不是由随机噪声生成，也不是简单手写 100 个点。当前候选数据由三部分组成。

### 1.1 USGS MRDS

主要全球点位来自美国地质调查局的 **Mineral Resources Data System (MRDS)**。项目使用 CSV 中的经纬度、矿种、矿点名称、生产规模、开发状态和记录质量等字段。

相关官方资料：

- [USGS MRDS publication](https://www.usgs.gov/publications/mineral-resources-data-system-mrds)
- [USGS Data Series 52](https://pubs.usgs.gov/publication/ds52)

MRDS 是历史矿产资源数据库，不代表矿山当前产量、所有权或最新储量。项目将它用于游戏地图中的地理锚点和相对等级，不把它当作实时矿业统计。

### 1.2 人工整理的主要矿区锚点

`tools/pipeline/make_world_v1_400_global_rich_ore_pack.py` 中的 `ZONES` 保存项目早期整理的重要矿区。这些点具有较高置信度，主要用于补充 MRDS 中排名不足、位置偏差或记录稀少的著名矿区。

人工锚点的基础得分为：

```text
5000 - 原列表排名
```

因此它们通常优先进入每个矿种的前 100。

### 1.3 Global Energy Monitor 煤矿补充

MRDS 对大型现代煤矿的表达不够均衡，因此脚本额外加入 Global Energy Monitor 的主要煤矿锚点。

- [Global Coal Mine Tracker](https://www.gem.wiki/Global_Coal_Mine_Tracker)

补充煤矿的基础得分为：

```text
6200 - 补充列表排名
```

补充列表不是完整 Tracker 数据副本，只是用于保证全球主要煤矿不会因 MRDS 字段差异而全部落选。

## 2. 矿种映射

脚本在 MRDS 的 `commod1`、`commod2`、`commod3` 以及名称、矿床类型、矿石、脉石和模型字段中匹配关键词。

| Minecraft 矿物 | 现实数据匹配 |
|---|---|
| Coal | coal、lignite、bituminous、subbituminous、anthracite |
| Iron | iron、hematite、magnetite |
| Copper | copper、porphyry |
| Gold | gold |
| Create Zinc | zinc |
| Diamond | diamond、kimberlite |
| Redstone | uranium、vanadium、thorium、rare earths、monazite |
| Lapis | lapis lazuli、lazurite、Badakhshan |
| Emerald | emerald、jade、jadeite、nephrite |

Redstone 没有现实中的直接矿种，对应铀、钒、钍和部分稀土矿区，是为了把现实工业/放射性矿区映射为 Minecraft 红石玩法层。玉、硬玉和软玉映射为绿宝石，但绿宝石的影响半径会额外缩小。

## 3. MRDS 评分

每条 MRDS 记录的基础分数由三部分相加。

### 3.1 生产规模 `prod_size`

| 代码 | 分数 |
|---|---:|
| L | 600 |
| M | 450 |
| S | 300 |
| Y | 250 |
| N | 20 |
| U / 空值 | 0 |

### 3.2 开发状态 `dev_stat`

| 状态 | 分数 |
|---|---:|
| Producer | 300 |
| Past Producer | 220 |
| Prospect | 120 |
| Plant | 80 |
| Occurrence | 10 |
| Unknown | 0 |

### 3.3 记录质量 `score`

| 代码 | 分数 |
|---|---:|
| A | 250 |
| B | 160 |
| C | 80 |
| D | 20 |
| E / 空值 | 0 |

若目标矿种出现在第一主矿种字段，再加 120 分。为减轻 MRDS 对美国记录较多造成的地域偏差，美国以外记录加 25 分。这个修正只能改善分布，不能消除数据库本身的采样偏差。

## 4. 去重与地域上限

候选点按得分从高到低处理：

1. 与已经入选点距离小于 22 km 的记录被视为重复并跳过。
2. 每个矿种最多保留 100 个点。
3. MRDS 煤矿每个国家最多 45 个。
4. 美国的其他 MRDS 矿种每种最多 28 个。
5. 其他国家的每种 MRDS 矿种最多 22 个。

人工锚点和煤矿补充点用于保留重要矿区，不完全受 MRDS 国家上限约束。

## 5. 五级富庶程度

每个矿种独立排名，而不是把所有矿种混在一起只取全球 100 个。

| 等级 | 每矿种排名 | 含义 |
|---|---:|---|
| 5 | 1–10 | 世界级核心矿区 |
| 4 | 11–25 | 主要矿区 |
| 3 | 26–50 | 大型矿区 |
| 2 | 51–75 | 区域矿区 |
| 1 | 76–100 | 地方矿区 |

生产规模还决定基础核心半径：

| `prod_size` | 基础核心半径 |
|---|---:|
| L | 150 km |
| M | 115 km |
| S | 80 km |
| Y | 75 km |
| N | 45 km |
| U | 40 km |
| 空值 | 38 km |

绿宝石/玉类半径乘以 0.62，且不低于 28 km。外圈半径再按等级乘以：5 级 1.90、4 级 1.65、3 级 1.45、2 级 1.28、1 级 1.14。

生成 Ore 图层时，所有半径还统一乘以 `RICH_ORE_RADIUS_MULTIPLIER = 1.33`。每个矿区由外圈、中圈和核心三层椭圆组成，等级从外向内逐步提高。

经度方向半径会按纬度余弦修正，使同一现实公里半径在高纬度不会被错误压窄。

## 6. 矿脉密度

每个矿种在 `ORES` 中定义：

```text
ore / deepslate_ore / core
vein_size
count
min_y / max_y
```

等级密度系数为：

| 等级 | `count` 系数 |
|---|---:|
| 5 | 2.00 |
| 4 | 1.00 |
| 3 | 0.66 |
| 2 | 0.24 |
| 1 | 0.10 |

实际每区块尝试次数约为：

```text
max(1, round(矿种 count × 等级密度系数))
```

四级和五级可额外生成矿物块核心。公开脚本与成品规则分别使用约 1% 和 2% 的理论矿脉方块量计算核心尝试数；由于矿脉会受替换方块、空气暴露和区块边界影响，游戏内最终比例不是严格统计值。

## 7. 重叠矿区

同一位置可能同时存在铁、铜、金、锌等矿区。脚本以六进制式位置编码保存每种矿物的 0–5 级值，再为常见组合生成独立 `ore_combo_*` cave biome。

为避免注册数无限增长，脚本只保留稳定数量的常见组合；过于复杂的组合会折叠为其中影响最大的单矿种组合。这是一项性能和数据包规模取舍。

## 8. 覆盖率含义

文档中的矿区覆盖率以 Minecraft 的矩形全球栅格像素为分母，不是球形地球真实表面积，也不是现实可开采土地比例。高纬度区域在等经纬度矩形图中面积会被放大，因此覆盖率只能用于比较游戏版本之间的影响范围。

## 9. Cave-biome 实现的副作用

富矿组合通过自定义 cave biome 选择矿物 feature。这种实现可以让矿区按全球坐标变化，但会替换原地下群系，而不是在原群系上叠加矿石。

自定义 cave biome 只显式复制了部分原版矿石、怪物房间和发光地衣等 feature，没有完整复制所有洞穴群系内容。因此矿区可能缺少紫水晶晶洞、繁茂洞穴装饰等 feature；古城等依赖 `deep_dark` 群系或 biome tag 的结构也可能无法生成。

新增矿物时应将这个副作用计入设计。如果目标是最大限度兼容原版和其他模组，推荐开发坐标感知的 feature 注入机制，而不是继续增加 cave biome 组合。
