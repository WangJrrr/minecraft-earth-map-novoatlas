# 坐标系统与经纬度换算

[English](../en-US/COORDINATE_SYSTEM.md) | [简体中文](COORDINATE_SYSTEM_zh-CN.md)

## 地图方向

- Minecraft `X` 对应东西方向，向东总体增加。
- Minecraft `Z` 对应南北方向，向南增加、向北减少。
- 全球地图西侧接缝经度为 `-31.5°`，即 `31.5°W`。
- 地图中央经度为 `148.5°E`。
- 北极接近最小 Z，南极接近最大 Z。

世界坐标原点 `(0, 0)` 位于全球矩形地图中央附近，不是经纬度 `(0°, 0°)`。

## 地图尺寸

| 比例 | `W` 全球宽度 | `H` 全球高度 | X 范围约 | Z 范围约 |
|---|---:|---:|---:|---:|
| 1:200 | 163840 | 92160 | -81920 到 81919 | -46080 到 46079 |
| 1:400 | 81920 | 46080 | -40960 到 40959 | -23040 到 23039 |

## 经纬度转 Minecraft X/Z

设：

```text
lon = 经度，东经为正、西经为负
lat = 纬度，北纬为正、南纬为负
S = -31.5（Pacific west seam）
W = 全球宽度
H = 全球高度
```

先把经度移动到 Pacific-centered 范围：

```text
shifted_lon = (lon - S) mod 360
```

然后计算：

```text
X = round(shifted_lon / 360 × W - W / 2)
Z = round((90 - lat) / 180 × H - H / 2)
```

`mod 360` 的结果应位于 `[0, 360)`。不同编程语言对负数取模的行为可能不同，建议使用：

```python
shifted_lon = (lon - seam_west) % 360.0
```

## Minecraft X/Z 反算经纬度

```text
pixel_x = X + W / 2
pixel_z = Z + H / 2
lon = normalize(pixel_x / W × 360 + S)
lat = 90 - pixel_z / H × 180
```

其中 `normalize` 把经度归一化到 `[-180, 180)`：

```python
lon = ((lon + 180.0) % 360.0) - 180.0
```

## 命令行工具

经纬度转 X/Z：

```powershell
python tools\scale\convert_coordinates.py --scale 200 --lonlat 116.4074 39.9042
python tools\scale\convert_coordinates.py --scale 400 --lonlat 103.8198 1.3521
```

X/Z 反算经纬度：

```powershell
python tools\scale\convert_coordinates.py --scale 200 --xz -14606 -20431
```

自定义比例或尺寸：

```powershell
python tools\scale\convert_coordinates.py --scale 300 --lonlat 120.15 31.20
python tools\scale\convert_coordinates.py --scale 300 --width 109227 --height 61440 --lonlat 120.15 31.20
```

## 示例坐标

| 地点 | 经纬度 | 1:200 X/Z | 1:400 X/Z |
|---|---|---:|---:|
| 北京 | 116.4074°E, 39.9042°N | -14606, -20431 | -7303, -10215 |
| 新加坡 | 103.8198°E, 1.3521°N | -20334, -692 | -10167, -346 |
| 纽约 | 74.0060°W, 40.7128°N | 62575, -20845 | 31288, -10422 |
| 伦敦 | 0.1276°W, 51.5074°N | -67642, -26372 | -33821, -13186 |
| 太湖中心附近 | 120.15°E, 31.20°N | -12902, -15974 | -6451, -7987 |

坐标使用最近整数方块。现实地点通常覆盖多个方块，城市中心、行政中心和地理中心也可能采用不同经纬度，因此几格到几十格差异不一定代表公式错误。

## Y 坐标

经纬度只能确定 X/Z，不能直接确定安全的 Y。文档中的 `/tp @s X 120 Z` 只是高空传送示例。实际地面高度应由游戏地形查询或安全传送逻辑确定；海洋、高山和洞穴上方不能统一使用同一个地面 Y。

## 世界边界与环绕

数据包本身不会把越过左右或上下边界的玩家自动传送到另一侧。如果服务器希望实现全球环绕，需要单独的模组或脚本：

- X 越过右边界时传到相同 Z 的左边界；
- X 越过左边界时传到相同 Z 的右边界；
- 若要南北环绕，可对 Z 使用同样逻辑，但这不是球形地球的真实极点行为。

边界传送应保留相对边界偏移，并在目标 X/Z 查询安全地面 Y。
