import json
import os
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
STATE_PATH = OUT_ROOT / "world_1_200_global_hq_region_queue_state.json"
LOG_PATH = OUT_ROOT / "world_1_200_global_hq_region_queue.log"
PYTHON = sys.executable
REGION_TIMEOUT_SECONDS = 45 * 60

BUILD = TOOLS / "build_high_quality_region_from_v5_pipeline.py"
PATCH = TOOLS / "patch_region_into_global_hq_assembly.py"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"completed": [], "failed": [], "started_at": time.strftime("%Y-%m-%d %H:%M:%S")}


def log(message):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def region_name(west, south, east, north):
    def fmt(v):
        hemi = "E" if v >= 0 else "W"
        return f"{abs(v):05.1f}{hemi}".replace(".", "p")

    def fmt_lat(v):
        hemi = "N" if v >= 0 else "S"
        return f"{abs(v):04.1f}{hemi}".replace(".", "p")

    return f"R_{fmt(west)}_{fmt(east)}_{fmt_lat(south)}_{fmt_lat(north)}"


def build_regions():
    # 13.5 x 12 degrees = 6144 x 6144 blocks at the global 1:200 grid.
    # This is the size that has completed reliably in the current pipeline.
    lon_step = 13.5
    lat_step = 12.0
    regions = []
    # Start with inhabited/non-polar latitudes so early previews are useful and
    # a polar data-source issue cannot block visible progress.
    south = -60.0
    while south < 72.0:
        north = min(72.0, south + lat_step)
        west = -180.0
        while west < 180.0:
            east = min(180.0, west + lon_step)
            regions.append(
                {
                    "name": region_name(west, south, east, north),
                    "west": round(west, 6),
                    "south": round(south, 6),
                    "east": round(east, 6),
                    "north": round(north, 6),
                }
            )
            west = east
        south = north
    south = -84.0
    while south < 84.0:
        north = min(84.0, south + lat_step)
        if -60.0 <= south < 72.0:
            south = north
            continue
        west = -180.0
        while west < 180.0:
            east = min(180.0, west + lon_step)
            regions.append(
                {
                    "name": region_name(west, south, east, north),
                    "west": round(west, 6),
                    "south": round(south, 6),
                    "east": round(east, 6),
                    "north": round(north, 6),
                }
            )
            west = east
        south = north
    # Polar caps are lower-detail visually in Minecraft but still generated as
    # native samples instead of scaling the old global raster.
    for south, north in [(-90.0, -84.0), (84.0, 90.0)]:
        west = -180.0
        while west < 180.0:
            east = min(180.0, west + lon_step)
            regions.append(
                {
                    "name": region_name(west, south, east, north),
                    "west": round(west, 6),
                    "south": south,
                    "east": round(east, 6),
                    "north": north,
                }
            )
            west = east
    land_priority_boxes = [
        # East/Southeast Asia and Oceania, useful for immediate comparison with
        # the validated East Asia shard.
        (70, -15, 150, 55, 100),
        (105, -45, 180, 0, 85),
        # Europe, Africa, South/West Asia.
        (-15, 35, 45, 72, 95),
        (-20, -35, 55, 35, 90),
        (35, 5, 80, 45, 80),
        # North and South America.
        (-170, 15, -50, 72, 88),
        (-85, -60, -30, 15, 86),
        # Northern Eurasia and secondary island arcs.
        (45, 45, 180, 72, 70),
        (-180, 45, -120, 72, 65),
        (-10, -55, 180, -35, 45),
    ]

    def overlap_area(region, box):
        west, south, east, north, _ = box
        ow = max(0.0, min(region["east"], east) - max(region["west"], west))
        oh = max(0.0, min(region["north"], north) - max(region["south"], south))
        return ow * oh

    def priority(region):
        score = 0.0
        for box in land_priority_boxes:
            score += overlap_area(region, box) * box[4]
        center_lat = (region["south"] + region["north"]) / 2.0
        # Keep polar/ocean belts later unless they overlap land-priority boxes.
        score -= max(0.0, abs(center_lat) - 60.0) * 20.0
        return (-score, abs(center_lat), region["west"])

    return sorted(regions, key=priority)


