import argparse
import json


BASE_SCALE = 200.0
BASE_WIDTH = 163840
BASE_HEIGHT = 92160
SEAM_WEST_LONGITUDE = -31.5


def dimensions(scale):
    factor = BASE_SCALE / scale
    return round(BASE_WIDTH * factor), round(BASE_HEIGHT * factor)


def normalize_longitude(longitude):
    return ((longitude + 180.0) % 360.0) - 180.0


def lonlat_to_world(longitude, latitude, width, height):
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("Latitude must be between -90 and 90")
    shifted = (longitude - SEAM_WEST_LONGITUDE) % 360.0
    pixel_x = shifted / 360.0 * width
    pixel_z = (90.0 - latitude) / 180.0 * height
    return round(pixel_x - width / 2.0), round(pixel_z - height / 2.0)


def world_to_lonlat(x, z, width, height):
    pixel_x = x + width / 2.0
    pixel_z = z + height / 2.0
    longitude = normalize_longitude(pixel_x / width * 360.0 + SEAM_WEST_LONGITUDE)
    latitude = 90.0 - pixel_z / height * 180.0
    return longitude, latitude


def main():
    parser = argparse.ArgumentParser(description="Convert Pacific-centered Earth-map coordinates.")
    parser.add_argument("--scale", type=float, default=200.0, help="Scale denominator, default: 200")
    parser.add_argument("--width", type=int, help="Override global width")
    parser.add_argument("--height", type=int, help="Override global height")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--lonlat", nargs=2, type=float, metavar=("LONGITUDE", "LATITUDE"))
    group.add_argument("--xz", nargs=2, type=float, metavar=("X", "Z"))
    args = parser.parse_args()

    if args.scale <= 0:
        raise ValueError("Scale must be positive")
    default_width, default_height = dimensions(args.scale)
    width = args.width if args.width is not None else default_width
    height = args.height if args.height is not None else default_height
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive")

    result = {
        "scale": f"1:{args.scale:g}",
        "width": width,
        "height": height,
        "pacific_west_seam_longitude": SEAM_WEST_LONGITUDE,
    }
    if args.lonlat:
        longitude, latitude = args.lonlat
        x, z = lonlat_to_world(longitude, latitude, width, height)
        result.update({
            "longitude": longitude,
            "latitude": latitude,
            "x": x,
            "z": z,
            "teleport_example": f"/tp @s {x} 120 {z}",
        })
    else:
        x, z = args.xz
        longitude, latitude = world_to_lonlat(x, z, width, height)
        result.update({"x": x, "z": z, "longitude": longitude, "latitude": latitude})

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
