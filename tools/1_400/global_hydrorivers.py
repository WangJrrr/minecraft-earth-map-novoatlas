import shutil
import struct
import time
import urllib.request
import zipfile
from pathlib import Path


HYDRORIVERS_URL = "https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_{code}_shp.zip"

# Broad archive footprints. Overlap is intentional because HydroRIVERS splits
# some high-latitude drainage into Arctic and Siberia archives.
ARCHIVE_BOUNDS = {
    "af": (-20.0, -36.0, 55.0, 38.0),
    "ar": (-180.0, 50.0, -45.0, 90.0),
    "as": (25.0, -12.0, 180.0, 62.0),
    "au": (90.0, -50.0, 180.0, 15.0),
    "eu": (-25.0, 20.0, 75.0, 75.0),
    "gr": (-75.0, 55.0, -10.0, 90.0),
    "na": (-180.0, 5.0, -45.0, 78.0),
    "sa": (-92.0, -60.0, -30.0, 16.0),
    "si": (25.0, 45.0, 180.0, 90.0),
}


def _intersects(a, b):
    return a[2] >= b[0] and a[0] <= b[2] and a[3] >= b[1] and a[1] <= b[3]


def archive_codes_for_bbox(bbox):
    bounds = (bbox["west"], bbox["south"], bbox["east"], bbox["north"])
    return [code for code, archive_bounds in ARCHIVE_BOUNDS.items() if _intersects(bounds, archive_bounds)]


def ensure_archive(cache_dir, code, retries=5):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"HydroRIVERS_v10_{code}_shp.zip"
    if path.exists() and path.stat().st_size > 1_000_000:
        return path

    partial = path.with_suffix(path.suffix + ".partial")
    url = HYDRORIVERS_URL.format(code=code)
    last_error = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "NovoAtlas-EarthMap/1.0"})
            with urllib.request.urlopen(request, timeout=120) as source, partial.open("wb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
            if partial.stat().st_size <= 1_000_000:
                raise RuntimeError(f"HydroRIVERS archive is unexpectedly small: {partial}")
            partial.replace(path)
            return path
        except Exception as exc:
            last_error = exc
            partial.unlink(missing_ok=True)
            time.sleep(3.0 + attempt * 3.0)
    raise RuntimeError(f"Unable to download HydroRIVERS archive {code} from {url}") from last_error


def _member_bytes(source, code, extension):
    expected = f"HydroRIVERS_v10_{code}.{extension}".lower()
    for name in source.namelist():
        if name.lower().endswith(expected):
            return source.read(name)
    raise KeyError(f"Missing {expected} in {source.filename}")


def _dbf_fields(dbf):
    fields = {}
    pos = 32
    offset = 1
    while dbf[pos] != 13:
        raw = dbf[pos:pos + 32]
        name = raw[:11].split(b"\0", 1)[0].decode("latin1")
        size = raw[16]
        fields[name] = (offset, size)
        offset += size
        pos += 32
    return fields


def _dbf_float(record, fields, name):
    offset, size = fields[name]
    value = record[offset:offset + size].strip()
    return float(value) if value else 0.0


def read_selected_reaches(archive, code, bbox, selected, radius_for):
    """Return the tuple shape consumed by the inherited river rasterizer."""
    with zipfile.ZipFile(archive) as source:
        shp = _member_bytes(source, code, "shp")
        dbf = _member_bytes(source, code, "dbf")

    fields = _dbf_fields(dbf)
    dbf_header_len = struct.unpack("<H", dbf[8:10])[0]
    dbf_record_len = struct.unpack("<H", dbf[10:12])[0]
    reaches = []
    pos = 100
    index = 0
    margin = 0.4
    while pos < len(shp):
        content_len = struct.unpack(">i", shp[pos + 4:pos + 8])[0] * 2
        pos += 8
        end = pos + content_len
        shape_type = struct.unpack("<i", shp[pos:pos + 4])[0]
        if shape_type == 3:
            xmin, ymin, xmax, ymax = struct.unpack("<4d", shp[pos + 4:pos + 36])
            intersects = (
                xmax >= bbox["west"] - margin
                and xmin <= bbox["east"] + margin
                and ymax >= bbox["south"] - margin
                and ymin <= bbox["north"] + margin
            )
            if intersects:
                record = dbf[
                    dbf_header_len + index * dbf_record_len:
                    dbf_header_len + (index + 1) * dbf_record_len
                ]
                flow = _dbf_float(record, fields, "DIS_AV_CMS")
                upland = _dbf_float(record, fields, "UPLAND_SKM")
                length = _dbf_float(record, fields, "LENGTH_KM")
                if selected(flow, upland, length):
                    num_parts, num_points = struct.unpack("<2i", shp[pos + 36:pos + 44])
                    parts = list(struct.unpack(
                        f"<{num_parts}i", shp[pos + 44:pos + 44 + num_parts * 4]
                    ))
                    parts.append(num_points)
                    point_offset = pos + 44 + num_parts * 4
                    reaches.append((point_offset, parts, radius_for(flow, upland), shp))
        pos = end
        index += 1
    return reaches


def make_reader(base, bbox, cache_dir):
    codes = archive_codes_for_bbox(bbox)

    def read_global_hydrorivers():
        reaches = []
        for code in codes:
            archive = ensure_archive(cache_dir, code)
            reaches.extend(read_selected_reaches(
                archive, code, bbox, base.hydroriver_selected, base.hydroriver_radius
            ))
        return reaches

    read_global_hydrorivers.archive_codes = tuple(codes)
    return read_global_hydrorivers