def run_command(args, log_file, timeout_seconds=None):
    start = time.monotonic()
    with log_file.open("w", encoding="utf-8", errors="replace") as f:
        proc = subprocess.Popen(
            args,
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.stdout is not None
        output_tail = []
        while True:
            line = proc.stdout.readline()
            if line:
                f.write(line)
                f.flush()
                output_tail.append(line.rstrip())
                output_tail = output_tail[-20:]
            if proc.poll() is not None:
                rest = proc.stdout.read()
                if rest:
                    f.write(rest)
                    f.flush()
                    output_tail.extend(rest.splitlines()[-20:])
                    output_tail = output_tail[-20:]
                return proc.returncode, "\n".join(output_tail)
            if timeout_seconds and (time.monotonic() - start) > timeout_seconds:
                proc.kill()
                f.write(f"\nTIMEOUT after {timeout_seconds} seconds\n")
                f.flush()
                return 124, "\n".join(output_tail)
            time.sleep(0.2)


def old_run_command(args):
    return subprocess.run(
        args,
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )


def main():
    state = load_state()
    completed = {item["name"] for item in state.get("completed", [])}
    regions = build_regions()
    state["total_regions"] = len(regions)
    state["state_path"] = str(STATE_PATH)
    state["log_path"] = str(LOG_PATH)
    write_json(STATE_PATH, state)
    log(f"Global HQ queue started/resumed: {len(completed)}/{len(regions)} completed")

    for index, region in enumerate(regions, start=1):
        name = region["name"]
        if name in completed:
            continue
        log(f"START {index}/{len(regions)} {name} {region}")
        build_args = [
            PYTHON,
            "-u",
            str(BUILD),
            "--name",
            name,
            "--west",
            str(region["west"]),
            "--south",
            str(region["south"]),
            "--east",
            str(region["east"]),
            "--north",
            str(region["north"]),
        ]
        build_log = OUT_ROOT / f"region_queue_{name}_build.log"
        code, output_tail = run_command(build_args, build_log, REGION_TIMEOUT_SECONDS)
        if code != 0:
            log(f"FAIL build {name}, code={code}")
            state.setdefault("failed", []).append({
                "name": name,
                "stage": "build",
                "region": region,
                "code": code,
                "log": str(build_log),
                "tail": output_tail,
            })
            write_json(STATE_PATH, state)
            continue

        region_pack = OUT_ROOT / f"NovoAtlas_World_1block200m_Region_{name}_v1"
        patch_args = [
            PYTHON,
            "-u",
            str(PATCH),
            "--region-pack",
            str(region_pack),
            "--name",
            name,
            "--west",
            str(region["west"]),
            "--south",
            str(region["south"]),
            "--east",
            str(region["east"]),
            "--north",
            str(region["north"]),
        ]
        patch_log = OUT_ROOT / f"region_queue_{name}_patch.log"
        code, output_tail = run_command(patch_args, patch_log, 15 * 60)
        if code != 0:
            log(f"FAIL patch {name}, code={code}")
            state.setdefault("failed", []).append({
                "name": name,
                "stage": "patch",
                "region": region,
                "code": code,
                "log": str(patch_log),
                "tail": output_tail,
            })
            write_json(STATE_PATH, state)
            continue

        preview = OUT_ROOT / f"world_1_200_region_{name}_v1_preview.png"
        state.setdefault("completed", []).append(
            {
                "name": name,
                "region": region,
                "region_pack": str(region_pack),
                "preview": str(preview),
                "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        write_json(STATE_PATH, state)
        log(f"DONE {index}/{len(regions)} {name}")

    log("Global HQ queue finished")


if __name__ == "__main__":
    main()
