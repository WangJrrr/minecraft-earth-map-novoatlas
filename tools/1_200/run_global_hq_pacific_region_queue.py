import importlib
import os
from pathlib import Path


q = importlib.import_module("run_global_hq_region_queue")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))

q.STATE_PATH = OUT_ROOT / "world_1_200_global_hq_pacific_region_queue_state.json"
q.LOG_PATH = OUT_ROOT / "world_1_200_global_hq_pacific_region_queue.log"
q.PATCH = Path(__file__).resolve().parent / "patch_region_into_global_hq_pacific_assembly.py"


if __name__ == "__main__":
    q.main()
