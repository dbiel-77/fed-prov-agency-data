import importlib
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(str(Path(__file__).resolve().parent))
from combine import combine

MODULES = [
    "regions.AB.alberta",
    "regions.BC.bc",
    "regions.MB.mb",
    "regions.NB.nb",
    "regions.NL.nl",
    "regions.NS.ns",
    "regions.NT.nt",
    "regions.NU.nunavut",
    "regions.ON.on",
    "regions.PE.pe",
    "regions.QC.qc",
    "regions.SK.sk",
    "regions.YT.yt",
    "regions.FED.federal",
]


def _run(module_path: str):
    try:
        mod = importlib.import_module(module_path)
        if hasattr(mod, "main"):
            mod.main()
            return module_path, None
        return module_path, "no main()"
    except Exception as e:
        return module_path, str(e)


def main():
    print(f"Running {len(MODULES)} modules concurrently…\n")
    # 6 workers: enough to keep all I/O busy without overwhelming the machine
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(_run, m): m for m in MODULES}
        for fut in as_completed(futs):
            path, err = fut.result()
            if err:
                print(f"[ERROR] {path}: {err}")
            else:
                print(f"[DONE]  {path}")

    print("\nMerging all output files…")
    combine()


if __name__ == "__main__":
    main()
