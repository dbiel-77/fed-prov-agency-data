import importlib
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parent))

# List of provincial modules
modules = [
    # "regions.AB.alberta",
    # "regions.BC.british-columbia",
    # "regions.NU.nunavut",
    # "regions.FED.federal",
    "regions.SK.saskatchewan",
]


def ensure_module_dir_on_path(module_path: str) -> None:
    """
    Ensures the directory that contains the module is on sys.path so that
    sibling absolute imports inside that module (e.g., `import sk_agencies`)
    can resolve without needing relative imports.
    """
    project_root = Path(__file__).resolve().parent
    parts = module_path.split(".")
    if len(parts) < 2:
        return

    module_dir = project_root.joinpath(*parts[:-1])
    module_dir_str = str(module_dir)

    if module_dir.is_dir() and module_dir_str not in sys.path:
        sys.path.append(module_dir_str)


def main():
    for module_path in modules:
        ensure_module_dir_on_path(module_path)
        mod = importlib.import_module(module_path)
        if hasattr(mod, "main"):
            print(f"Running {module_path}.main()")
            mod.main()
        else:
            print(f"[WARN] {module_path} has no main()")

if __name__ == "__main__":
    main()
