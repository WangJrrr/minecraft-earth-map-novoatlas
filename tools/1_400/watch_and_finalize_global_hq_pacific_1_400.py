import json
import os
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
HQ_ROOT = Path(os.environ.get(
    "NOVOATLAS_1_400_HQ_ROOT",
    OUT_ROOT / "HQ_1_400_Pacific_FullRoute",
))
STATE_PATH = HQ_ROOT / "world_1_400_global_hq_pacific_region_queue_state.json"
QUEUE_LOG = HQ_ROOT / "world_1_400_global_hq_pacific_region_queue.log"
WATCH_LOG = HQ_ROOT / "watch_and_finalize_1_400.log"
FINALIZER = Path(__file__).resolve().parent / "finalize_global_hq_pacific_1_400_packs.py"


def log(message):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    WATCH_LOG.parent.mkdir(parents=True, exist_ok=True)
    with WATCH_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_state():
    if not STATE_PATH.exists():
        return None
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def queue_finished():
    if not QUEUE_LOG.exists():
        return False
    tail = QUEUE_LOG.read_text(encoding="utf-8", errors="replace")[-4000:]
    return "Global 1:400 HQ Pacific queue finished" in tail


def main():
    log("Watcher started")
    while True:
        state = read_state()
        if state:
            completed = len(state.get("completed", []))
            failed = len(state.get("failed", []))
            total = int(state.get("total_regions", 432))
            log(f"progress {completed}/{total}, failed={failed}")
            if queue_finished():
                if completed == total and failed == 0:
                    log("queue cleanly finished; running finalizer")
                    result = subprocess.run(
                        [sys.executable, "-u", str(FINALIZER)],
                        cwd=str(FINALIZER.parent.parent),
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        encoding="utf-8",
                        errors="replace",
                    )
                    with WATCH_LOG.open("a", encoding="utf-8") as f:
                        f.write(result.stdout)
                    log(f"finalizer exit code={result.returncode}")
                    return result.returncode
                log("queue finished but not clean; finalizer skipped")
                return 2
        time.sleep(300)


if __name__ == "__main__":
    raise SystemExit(main())
