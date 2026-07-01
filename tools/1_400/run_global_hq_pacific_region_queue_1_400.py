import json
import os
import subprocess
import sys
import time
from pathlib import Path

from run_global_hq_region_queue import build_regions


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
HQ_ROOT = Path(os.environ.get(
    "NOVOATLAS_1_400_HQ_ROOT",
    str(OUT_ROOT / "HQ_1_400_Pacific_FullRoute"),
))
STATE_PATH = HQ_ROOT / "world_1_400_global_hq_pacific_region_queue_state.json"
LOG_PATH = HQ_ROOT / "world_1_400_global_hq_pacific_region_queue.log"
PYTHON = sys.executable
REGION_TIMEOUT_SECONDS = 45 * 60

BUILD = TOOLS / "build_high_quality_region_1_400_from_v5_pipeline.py"
PATCH = TOOLS / "patch_region_into_global_hq_pacific_assembly_1_400.py"


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


def run_command(args, log_file, timeout_seconds=None):
    start = time.monotonic()
    log_file.parent.mkdir(parents=True, exist_ok=True)
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


def main():
    state = load_state()
    completed = {item["name"] for item in state.get("completed", [])}
    regions = build_regions()
    state["total_regions"] = len(regions)
    state["state_path"] = str(STATE_PATH)
    state["log_path"] = str(LOG_PATH)
    state["scale"] = "1 block ~= 400 m"
    state["route"] = "Same geographic region queue as 1:200 HQ, rebuilt at 81920x46080 global pixels."
    write_json(STATE_PATH, state)
    log(f"Global 1:400 HQ Pacific queue started/resumed: {len(completed)}/{len(regions)} completed")

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
        build_log = HQ_ROOT / "logs" / f"region_queue_{name}_build.log"
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

        region_pack = OUT_ROOT / f"NovoAtlas_World_1block400m_HQ_Region_{name}_v1"
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
        patch_log = HQ_ROOT / "logs" / f"region_queue_{name}_patch.log"
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

        preview = OUT_ROOT / f"world_1_400_hq_region_{name}_v1_preview.png"
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

    log("Global 1:400 HQ Pacific queue finished")


if __name__ == "__main__":
    main()
