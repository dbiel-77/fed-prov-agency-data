import importlib
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parent))

# List of provincial modules
modules = [
    "regions.AB.alberta",
    "regions.NU.nunavut",
    "regions.FED.federal"
]

def main():
    for module_path in modules:
        mod = importlib.import_module(module_path)
        if hasattr(mod, "main"):
            print(f"Running {module_path}.main()")
            mod.main()
        else:
            print(f"[WARN] {module_path} has no main()")

if __name__ == "__main__":
    main()
