# Coordinate System and Longitude/Latitude Conversion

[English](COORDINATE_SYSTEM.md) | [简体中文](../zh-CN/COORDINATE_SYSTEM_zh-CN.md)

## Orientation

- Minecraft `X` is the east-west axis and generally increases eastward.
- Minecraft `Z` increases southward and decreases northward.
- The west map seam is `-31.5°`, or `31.5°W`.
- The map center longitude is approximately `148.5°E`.
- The North Pole is near minimum Z; the South Pole is near maximum Z.

World `(0, 0)` is near the center of the rectangular global map. It is not geographic `(0°, 0°)`.

## Dimensions

| Scale | Width `W` | Height `H` | Approximate X range | Approximate Z range |
|---|---:|---:|---:|---:|
| 1:200 | 163840 | 92160 | -81920 to 81919 | -46080 to 46079 |
| 1:400 | 81920 | 46080 | -40960 to 40959 | -23040 to 23039 |

## Longitude/Latitude to Minecraft X/Z

Let `S = -31.5`, longitude be positive east, latitude be positive north, and `W/H` be global dimensions.

```text
shifted_lon = (longitude - S) mod 360
X = round(shifted_lon / 360 × W - W / 2)
Z = round((90 - latitude) / 180 × H - H / 2)
```

Use a positive modulo result in `[0, 360)`. Python's expression is:

```python
shifted_lon = (longitude - seam_west) % 360.0
```

## Minecraft X/Z to Longitude/Latitude

```text
pixel_x = X + W / 2
pixel_z = Z + H / 2
longitude = normalize(pixel_x / W × 360 + S)
latitude = 90 - pixel_z / H × 180
```

Normalize longitude to `[-180, 180)`:

```python
longitude = ((longitude + 180.0) % 360.0) - 180.0
```

## Command-Line Tool

```powershell
python tools\scale\convert_coordinates.py --scale 200 --lonlat 116.4074 39.9042
python tools\scale\convert_coordinates.py --scale 400 --lonlat 103.8198 1.3521
python tools\scale\convert_coordinates.py --scale 200 --xz -14606 -20431
```

Custom scale/dimensions:

```powershell
python tools\scale\convert_coordinates.py --scale 300 --width 109227 --height 61440 --lonlat 120.15 31.20
```

## Examples

| Place | Longitude/latitude | 1:200 X/Z | 1:400 X/Z |
|---|---|---:|---:|
| Beijing | 116.4074°E, 39.9042°N | -14606, -20431 | -7303, -10215 |
| Singapore | 103.8198°E, 1.3521°N | -20334, -692 | -10167, -346 |
| New York | 74.0060°W, 40.7128°N | 62575, -20845 | 31288, -10422 |
| London | 0.1276°W, 51.5074°N | -67642, -26372 | -33821, -13186 |
| Lake Tai center area | 120.15°E, 31.20°N | -12902, -15974 | -6451, -7987 |

Coordinates are rounded to the nearest block. Real places occupy areas, and different definitions of city center can produce small differences.

## Y Coordinate

Longitude and latitude determine X/Z only. `/tp @s X 120 Z` is a high-altitude example, not a guaranteed ground coordinate. Safe teleportation should query terrain height at the destination.

## Boundary Wrapping

The datapack does not automatically wrap players across map edges. A separate mod or script can map right-edge X to left-edge X at the same Z and vice versa. North-south Z wrapping is possible but does not model real polar geometry. Preserve edge offset and recalculate safe destination Y.
